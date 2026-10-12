# Implementation of the protocol v2 API (see CLAUDE.md "API contract") with FastAPI on uvicorn.
# Deliberately plain, like node-express v02: one process, an asyncpg pool with default settings except max_size
# (min 10, max 10; every request acquires one connection for all its queries and releases it when done).
# GET /posts (global feed) is cached in process for 1 s (see "Global feed cache"), as in node-express v06 / node-http.
# Writes that touch two tables (like + counter, comment + counter) are ONE statement with data-modifying CTEs, as in
# every other stack. asyncpg prepares every query and caches the prepared statement per pooled connection.
# Idiomatic FastAPI: route decorators, handlers return dicts (FastAPI encodes them with jsonable_encoder + json).
# Path/query/body parsing is done by hand so status codes and error messages match the other stacks exactly
# (FastAPI's own validation would answer 422 with a different body). /docs and /openapi.json are off.
# Every response carries a Server-Timing header: conn (pool acquire + release), db (queries), app (the rest), total.

import asyncio
import json
import os
import re
import time
import traceback
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

DATABASE_URL = os.environ["DATABASE_URL"]

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_TEXT = 1000
MAX_BODY = 100 * 1024
MAX_ID = 9223372036854775807

POST_COLUMNS = "p.id, p.user_id, u.handle, p.text, p.is_public, p.like_count, p.comment_count, p.created_at"


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class JSON(JSONResponse):
    # Same Content-Type as the other stacks (Starlette's default has no charset). Starlette renders compact JSON
    # (separators "," and ":", non-ASCII as UTF-8), like JSON.stringify.
    media_type = "application/json; charset=utf-8"


def error(status, message):
    return JSON({"error": message}, status_code=status)


# --- Parsing helpers (same rules as the JavaScript stacks) ---------------------------------------------------------
ID_RE = re.compile(r"[1-9][0-9]{0,17}")
# JavaScript Number(): surrounding whitespace ignored, decimal literals incl. exponent, 0x/0o/0b integers, '' -> 0.
JS_DECIMAL_RE = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
JS_RADIX_RE = re.compile(r"0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+")


def js_number(value):
    s = value.strip()
    if s == "":
        return 0.0
    if JS_DECIMAL_RE.fullmatch(s):
        return float(s)
    if JS_RADIX_RE.fullmatch(s):
        return float(int(s, 0))
    return float("nan")


