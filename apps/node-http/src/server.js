'use strict';

// Implementation of the protocol v2 API (see CLAUDE.md "API contract") without a framework.
// Same data access and caching as node-express v06: one process, a connection pool of 10, every request reserves one
// connection for all its queries; writes that touch two tables are ONE statement with data-modifying CTEs; every
// query is a prepared statement; GET /posts (global feed) is cached in process for 1 s (see "Global feed cache").
// Since node-http v03 the Postgres client is Bun's native one (Bun.sql: tagged-template queries, prepared and cached
// per connection automatically) instead of node-postgres; since v04 the HTTP server is Bun's native one (Bun.serve:
// fetch(Request) -> Response) instead of node:http. This file needs Bun.
// What Express did is done here by hand: a small router (method + path segments), JSON body parsing (100 kB limit,
// like express.json), JSON responses. Not copied from Express: ETag and X-Powered-By headers (not in the contract).
// Every response carries a Server-Timing header: conn (pool wait), db (queries), app (the rest), total.

const { SQL } = require('bun');

const PORT = Number(process.env.PORT || 3000);
const sql = new SQL({ url: process.env.DATABASE_URL, max: 10 });

// Bun.sql returns bigint (int8) columns as strings; all our ids fit in a JS number (node-postgres did the same with a
// type parser). These are the int8 columns any query returns.
const INT8_COLUMNS = ['id', 'user_id', 'post_id'];
function int8ToNumber(rows) {
  for (const row of rows) {
    for (const col of INT8_COLUMNS) {
      if (typeof row[col] === 'string') row[col] = Number(row[col]);
    }
  }
  return rows;
}

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;
const MAX_TEXT = 1000;
const MAX_BODY = 100 * 1024;
const MAX_ID = '9223372036854775807';

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function parseId(value) {
  if (typeof value !== 'string' || !/^[1-9]\d{0,17}$/.test(value)) return null;
  return Number(value);
}

function requireId(value) {
  const id = parseId(value);
  if (id === null) throw new HttpError(404, 'not found');
  return id;
}

function pageParams(query) {
  let limit = DEFAULT_LIMIT;
  const rawLimit = query.get('limit');
  if (rawLimit !== null) {
    limit = Number(rawLimit);
    if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
      throw new HttpError(400, `limit must be an integer between 1 and ${MAX_LIMIT}`);
    }
  }
  let before = MAX_ID;
  const rawBefore = query.get('before');
  if (rawBefore !== null) {
    before = parseId(rawBefore);
    if (before === null) throw new HttpError(400, 'before must be a positive integer');
  }
  return { limit, before };
}

function page(rows, limit) {
  return { posts: rows, next_before: rows.length === limit ? rows[rows.length - 1].id : null };
}

function validText(body) {
  const text = body && body.text;
  if (typeof text !== 'string' || text.trim().length === 0 || text.length > MAX_TEXT) {
    throw new HttpError(400, `text must be 1..${MAX_TEXT} characters`);
  }
  return text;
}

// Acting user from X-User-Id (simulated auth).
function optionalUser(req) {
  const header = req.headers.get('x-user-id');
  return header === null ? null : parseId(header);
}

function requireUser(req) {
  const userId = optionalUser(req);
  if (userId === null) throw new HttpError(401, 'missing or invalid X-User-Id');
  return userId;
}

// Request body as JSON (like express.json: only for JSON content types, 100 kB limit; otherwise an empty object).
async function readJson(req) {
  const type = req.headers.get('content-type') || '';
  if (!type.includes('json')) return {};
  const text = await req.text();
  if (Buffer.byteLength(text) > MAX_BODY) throw new HttpError(413, 'request entity too large');
  if (text.length === 0) return {};
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, 'invalid JSON');
  }
}

// --- Server timing + responses -----------------------------------------------------------------------------------
const nowMs = () => Number(process.hrtime.bigint()) / 1e6;

// Every response is built here: Server-Timing is computed when the Response is created (also on errors); Bun.serve
// adds Content-Length.
function respond(timing, status, json) {
  const total = nowMs() - timing.start;
  const app = Math.max(0, total - timing.conn - timing.db);
  return new Response(json, {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Server-Timing': `conn;dur=${timing.conn.toFixed(1)}, db;dur=${timing.db.toFixed(1)}, ` +
        `app;dur=${app.toFixed(1)}, total;dur=${total.toFixed(1)}`,
    },
  });
}

// --- Database access ---------------------------------------------------------------------------------------------
// One reserved connection per request, released before the response is sent. `fn` receives `db.q`, a tagged
// template (db.q`SELECT ... ${value}`) that runs on that connection and adds each query's duration to timing.db;
// time waiting for a free connection (or opening a new one while the pool fills) goes to timing.conn.
async function withClient(timing, fn) {
  const connectStart = nowMs();
  let conn;
  try {
    conn = await sql.reserve();
  } finally {
    timing.conn += nowMs() - connectStart;
  }
  const db = {
    async q(strings, ...values) {
      const start = nowMs();
      try {
        return int8ToNumber(await conn(strings, ...values));
      } finally {
        timing.db += nowMs() - start;
      }
    },
  };
  try {
    return await fn(db);
  } finally {
    conn.release();
  }
}

