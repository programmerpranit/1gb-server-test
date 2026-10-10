'use strict';

// Baseline implementation of the protocol v1 API (see CLAUDE.md "API contract").
// Deliberately plain: Express defaults, one process, NO connection pool — every request opens its own
// Postgres connection and closes it when done. One query per step.

const express = require('express');
const { Client, types } = require('pg');

// bigint ids/counters come back as strings by default; all our values fit in a JS number.
types.setTypeParser(20, (v) => parseInt(v, 10));

const PORT = Number(process.env.PORT || 3000);
const DATABASE_URL = process.env.DATABASE_URL;

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

// One fresh connection per request, closed before the response is sent.
async function withClient(fn) {
  const client = new Client({ connectionString: DATABASE_URL });
  client.on('error', (err) => console.error('pg client error', err));
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.end().catch(() => {});
  }
}

async function withTransaction(fn) {
  return withClient(async (client) => {
    await client.query('BEGIN');
    try {
      const result = await fn(client);
      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      throw err;
    }
  });
}

const app = express();
app.use(express.json());

app.get('/health', async (req, res) => {
  await withClient((db) => db.query('SELECT 1'));
  res.json({ status: 'ok' });
});

app.get('/posts', async (req, res) => {
  const { limit, before } = pageParams(req.query);
  const { rows } = await withClient((db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.is_public AND p.id < $1 ORDER BY p.id DESC LIMIT $2`,
    [before, limit],
  ));
  res.json(page(rows, limit));
});

app.get('/posts/:id', async (req, res) => {
  const postId = requireId(req.params.id);
  const viewer = optionalUser(req);
  const body = await withClient(async (db) => {
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
  const { rows } = await withClient((db) => db.query(
    `SELECT ${POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
     WHERE p.user_id = $1 AND p.is_public AND p.id < $2 ORDER BY p.id DESC LIMIT $3`,
    [userId, before, limit],
  ));
  res.json(page(rows, limit));
});

app.get('/me/posts', requireUser, async (req, res) => {
  const { limit, before } = pageParams(req.query);
  const { rows } = await withClient((db) => db.query(
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
  const { rows } = await withClient((db) => db.query(
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
  const likeCount = await withTransaction(async (client) => {
    const inserted = await client.query(
      'INSERT INTO likes (post_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING',
      [postId, req.userId],
    );
    const { rows } = inserted.rowCount
      ? await client.query('UPDATE posts SET like_count = like_count + 1 WHERE id = $1 RETURNING like_count', [postId])
      : await client.query('SELECT like_count FROM posts WHERE id = $1', [postId]);
    if (!rows[0]) throw new HttpError(404, 'not found');
    return rows[0].like_count;
  });
  res.json({ liked: true, like_count: likeCount });
});

app.delete('/posts/:id/like', requireUser, async (req, res) => {
  const postId = requireId(req.params.id);
  const likeCount = await withTransaction(async (client) => {
    const deleted = await client.query('DELETE FROM likes WHERE post_id = $1 AND user_id = $2', [postId, req.userId]);
    const { rows } = deleted.rowCount
      ? await client.query('UPDATE posts SET like_count = like_count - 1 WHERE id = $1 RETURNING like_count', [postId])
      : await client.query('SELECT like_count FROM posts WHERE id = $1', [postId]);
    if (!rows[0]) throw new HttpError(404, 'not found');
    return rows[0].like_count;
  });
  res.json({ liked: false, like_count: likeCount });
});

app.post('/posts/:id/comments', requireUser, async (req, res) => {
  const postId = requireId(req.params.id);
  const text = validText(req.body);
  const comment = await withTransaction(async (client) => {
    const { rows } = await client.query(
      `INSERT INTO comments (post_id, user_id, text) VALUES ($1, $2, $3)
       RETURNING id, post_id, user_id, text, created_at`,
      [postId, req.userId, text],
    );
    await client.query('UPDATE posts SET comment_count = comment_count + 1 WHERE id = $1', [postId]);
    return rows[0];
  });
  res.status(201).json({ comment });
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
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
