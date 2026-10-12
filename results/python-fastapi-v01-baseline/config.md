# python-fastapi-v01-baseline

## Summary
**Capacity: 60 VUs at 29.9 req/s (1,793 req/min)**, steady p50 115 ms / p95 490 ms / p99 619 ms, 0 % errors (not
marginal: p95 and p99 38–39 % under their limits). The first failing level is **70 VUs**: 32.2 req/s, p95 1006 ms /
p99 1182 ms (limits 800 / 1000), still 0 % errors. At 100 VUs: 35.8 req/s, p50 955 ms. **Python's no-pool baseline
reaches 60 % of node-express v01's capacity** (100 VUs / 46.7 req/s, same design: no pool, no cache, one connection
per request).

- **The bottleneck is the CPU, and most of the wait is connection setup, as on Node.** CPU 87 % at 60 VUs, 93 % at
  70 VUs and 100 % at 100 VUs, steal ≤ 0.2 %. Server time at 60 VUs p50 109 ms = `conn` (connect + SCRAM auth +
  close) 82 ms + `db` 24 ms + `app` 1.8 ms. Past the edge the wait grows almost entirely in `conn` (p95 365 → 739 →
  1273 ms at 60 / 70 / 100 VUs): every request makes Postgres start a backend process and check a SCRAM password.
- **Python costs ≈ 75 % more app CPU per request than Node, and Postgres ≈ 25 % more.** At 60 VUs Python used 36 %
  and Postgres 49 % of the vCPU at 29.9 req/s: ≈ 12.1 ms (Python) + 16.3 ms (Postgres) per request, 29 ms in total.
  node-express v01 at 100 VUs: Node 32 % / Postgres 61 % at 46.7 req/s ≈ 6.9 + 13.1 ms, 21 ms in total (no host-speed
  probe existed then; this run's probe was 80–112 ms, around normal). Python's share: pure-Python asyncio loop and
  h11 parser, FastAPI routing + `jsonable_encoder`, asyncpg's connect/auth. The higher Postgres cost is likely
  asyncpg's protocol: it prepares every query (Parse + Describe, then Bind + Execute) on the fresh connection, where
  node-postgres sent unnamed parameterised queries in one round trip.
- **Memory is not a constraint.** Peak 449 MB used (100 VUs), Python PSS ≤ 65 MB, Postgres ≤ 71 MB, no swap.
- **No errors and no `too many clients`:** connections stay short-lived, at most one per VU (≤ 100).
- **The load generator is not a factor:** ≤ 2.3 % CPU on average, k6 RSS ≤ 93 MB.
- **Next:** `python-fastapi-v02-pool` — an asyncpg pool (max 10), the only change. On Node the pool removed the
  per-request connect + auth (≈ 80 % of server time) and lifted capacity from 100 to 1350 VUs.

## What changed vs. the previous tag
New stack `apps/python-fastapi/`, no parent (first Python tag). The design matches **node-express v01** (the Node
baseline): one process, **no connection pool** (a new asyncpg connection per request, closed before the response is
sent; `conn` = connect + auth + close), **no feed cache**, writes as one CTE statement (as in every current stack),
`Server-Timing` on every response. Idiomatic FastAPI: route decorators, handlers return dicts that FastAPI encodes
(`jsonable_encoder` + `json.dumps`). Path, query and body parsing are done by hand so status codes and error bodies
match the other stacks (FastAPI's own validation would answer 422 with a different body); unknown routes and methods
answer 404 `{"error":"not found"}`; `/docs` and `/openapi.json` are off. `Server-Timing` comes from a plain ASGI
middleware (outermost app middleware), which also ignores trailing slashes like the JavaScript routers. The parity
check (39 requests on a fresh DB) gave responses identical to the node-http reference. App code from commit `d21ccdf`.

## Full configuration
- App: `apps/python-fastapi` — FastAPI 0.143.0 (Starlette 1.7.0, Pydantic 2.14.1), asyncpg 0.32.0, plain SQL, no
  ORM; all dependencies pinned in `requirements.txt` (app code from commit `d21ccdf`)
- Runtime: CPython 3.12.3 (Ubuntu 24.04 system Python, venv), uvicorn 0.54.0 **without extras**: asyncio event loop
  (no uvloop), h11 HTTP parser (no httptools), `--no-access-log`, keep-alive timeout 5 s (default)
- App processes/workers: 1 (uvicorn single process, systemd `bench-app`)
- DB connections: **no pool**, one new connection per request (connect + SCRAM auth + close)
- Queries: asyncpg default (every query prepared on its connection; the statement cache is useless with fresh
  connections)
- Writes: single statement (CTE), no explicit transactions
- Cache: none
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (nginx installed but disabled)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2

## Results
Levels chosen by the user: 100 (node-express v01's capacity), then 70, then 60.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **60** | **PASS** | **29.9** | **115.2** | **490.0** | **618.8** | 0.00 | 109.1 / 456.5 | 82.0 / 364.8 | 23.5 / 92.0 | 86.9 (36.3 / 48.6) | 29.1 | 90 / 84 | 397 |
| 70 | FAIL (p95, p99) | 32.2 | 213.2 | 1006.0 | 1182.4 | 0.00 | 199.3 / 934.5 | 156.2 / 739.2 | 39.3 / 181.2 | 92.6 (38.5 / 51.8) | 28.8 | 86 / 112 | 414 |
| 100 | FAIL (p50, p95, p99) | 35.8 | 954.8 | 1721.6 | 1969.3 | 0.00 | 885.9 / 1606.9 | 713.6 / 1273.2 | 155.6 / 346.2 | 100.0 (40.3 / 56.4) | 28.0 | 80 / 88 | 449 |

**Capacity: 60 VUs at 29.9 req/s.** First fail: 70 VUs. node-express v01 (no pool, Node 24 + Express): 100 VUs PASS
at 46.7 req/s (marginal), 110 VUs FAIL at 49.8 req/s.

## Observations
- CPU per request is flat across levels (28–29 ms), so throughput is capped by the CPU at ≈ 34–36 req/s; the 70 VUs
  offer ≈ 35 req/s, right at that ceiling, and the queue shows up in `conn`.
- 70 VUs: the host slowed during the run (probe 86 → 112 ms) and the CPU dipped to 63 % at times; p50 213 ms was
  well under its limit and only the tail failed. On a fast host 70 might pass, but 60 → 70 is a 17 % step and the
  next tag changes the picture anyway.
- `app` time stays ≈ 2 ms p50 / 5–6 ms p95 at every level: FastAPI's own work per request is small next to
  connection setup, but it runs on the same single vCPU as Postgres's backend start-up.
- Time outside the app (client − server): p50 6 / 14 / 69 ms at 60 / 70 / 100 VUs — at 100 VUs requests also wait in
  the event loop and accept queue before the middleware starts the clock.
- `app_log_tail.txt` has no errors at any level.

## Next idea
`python-fastapi-v02-pool` (parent v01): `asyncpg.create_pool(max_size=10)`, one pooled connection per request, the
only change (prepared statements are then cached per pooled connection). Start near the expected order of magnitude
(Node v02: 1350 VUs; Python's higher app CPU per request suggests well below that, e.g. 400–800 VUs).