// --- Global feed cache ---------------------------------------------------------------------------------------------
// GET /posts responses (serialized JSON) are cached in process for FEED_CACHE_TTL_MS, keyed by (limit, before).
// Trade-off: the global feed may be up to one TTL stale (new posts, like/comment counts). Concurrent misses for the
// same key share one query (single-flight): the request that runs it records conn/db time, the ones waiting on it
// record their wait as app time. Hit/miss counts are logged every 10 s while there is traffic.
const FEED_CACHE_TTL_MS = 1000;
const feedCache = new Map(); // key -> { expires, body: Promise<string> }
const feedStats = { hit: 0, miss: 0 };

setInterval(() => {
  const now = Date.now();
  for (const [key, entry] of feedCache) if (entry.expires <= now) feedCache.delete(key);
  if (feedStats.hit + feedStats.miss > 0) {
    console.log(`feed cache: hit=${feedStats.hit} miss=${feedStats.miss} keys=${feedCache.size}`);
    feedStats.hit = 0;
    feedStats.miss = 0;
  }
}, 10000).unref();

function cachedFeed(timing, limit, before) {
  const key = `${limit}:${before}`;
  const now = Date.now();
  const entry = feedCache.get(key);
  if (entry && entry.expires > now) {
    feedStats.hit++;
    return entry.body;
  }
  feedStats.miss++;
  const body = withClient(timing, (db) => db.q`
    SELECT p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at
    FROM posts p JOIN users u ON u.id = p.user_id
    WHERE p.is_public AND p.id < ${before}::bigint ORDER BY p.id DESC LIMIT ${limit}::int`,
  ).then((rows) => JSON.stringify(page(rows, limit)));
  const fresh = { expires: now + FEED_CACHE_TTL_MS, body };
  feedCache.set(key, fresh);
  // A failed query is not cached: the waiting requests get the error, the next request retries.
  body.catch(() => { if (feedCache.get(key) === fresh) feedCache.delete(key); });
  return body;
}

// --- Handlers ------------------------------------------------------------------------------------------------------
// Each handler gets a context { req, timing, query, params } and returns [status, json string]. The column list is
// written out in every query: in a tagged template an interpolated string would become a parameter. Every parameter
// has an explicit cast, so a JS number is never sent as float8 (which would keep the planner off the id indexes).
const ok = (body, status = 200) => [status, JSON.stringify(body)];

async function health(ctx) {
  await withClient(ctx.timing, (db) => db.q`SELECT 1`);
  return ok({ status: 'ok' });
}

async function globalFeed(ctx) {
  const { limit, before } = pageParams(ctx.query);
  return [200, await cachedFeed(ctx.timing, limit, before)];
}

async function getPost(ctx) {
  const postId = requireId(ctx.params[0]);
  const viewer = optionalUser(ctx.req);
  const body = await withClient(ctx.timing, async (db) => {
    const [post] = await db.q`
      SELECT p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at
      FROM posts p JOIN users u ON u.id = p.user_id WHERE p.id = ${postId}::bigint`;
    if (!post || (!post.is_public && post.user_id !== viewer)) throw new HttpError(404, 'not found');
    const comments = await db.q`
      SELECT id, post_id, user_id, text, created_at FROM comments
      WHERE post_id = ${postId}::bigint ORDER BY id DESC LIMIT 20`;
    return { post, comments };
  });
  return ok(body);
}

async function userPosts(ctx) {
  const userId = requireId(ctx.params[0]);
  const { limit, before } = pageParams(ctx.query);
  const rows = await withClient(ctx.timing, (db) => db.q`
    SELECT p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at
    FROM posts p JOIN users u ON u.id = p.user_id
    WHERE p.user_id = ${userId}::bigint AND p.is_public AND p.id < ${before}::bigint
    ORDER BY p.id DESC LIMIT ${limit}::int`);
  return ok(page(rows, limit));
}

async function myPosts(ctx) {
  const userId = requireUser(ctx.req);
  const { limit, before } = pageParams(ctx.query);
  const rows = await withClient(ctx.timing, (db) => db.q`
    SELECT p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at
    FROM posts p JOIN users u ON u.id = p.user_id
    WHERE p.user_id = ${userId}::bigint AND p.id < ${before}::bigint ORDER BY p.id DESC LIMIT ${limit}::int`);
  return ok(page(rows, limit));
}

async function createPost(ctx) {
  const userId = requireUser(ctx.req);
  const body = await readJson(ctx.req);
  const text = validText(body);
  const isPublic = body.is_public === undefined ? true : body.is_public;
  if (typeof isPublic !== 'boolean') throw new HttpError(400, 'is_public must be a boolean');
  const [post] = await withClient(ctx.timing, (db) => db.q`
    WITH p AS (
      INSERT INTO posts (user_id, text, is_public) VALUES (${userId}::bigint, ${text}::text, ${isPublic}::boolean)
      RETURNING *
    )
    SELECT p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at
    FROM p JOIN users u ON u.id = p.user_id`);
  return ok({ post }, 201);
}

