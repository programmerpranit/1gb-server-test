'use strict';

// Implementation of the protocol v2 API (see CLAUDE.md "API contract").
// Deliberately plain: Express defaults, one process, a pg.Pool with default settings (max 10) — every request
// borrows one connection for all its queries and returns it when done. Writes that touch two tables (like + counter,
// comment + counter) are ONE statement with data-modifying CTEs: atomic without BEGIN/COMMIT, one round trip.
// Every response carries a Server-Timing header: conn (pool wait), db (queries), app (the rest), total.

const express = require('express');
const { Pool, types } = require('pg');

// bigint ids/counters come back as strings by default; all our values fit in a JS number.
types.setTypeParser(20, (v) => parseInt(v, 10));

const PORT = Number(process.env.PORT || 3000);
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.on('error', (err) => console.error('pg pool error', err));

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;
const MAX_TEXT = 1000;
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
  if (query.limit !== undefined) {
    limit = Number(query.limit);
    if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
      throw new HttpError(400, `limit must be an integer between 1 and ${MAX_LIMIT}`);
    }
  }
  let before = MAX_ID;
  if (query.before !== undefined) {
    before = parseId(query.before);
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
  const header = req.get('x-user-id');
  return header === undefined ? null : parseId(header);
}

function requireUser(req, res, next) {
  const userId = optionalUser(req);
  if (userId === null) return next(new HttpError(401, 'missing or invalid X-User-Id'));
  req.userId = userId;
  next();
}

// --- Server timing -------------------------------------------------------------------------------------------
const nowMs = () => Number(process.hrtime.bigint()) / 1e6;

// First middleware: start the clock and emit Server-Timing just before the headers go out (also on errors).
function serverTiming(req, res, next) {
  const timing = { start: nowMs(), conn: 0, db: 0 };
  req.timing = timing;
  const writeHead = res.writeHead;
  res.writeHead = function timedWriteHead(...args) {
    const total = nowMs() - timing.start;
    const app = Math.max(0, total - timing.conn - timing.db);
    this.setHeader('Server-Timing',
      `conn;dur=${timing.conn.toFixed(1)}, db;dur=${timing.db.toFixed(1)}, ` +
      `app;dur=${app.toFixed(1)}, total;dur=${total.toFixed(1)}`);
    return writeHead.apply(this, args);
  };
  next();
}

// --- Database access ---------------------------------------------------------------------------------------------
// One pooled connection per request, returned to the pool before the response is sent. `fn` receives a query
// wrapper that adds each query's duration to req.timing.db; time waiting for a pooled connection (or opening a new
// one while the pool fills) goes to req.timing.conn.
async function withClient(req, fn) {
  const timing = req.timing;
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
        return await client.query(text, params);
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

const app = express();
app.use(serverTiming);
app.use(express.json());

app.get('/health', async (req, res) => {
  await withClient(req, (db) => db.query('SELECT 1'));
  res.json({ status: 'ok' });
});

app.get('/posts', async (req, res) => {
  const { limit, before } = pageParams(req.query);
  const { rows } = await withClient(req, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.is_public AND p.id < $1 ORDER BY p.id DESC LIMIT $2`,
    [before, limit],
  ));
  res.json(page(rows, limit));
});

app.get('/posts/:id', async (req, res) => {
  const postId = requireId(req.params.id);
  const viewer = optionalUser(req);
  const body = await withClient(req, async (db) => {
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
  res.json(body);
});

app.get('/users/:id/posts', async (req, res) => {
  const userId = requireId(req.params.id);
  const { limit, before } = pageParams(req.query);
  const { rows } = await withClient(req, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.user_id = $1 AND p.is_public AND p.id < $2 ORDER BY p.id DESC LIMIT $3`,
    [userId, before, limit],
  ));
  res.json(page(rows, limit));
});