def parse_id(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        return None
    return int(value)


def require_id(value):
    id_ = parse_id(value)
    if id_ is None:
        raise HttpError(404, "not found")
    return id_


def first_param(request, name):
    # URLSearchParams.get(): the first value (Starlette's .get() returns the last one).
    values = request.query_params.getlist(name)
    return values[0] if values else None


def page_params(request):
    limit = DEFAULT_LIMIT
    raw_limit = first_param(request, "limit")
    if raw_limit is not None:
        n = js_number(raw_limit)
        if not n.is_integer() or n < 1 or n > MAX_LIMIT:
            raise HttpError(400, f"limit must be an integer between 1 and {MAX_LIMIT}")
        limit = int(n)
    before = MAX_ID
    raw_before = first_param(request, "before")
    if raw_before is not None:
        before = parse_id(raw_before)
        if before is None:
            raise HttpError(400, "before must be a positive integer")
    return limit, before


def page(rows, limit):
    return {"posts": rows, "next_before": rows[-1]["id"] if len(rows) == limit else None}


def valid_text(body):
    text = body.get("text") if isinstance(body, dict) else None
    # Length in UTF-16 code units, like JavaScript's String.length.
    if not isinstance(text, str) or text.strip() == "" or len(text.encode("utf-16-le")) // 2 > MAX_TEXT:
        raise HttpError(400, f"text must be 1..{MAX_TEXT} characters")
    return text


# Acting user from X-User-Id (simulated auth).
def optional_user(request):
    header = request.headers.get("x-user-id")
    return None if header is None else parse_id(header)


def require_user(request):
    user_id = optional_user(request)
    if user_id is None:
        raise HttpError(401, "missing or invalid X-User-Id")
    return user_id


# Request body as JSON (like express.json: only for JSON content types, 100 kB limit; otherwise an empty object).
async def read_json(request):
    if "json" not in request.headers.get("content-type", ""):
        return {}
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HttpError(413, "request entity too large")
    if len(raw) == 0:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        raise HttpError(400, "invalid JSON")


# created_at as JavaScript's Date.toISOString(): UTC, milliseconds, "Z" (asyncpg returns timestamptz in UTC).
def iso(dt):
    return f"{dt:%Y-%m-%dT%H:%M:%S}.{dt.microsecond // 1000:03d}Z"


def to_json(record):
    row = dict(record)
    row["created_at"] = iso(row["created_at"])
    return row


# --- Server timing -------------------------------------------------------------------------------------------------
def now_ms():
    return time.perf_counter() * 1000


class Timing:
    __slots__ = ("start", "conn", "db")

    def __init__(self):
        self.start = now_ms()
        self.conn = 0.0
        self.db = 0.0


class ServerTiming:
    """Outermost app middleware (plain ASGI): starts the clock, adds Server-Timing when the response starts (also on
    errors), turns unhandled exceptions into 500 {"error": "internal error"}. Also normalises the path like the
    JavaScript router: empty segments and a trailing slash are ignored (/posts/ is /posts, no redirect)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        timing = scope["timing"] = Timing()
        path = scope["path"]
        if path.endswith("/") or "//" in path:
            scope["path"] = "/" + "/".join(s for s in path.split("/") if s)
        started = False

        async def send_timed(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                total = now_ms() - timing.start
                app = max(0.0, total - timing.conn - timing.db)
                value = (f"conn;dur={timing.conn:.1f}, db;dur={timing.db:.1f}, "
                         f"app;dur={app:.1f}, total;dur={total:.1f}")
                message["headers"] = [*message.get("headers", ()), (b"Server-Timing", value.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_timed)
        except Exception:
            traceback.print_exc()
            if started:
                raise
            await error(500, "internal error")(scope, receive, send_timed)


# --- Database access -----------------------------------------------------------------------------------------------
# One pooled connection per request, released before the response is sent. The handler gets a wrapper whose fetch()
# adds each query's duration to timing.db; time waiting for a free connection, and the release (asyncpg's pool runs
# its reset query, one round trip, before the connection can be reused), go to timing.conn.
pool = None


@asynccontextmanager
async def lifespan(app):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=10, max_size=10)
    janitor = asyncio.create_task(feed_cache_janitor())
    try:
        yield
    finally:
        janitor.cancel()
        await pool.close()


class Db:
    __slots__ = ("conn", "timing")

    def __init__(self, conn, timing):
        self.conn = conn
        self.timing = timing

    async def fetch(self, query, *args):
        start = now_ms()
        try:
            return await self.conn.fetch(query, *args)
        finally:
            self.timing.db += now_ms() - start


@asynccontextmanager
async def connection(request):
    timing = request.scope["timing"]
    start = now_ms()
    try:
        conn = await pool.acquire()
    finally:
        timing.conn += now_ms() - start
    try:
        yield Db(conn, timing)
    finally:
        start = now_ms()
        await pool.release(conn)
        timing.conn += now_ms() - start


# --- Global feed cache ---------------------------------------------------------------------------------------------
# GET /posts responses (encoded JSON) are cached in process for FEED_CACHE_TTL_S, keyed by (limit, before).
# Trade-off: the global feed may be up to one TTL stale (new posts, like/comment counts). Concurrent misses for the
# same key share one query (single-flight, an asyncio task): the request that starts it records conn/db time, the
# ones waiting on it record their wait as app time. Hit/miss counts are logged every 10 s while there is traffic.
FEED_CACHE_TTL_S = 1.0
feed_cache = {}  # (limit, before) -> (expires, task resolving to the body bytes)
feed_stats = {"hit": 0, "miss": 0}


async def feed_cache_janitor():
    while True:
        await asyncio.sleep(10)
        now = time.monotonic()
        for key in [k for k, (expires, _) in feed_cache.items() if expires <= now]:
            del feed_cache[key]
        if feed_stats["hit"] + feed_stats["miss"] > 0:
            print(f"feed cache: hit={feed_stats['hit']} miss={feed_stats['miss']} keys={len(feed_cache)}")
            feed_stats["hit"] = feed_stats["miss"] = 0


async def load_feed(request, limit, before):
    async with connection(request) as db:
        rows = await db.fetch(f"""
            SELECT {POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.is_public AND p.id < $1 ORDER BY p.id DESC LIMIT $2""", before, limit)
    # Encoded like Starlette's JSONResponse.render.
    return json.dumps(page([to_json(r) for r in rows], limit), ensure_ascii=False, separators=(",", ":")).encode()


def cached_feed(request, limit, before):
    key = (limit, before)
    now = time.monotonic()
    entry = feed_cache.get(key)
    if entry is not None and entry[0] > now:
        feed_stats["hit"] += 1
        return entry[1]
    feed_stats["miss"] += 1
    task = asyncio.ensure_future(load_feed(request, limit, before))
    fresh = (now + FEED_CACHE_TTL_S, task)
    feed_cache[key] = fresh

    # A failed query is not cached: the waiting requests get the error, the next request retries.
    def drop_failed(t):
        if (t.cancelled() or t.exception() is not None) and feed_cache.get(key) is fresh:
            del feed_cache[key]

    task.add_done_callback(drop_failed)
    return task


# --- App -----------------------------------------------------------------------------------------------------------
app = FastAPI(default_response_class=JSON, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(ServerTiming)


@app.exception_handler(HttpError)
async def http_error(request, exc):
    return error(exc.status, exc.message)


# Unknown route or method: 404 {"error": "not found"} (the other stacks have no 405).
@app.exception_handler(StarletteHTTPException)
async def not_found(request, exc):
    return error(404, "not found")


# Foreign key violation: unknown post -> 404, unknown acting user -> 401.
@app.exception_handler(asyncpg.ForeignKeyViolationError)
async def foreign_key(request, exc):
    if "user_id" in (exc.constraint_name or ""):
        return error(401, "unknown user")
    return error(404, "not found")


@app.get("/health")
async def health(request: Request):
    async with connection(request) as db:
        await db.fetch("SELECT 1")
    return {"status": "ok"}


@app.get("/posts")
async def global_feed(request: Request):
    limit, before = page_params(request)
    return Response(await cached_feed(request, limit, before), media_type=JSON.media_type)


@app.get("/posts/{post_id}")
async def get_post(request: Request, post_id: str):
    post_id = require_id(post_id)
    viewer = optional_user(request)
    async with connection(request) as db:
        posts = await db.fetch(f"""
            SELECT {POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id WHERE p.id = $1""", post_id)
        post = posts[0] if posts else None
        if post is None or (not post["is_public"] and post["user_id"] != viewer):
            raise HttpError(404, "not found")
        comments = await db.fetch("""
            SELECT id, post_id, user_id, text, created_at FROM comments
            WHERE post_id = $1 ORDER BY id DESC LIMIT 20""", post_id)
    return {"post": to_json(post), "comments": [to_json(c) for c in comments]}


@app.get("/users/{user_id}/posts")
async def user_posts(request: Request, user_id: str):
    user_id = require_id(user_id)
    limit, before = page_params(request)
    async with connection(request) as db:
        rows = await db.fetch(f"""
            SELECT {POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.user_id = $1 AND p.is_public AND p.id < $2 ORDER BY p.id DESC LIMIT $3""",
                              user_id, before, limit)
    return page([to_json(r) for r in rows], limit)


@app.get("/me/posts")
async def my_posts(request: Request):
    user_id = require_user(request)
    limit, before = page_params(request)
    async with connection(request) as db:
        rows = await db.fetch(f"""
            SELECT {POST_COLUMNS} FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.user_id = $1 AND p.id < $2 ORDER BY p.id DESC LIMIT $3""", user_id, before, limit)
    return page([to_json(r) for r in rows], limit)


@app.post("/posts", status_code=201)
async def create_post(request: Request):
    user_id = require_user(request)
    body = await read_json(request)
    text = valid_text(body)
    is_public = body.get("is_public", True)
    if not isinstance(is_public, bool):
        raise HttpError(400, "is_public must be a boolean")
    async with connection(request) as db:
        rows = await db.fetch(f"""
            WITH p AS (
              INSERT INTO posts (user_id, text, is_public) VALUES ($1, $2, $3) RETURNING *
            )
            SELECT {POST_COLUMNS} FROM p JOIN users u ON u.id = p.user_id""", user_id, text, is_public)
    return {"post": to_json(rows[0])}


@app.post("/posts/{post_id}/like")
async def like(request: Request, post_id: str):
    user_id = require_user(request)
    post_id = require_id(post_id)
    # Insert the like only if the post exists; bump the counter only if the like is new. The outer SELECT sees the
    # snapshot from before the statement, so a new like's count comes from `upd`, an existing like's from `posts`.
    async with connection(request) as db:
        rows = await db.fetch("""
            WITH ins AS (
              INSERT INTO likes (post_id, user_id) SELECT id, $2::bigint FROM posts WHERE id = $1
              ON CONFLICT DO NOTHING RETURNING post_id
            ), upd AS (
              UPDATE posts SET like_count = like_count + 1 FROM ins WHERE posts.id = ins.post_id
              RETURNING posts.like_count
            )
            SELECT COALESCE((SELECT like_count FROM upd),
                            (SELECT like_count FROM posts WHERE id = $1)) AS like_count""", post_id, user_id)
    like_count = rows[0]["like_count"]
    if like_count is None:
        raise HttpError(404, "not found")
    return {"liked": True, "like_count": like_count}


@app.delete("/posts/{post_id}/like")
async def unlike(request: Request, post_id: str):
    user_id = require_user(request)
    post_id = require_id(post_id)
    async with connection(request) as db:
        rows = await db.fetch("""
            WITH del AS (
              DELETE FROM likes WHERE post_id = $1 AND user_id = $2 RETURNING post_id
            ), upd AS (
              UPDATE posts SET like_count = like_count - 1 FROM del WHERE posts.id = del.post_id
              RETURNING posts.like_count
            )
            SELECT COALESCE((SELECT like_count FROM upd),
                            (SELECT like_count FROM posts WHERE id = $1)) AS like_count""", post_id, user_id)
    like_count = rows[0]["like_count"]
    if like_count is None:
        raise HttpError(404, "not found")
    return {"liked": False, "like_count": like_count}


@app.post("/posts/{post_id}/comments", status_code=201)
async def comment(request: Request, post_id: str):
    user_id = require_user(request)
    post_id = require_id(post_id)
    text = valid_text(await read_json(request))
    # Unknown post or user fails the comments foreign keys (23503).
    async with connection(request) as db:
        rows = await db.fetch("""
            WITH c AS (
              INSERT INTO comments (post_id, user_id, text) VALUES ($1, $2, $3)
              RETURNING id, post_id, user_id, text, created_at
            ), upd AS (
              UPDATE posts SET comment_count = comment_count + 1 FROM c WHERE posts.id = c.post_id
            )
            SELECT * FROM c""", post_id, user_id, text)
    return {"comment": to_json(rows[0])}