async function like(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  // Insert the like only if the post exists; bump the counter only if the like is new. The outer SELECT sees the
  // snapshot from before the statement, so a new like's count comes from `upd`, an existing like's from `posts`.
  const [row] = await withClient(ctx.timing, (db) => db.q`
    WITH ins AS (
      INSERT INTO likes (post_id, user_id) SELECT id, ${userId}::bigint FROM posts WHERE id = ${postId}::bigint
      ON CONFLICT DO NOTHING RETURNING post_id
    ), upd AS (
      UPDATE posts SET like_count = like_count + 1 FROM ins WHERE posts.id = ins.post_id RETURNING posts.like_count
    )
    SELECT COALESCE((SELECT like_count FROM upd),
                    (SELECT like_count FROM posts WHERE id = ${postId}::bigint)) AS like_count`);
  if (row.like_count === null) throw new HttpError(404, 'not found');
  return ok({ liked: true, like_count: row.like_count });
}

async function unlike(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  const [row] = await withClient(ctx.timing, (db) => db.q`
    WITH del AS (
      DELETE FROM likes WHERE post_id = ${postId}::bigint AND user_id = ${userId}::bigint RETURNING post_id
    ), upd AS (
      UPDATE posts SET like_count = like_count - 1 FROM del WHERE posts.id = del.post_id RETURNING posts.like_count
    )
    SELECT COALESCE((SELECT like_count FROM upd),
                    (SELECT like_count FROM posts WHERE id = ${postId}::bigint)) AS like_count`);
  if (row.like_count === null) throw new HttpError(404, 'not found');
  return ok({ liked: false, like_count: row.like_count });
}

async function comment(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  const text = validText(await readJson(ctx.req));
  // Unknown post or user fails the comments foreign keys (23503).
  const [row] = await withClient(ctx.timing, (db) => db.q`
    WITH c AS (
      INSERT INTO comments (post_id, user_id, text) VALUES (${postId}::bigint, ${userId}::bigint, ${text}::text)
      RETURNING id, post_id, user_id, text, created_at
    ), upd AS (
      UPDATE posts SET comment_count = comment_count + 1 FROM c WHERE posts.id = c.post_id
    )
    SELECT * FROM c`);
  return ok({ comment: row }, 201);
}

// --- Router ----------------------------------------------------------------------------------------------------------
// Path split into segments (a trailing slash is ignored, as in Express); ':id' segments are passed as params.
function route(method, seg) {
  const n = seg.length;
  if (method === 'GET' || method === 'HEAD') {
    if (n === 1 && seg[0] === 'health') return [health];
    if (n === 1 && seg[0] === 'posts') return [globalFeed];
    if (n === 2 && seg[0] === 'posts') return [getPost, seg[1]];
    if (n === 3 && seg[0] === 'users' && seg[2] === 'posts') return [userPosts, seg[1]];
    if (n === 2 && seg[0] === 'me' && seg[1] === 'posts') return [myPosts];
  } else if (method === 'POST') {
    if (n === 1 && seg[0] === 'posts') return [createPost];
    if (n === 3 && seg[0] === 'posts' && seg[2] === 'like') return [like, seg[1]];
    if (n === 3 && seg[0] === 'posts' && seg[2] === 'comments') return [comment, seg[1]];
  } else if (method === 'DELETE') {
    if (n === 3 && seg[0] === 'posts' && seg[2] === 'like') return [unlike, seg[1]];
  }
  return null;
}

function errorResponse(err) {
  if (err instanceof HttpError) return ok({ error: err.message }, err.status);
  if (err instanceof URIError) return ok({ error: 'malformed URL' }, 400);
  if (err.errno === '23503') { // Bun.sql: SQLSTATE in errno (err.code is Bun's own error code)
    // Foreign key violation: unknown post -> 404, unknown acting user -> 401.
    if (/user_id/.test(err.constraint || '')) return ok({ error: 'unknown user' }, 401);
    return ok({ error: 'not found' }, 404);
  }
  console.error(err);
  return ok({ error: 'internal error' }, 500);
}

async function handle(req) {
  const timing = { start: nowMs(), conn: 0, db: 0 };
  let status;
  let json;
  try {
    // req.url is absolute (http://host:port/path?query): the path starts at the first '/' after the scheme.
    const url = req.url;
    const p = url.indexOf('/', url.indexOf('//') + 2);
    const q = url.indexOf('?', p);
    const path = q === -1 ? url.slice(p) : url.slice(p, q);
    const query = new URLSearchParams(q === -1 ? '' : url.slice(q + 1));
    const seg = path.split('/').filter(Boolean).map(decodeURIComponent);
    const match = route(req.method, seg);
    if (match === null) throw new HttpError(404, 'not found');
    const [handler, ...params] = match;
    [status, json] = await handler({ req, timing, query, params });
  } catch (err) {
    [status, json] = errorResponse(err);
  }
  return respond(timing, status, json);
}

const server = Bun.serve({ port: PORT, fetch: handle });
console.log(`node-http (Bun.serve) listening on :${server.port}`);

function shutdown() {
  server.stop().then(() => sql.close()).then(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
