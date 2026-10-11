'use strict';

// Implementation of the protocol v2 API (see CLAUDE.md "API contract") on plain node:http — no framework.
// Same data access and caching as node-express v06: one process, a pg.Pool with default settings (max 10), every
// request borrows one connection for all its queries; writes that touch two tables are ONE statement with
// data-modifying CTEs; every query is a prepared statement (named query); GET /posts (global feed) is cached in
// process for 1 s (see "Global feed cache"). What Express did is done here by hand: a small router (method + path
// segments), JSON body parsing (100 kB limit, like express.json), JSON responses with Content-Length. Not copied
// from Express: ETag and X-Powered-By headers (not part of the contract).
// Every response carries a Server-Timing header: conn (pool wait), db (queries), app (the rest), total.

const http = require('node:http');
const { Pool, types } = require('pg');

// bigint ids/counters come back as strings by default; all our values fit in a JS number.
types.setTypeParser(20, (v) => parseInt(v, 10));

const PORT = Number(process.env.PORT || 3000);
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.on('error', (err) => console.error('pg pool error', err));

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;
const MAX_TEXT = 1000;
const MAX_BODY = 100 * 1024;
const MAX_ID = '9223372036854775807';

const POST_COLUMNS = `p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at`;

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
  const header = req.headers['x-user-id'];
  return header === undefined ? null : parseId(header);
}

function requireUser(req) {
  const userId = optionalUser(req);
  if (userId === null) throw new HttpError(401, 'missing or invalid X-User-Id');
  return userId;
}