app.get('/me/posts', requireUser, async (req, res) => {
  const { limit, before } = pageParams(req.query);
  const { rows } = await withClient(req, (db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.user_id = $1 AND p.id < $2 ORDER BY p.id DESC LIMIT $3`,
    [req.userId, before, limit],
  ));
  res.json(page(rows, limit));
});

app.post('/posts', requireUser, async (req, res) => {
  const text = validText(req.body);
  const isPublic = req.body.is_public === undefined ? true : req.body.is_public;
  if (typeof isPublic !== 'boolean') throw new HttpError(400, 'is_public must be a boolean');
  const { rows } = await withClient(req, (db) => db.query(
    `WITH p AS (
       INSERT INTO posts (user_id, text, is_public) VALUES ($1, $2, $3) RETURNING *
     )
     SELECT ${POST_COLUMNS} FROM p JOIN users u ON u.id = p.user_id`,
    [req.userId, text, isPublic],
  ));
  res.status(201).json({ post: rows[0] });
});

app.post('/posts/:id/like', requireUser, async (req, res) => {
  const postId = requireId(req.params.id);
  // Insert the like only if the post exists; bump the counter only if the like is new. The outer SELECT sees the
  // snapshot from before the statement, so a new like's count comes from `upd`, an existing like's from `posts`.
  const { rows } = await withClient(req, (db) => db.query(
    `WITH ins AS (
       INSERT INTO likes (post_id, user_id) SELECT id, $2::bigint FROM posts WHERE id = $1
       ON CONFLICT DO NOTHING RETURNING post_id
     ), upd AS (
       UPDATE posts SET like_count = like_count + 1 FROM ins WHERE posts.id = ins.post_id RETURNING posts.like_count
     )
     SELECT COALESCE((SELECT like_count FROM upd), (SELECT like_count FROM posts WHERE id = $1)) AS like_count`,
    [postId, req.userId],
  ));
  if (rows[0].like_count === null) throw new HttpError(404, 'not found');
  res.json({ liked: true, like_count: rows[0].like_count });
});

app.delete('/posts/:id/like', requireUser, async (req, res) => {
  const postId = requireId(req.params.id);
  const { rows } = await withClient(req, (db) => db.query(
    `WITH del AS (
       DELETE FROM likes WHERE post_id = $1 AND user_id = $2 RETURNING post_id
     ), upd AS (
       UPDATE posts SET like_count = like_count - 1 FROM del WHERE posts.id = del.post_id RETURNING posts.like_count
     )
     SELECT COALESCE((SELECT like_count FROM upd), (SELECT like_count FROM posts WHERE id = $1)) AS like_count`,
    [postId, req.userId],
  ));
  if (rows[0].like_count === null) throw new HttpError(404, 'not found');
  res.json({ liked: false, like_count: rows[0].like_count });
});

app.post('/posts/:id/comments', requireUser, async (req, res) => {
  const postId = requireId(req.params.id);
  const text = validText(req.body);
  // Unknown post or user fails the comments foreign keys (23503), as before.
  const { rows } = await withClient(req, (db) => db.query(
    `WITH c AS (
       INSERT INTO comments (post_id, user_id, text) VALUES ($1, $2, $3)
       RETURNING id, post_id, user_id, text, created_at
     ), upd AS (
       UPDATE posts SET comment_count = comment_count + 1 FROM c WHERE posts.id = c.post_id
     )
     SELECT * FROM c`,
    [postId, req.userId, text],
  ));
  res.status(201).json({ comment: rows[0] });
});

app.use((req, res) => {
  res.status(404).json({ error: 'not found' });
});

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  if (err instanceof HttpError) return res.status(err.status).json({ error: err.message });
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'invalid JSON' });
  if (err.code === '23503') {
    // Foreign key violation: unknown post -> 404, unknown acting user -> 401.
    if (/user_id/.test(err.constraint || '')) return res.status(401).json({ error: 'unknown user' });
    return res.status(404).json({ error: 'not found' });
  }
  console.error(err);
  res.status(500).json({ error: 'internal error' });
});

const server = app.listen(PORT, () => console.log(`node-express listening on :${PORT}`));

function shutdown() {
  server.close(() => pool.end().then(() => process.exit(0)));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