// Request body as JSON (like express.json: only for JSON content types, 100 kB limit; otherwise an empty object).
function readJson(req) {
  const type = req.headers['content-type'] || '';
  if (!type.includes('json')) {
    req.resume();
    return Promise.resolve({});
  }
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        reject(new HttpError(413, 'request entity too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (size === 0) return resolve({});
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
      } catch {
        reject(new HttpError(400, 'invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

// --- Server timing + responses -----------------------------------------------------------------------------------
const nowMs = () => Number(process.hrtime.bigint()) / 1e6;

// Every response goes through here: Server-Timing is computed just before the headers go out (also on errors).
function send(res, timing, status, json) {
  const total = nowMs() - timing.start;
  const app = Math.max(0, total - timing.conn - timing.db);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(json),
    'Server-Timing': `conn;dur=${timing.conn.toFixed(1)}, db;dur=${timing.db.toFixed(1)}, ` +
      `app;dur=${app.toFixed(1)}, total;dur=${total.toFixed(1)}`,
  });
  res.end(json);
}

// --- Database access ---------------------------------------------------------------------------------------------
// All SQL texts are constants, so each distinct text gets a stable statement name (q1, q2, ...).
const statementNames = new Map();
function statementName(text) {
  let name = statementNames.get(text);
  if (name === undefined) {
    name = `q${statementNames.size + 1}`;
    statementNames.set(text, name);
  }
  return name;
}

// One pooled connection per request, returned to the pool before the response is sent. `fn` receives a query
// wrapper that adds each query's duration to timing.db; time waiting for a pooled connection (or opening a new
// one while the pool fills) goes to timing.conn.
async function withClient(timing, fn) {
  const connectStart = nowMs();
  let client;
  try {
    client = await pool.connect();
  } finally {
    timing.conn += nowMs() - connectStart;
  }
  const db = {
    async query(text, params) {
      const start = nowMs();
      try {
        return await client.query({ name: statementName(text), text, values: params });
      } finally {
        timing.db += nowMs() - start;
      }
    },
  };
  try {
    return await fn(db);
  } finally {
    client.release();
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
  const body = withClient(timing, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.is_public AND p.id < $1 ORDER BY p.id DESC LIMIT $2`,
    [before, limit],
  )).then(({ rows }) => JSON.stringify(page(rows, limit)));
  const fresh = { expires: now + FEED_CACHE_TTL_MS, body };
  feedCache.set(key, fresh);
  // A failed query is not cached: the waiting requests get the error, the next request retries.
  body.catch(() => { if (feedCache.get(key) === fresh) feedCache.delete(key); });
  return body;
}

// --- Handlers ------------------------------------------------------------------------------------------------------
// Each handler gets a context { req, timing, query, params } and returns [status, json string].
const ok = (body, status = 200) => [status, JSON.stringify(body)];

async function health(ctx) {
  await withClient(ctx.timing, (db) => db.query('SELECT 1'));
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
    const { rows } = await db.query(
      `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id WHERE p.id = $1`,
      [postId],
    );
    const post = rows[0];
    if (!post || (!post.is_public && post.user_id !== viewer)) throw new HttpError(404, 'not found');
    const comments = await db.query(
      `SELECT id, post_id, user_id, text, created_at FROM comments
       WHERE post_id = $1 ORDER BY id DESC LIMIT 20`,
      [postId],
    );
    return { post, comments: comments.rows };
  });
  return ok(body);
}

async function userPosts(ctx) {
  const userId = requireId(ctx.params[0]);
  const { limit, before } = pageParams(ctx.query);
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.user_id = $1 AND p.is_public AND p.id < $2 ORDER BY p.id DESC LIMIT $3`,
    [userId, before, limit],
  ));
  return ok(page(rows, limit));
}

async function myPosts(ctx) {
  const userId = requireUser(ctx.req);
  const { limit, before } = pageParams(ctx.query);
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.user_id = $1 AND p.id < $2 ORDER BY p.id DESC LIMIT $3`,
    [userId, before, limit],
  ));
  return ok(page(rows, limit));
}

async function createPost(ctx) {
  const userId = requireUser(ctx.req);
  const body = await readJson(ctx.req);
  const text = validText(body);
  const isPublic = body.is_public === undefined ? true : body.is_public;
  if (typeof isPublic !== 'boolean') throw new HttpError(400, 'is_public must be a boolean');
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `WITH p AS (
       INSERT INTO posts (user_id, text, is_public) VALUES ($1, $2, $3) RETURNING *
     )
     SELECT ${POST_COLUMNS} FROM p JOIN users u ON u.id = p.user_id`,
    [userId, text, isPublic],
  ));
  return ok({ post: rows[0] }, 201);
}

async function like(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  // Insert the like only if the post exists; bump the counter only if the like is new. The outer SELECT sees the
  // snapshot from before the statement, so a new like's count comes from `upd`, an existing like's from `posts`.
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `WITH ins AS (
       INSERT INTO likes (post_id, user_id) SELECT id, $2::bigint FROM posts WHERE id = $1
       ON CONFLICT DO NOTHING RETURNING post_id
     ), upd AS (
       UPDATE posts SET like_count = like_count + 1 FROM ins WHERE posts.id = ins.post_id RETURNING posts.like_count
     )
     SELECT COALESCE((SELECT like_count FROM upd), (SELECT like_count FROM posts WHERE id = $1)) AS like_count`,
    [postId, userId],
  ));
  if (rows[0].like_count === null) throw new HttpError(404, 'not found');
  return ok({ liked: true, like_count: rows[0].like_count });
}

async function unlike(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `WITH del AS (
       DELETE FROM likes WHERE post_id = $1 AND user_id = $2 RETURNING post_id
     ), upd AS (
       UPDATE posts SET like_count = like_count - 1 FROM del WHERE posts.id = del.post_id RETURNING posts.like_count
     )
     SELECT COALESCE((SELECT like_count FROM upd), (SELECT like_count FROM posts WHERE id = $1)) AS like_count`,
    [postId, userId],
  ));
  if (rows[0].like_count === null) throw new HttpError(404, 'not found');
  return ok({ liked: false, like_count: rows[0].like_count });
}

async function comment(ctx) {
  const userId = requireUser(ctx.req);
  const postId = requireId(ctx.params[0]);
  const text = validText(await readJson(ctx.req));
  // Unknown post or user fails the comments foreign keys (23503).
  const { rows } = await withClient(ctx.timing, (db) => db.query(
    `WITH c AS (
       INSERT INTO comments (post_id, user_id, text) VALUES ($1, $2, $3)
       RETURNING id, post_id, user_id, text, created_at
     ), upd AS (
       UPDATE posts SET comment_count = comment_count + 1 FROM c WHERE posts.id = c.post_id
     )
     SELECT * FROM c`,
    [postId, userId, text],
  ));
  return ok({ comment: rows[0] }, 201);
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
  if (err.code === '23503') {
    // Foreign key violation: unknown post -> 404, unknown acting user -> 401.
    if (/user_id/.test(err.constraint || '')) return ok({ error: 'unknown user' }, 401);
    return ok({ error: 'not found' }, 404);
  }
  console.error(err);
  return ok({ error: 'internal error' }, 500);
}

async function handle(req, res) {
  const timing = { start: nowMs(), conn: 0, db: 0 };
  let status;
  let json;
  try {
    const q = req.url.indexOf('?');
    const path = q === -1 ? req.url : req.url.slice(0, q);
    const query = new URLSearchParams(q === -1 ? '' : req.url.slice(q + 1));
    const seg = path.split('/').filter(Boolean).map(decodeURIComponent);
    const match = route(req.method, seg);
    if (match === null) throw new HttpError(404, 'not found');
    const [handler, ...params] = match;
    [status, json] = await handler({ req, timing, query, params });
  } catch (err) {
    [status, json] = errorResponse(err);
  }
  send(res, timing, status, json);
}

const server = http.createServer((req, res) => { handle(req, res); });
server.listen(PORT, () => console.log(`node-http listening on :${PORT}`));

function shutdown() {
  server.close(() => pool.end().then(() => process.exit(0)));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
