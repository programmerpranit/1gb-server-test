# python-fastapi-v02-pool

## Summary
**Capacity: 600 VUs at 306.9 req/s (18,414 req/min)**, steady p50 43 ms / p95 435 ms / p99 863 ms, 0 % errors (p99
14 % under its limit). The first failing level is **650 VUs**: 297.8 req/s, p95 1153 ms / p99 2016 ms, still 0 %
errors, on a normal-speed host (probe 85 ms). **10× the VUs of v01** (60 VUs / 29.9 req/s) from one change, the
pool. node-express v02 (the same step on Node + Express) reached 1350 VUs / 619 req/s: Python with a pool is at
≈ 45 % of Node's capacity.

- **The pool removes connection setup: CPU per request 29 → 3.1–3.5 ms** (≈ 9× less). Postgres no longer starts a
  backend and checks a SCRAM password per request; its share falls from 49 % to ≈ 23–27 % of the vCPU.
- **The ceiling is ≈ 300 req/s, and it is the CPU spent in Python.** At 650 VUs the vCPU is at 99 % (never below
  91 %), Python 67 % / Postgres 27 % (ratio 2.5; node-express v02: 0.84). Going from 600 to 650 VUs adds no
  throughput (306.9 → 297.8 req/s); the extra load only queues. Python spends ≈ 2.1–2.3 ms per request (pure-Python
  asyncio loop, h11 parser, Starlette/FastAPI routing and `jsonable_encoder`, asyncpg), Postgres ≈ 0.85–0.9 ms.
- **Overload shows up as pool wait, not query time.** `conn` p95 399 ms at 600 VUs and 1110 ms at 650; `db` p95
  stays 21–29 ms at every level; `app` p95 ≈ 2 ms. 0 % errors at every level.
- **Memory is not a constraint.** Peak 469 MB used, Python PSS ≤ 76 MB, Postgres ≤ 113 MB, no swap.
- **The load generator is not a factor:** ≈ 12–13 % CPU on average (peak 60 %), time outside the app p95 ≤ 23 ms.
- **Next:** `python-fastapi-v03-feed-cache-1s` (user's choice) — the 1 s in-process cache of `GET /posts` with
  single-flight, ported from node-http. On Node it took capacity from 1400 to 3000 VUs; with Python's app CPU the
  dominant cost, skipping DB access and JSON encoding for ≈ 47 % of requests should matter even more.

## What changed vs. the previous tag
Parent: `python-fastapi-v01-baseline`. One change: **a connection pool** — `asyncpg.create_pool(min_size=10,
max_size=10)` created at startup (FastAPI lifespan), instead of a new connection per request. Every request acquires
one connection for all its queries and releases it before the response is sent. asyncpg's pool defaults otherwise:
on release it runs the reset query (`SELECT pg_advisory_unlock_all(); CLOSE ALL; UNLISTEN *; RESET ALL;`, one round
trip), and prepared statements are cached per connection (100 statements). `conn` now measures pool acquire (waiting
for a free connection) plus release. The 10 connections are opened at startup (asyncpg's default `min_size=10`);
the Node pools opened them on demand. The parity check gave responses identical to the node-http reference. App code
from commit `57434bf`.

## Full configuration
- App: `apps/python-fastapi` — FastAPI 0.143.0 (Starlette 1.7.0, Pydantic 2.14.1), asyncpg 0.32.0, plain SQL, no
  ORM; dependencies pinned in `requirements.txt` (app code from commit `57434bf`)
- Runtime: CPython 3.12.3 (system, venv), uvicorn 0.54.0 without extras: asyncio event loop, h11 parser,
  `--no-access-log`
- App processes/workers: 1 (uvicorn single process, systemd `bench-app`)
- DB connections: **asyncpg pool, min 10 / max 10**, one connection per request, reset query on release
- Queries: prepared (asyncpg statement cache per pooled connection)
- Writes: single statement (CTE), no explicit transactions
- Cache: none
- Server timing: `Server-Timing: conn, db, app, total` on every response (`conn` = acquire + release)
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (nginx installed but disabled)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2

## Results
Levels chosen by the user: 500, 400, 450, 500 again (the rerun replaces the first run in `vus-500/`), 600, 650.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 400 | PASS | 211.9 | 17.8 | 199.2 | 384.4 | 0.00 | 13.5 / 176.2 | 6.8 / 154.0 | 5.5 / 27.1 | 83.8 (56.0 / 22.0) | 3.96 | 95 / 104 | 455 |
| 450 | PASS | 239.8 | 16.0 | 104.3 | 245.7 | 0.00 | 12.2 / 82.9 | 6.3 / 61.3 | 4.8 / 20.8 | 84.0 (56.6 / 22.5) | 3.50 | 92 / 101 | 459 |
| 500 | PASS (rerun) | 266.1 | 20.2 | 114.0 | 193.8 | 0.00 | 15.3 / 95.4 | 8.3 / 77.4 | 5.7 / 21.0 | 86.7 (58.5 / 23.5) | 3.26 | 94 / 86 | 462 |
| **600** | **PASS** | **306.9** | **42.6** | **434.6** | **862.6** | 0.00 | 32.6 / 415.1 | 19.7 / 398.7 | 9.2 / 23.7 | 94.3 (63.6 / 26.0) | 3.07 | 123 / 91 | 463 |
| 650 | FAIL (p95, p99) | 297.8 | 168.7 | 1152.8 | 2015.9 | 0.00 | 154.1 / 1130.5 | 139.5 / 1109.7 | 12.9 / 28.9 | 99.2 (67.3 / 27.0) | 3.33 | 85 / 86 | 469 |

**Capacity: 600 VUs at 306.9 req/s.** First fail: 650 VUs. Parent v01: 60 VUs / 29.9 req/s (first fail 70).
node-express v02 (pool on Node): 1350 VUs / 619 req/s, first fail 1400.

## Observations
- 500 VUs, first run (replaced by the rerun): FAIL on p99 only — 246.8 req/s, p50 34 / p95 517 / p99 4363 ms, CPU
  91.6 % (Python 61.8 / PG 24.4), 3.71 ms CPU/req, probe 111 / 85 ms. A ≈ 6 s stretch at 100 % CPU (app CPU up to
  78 %) built a queue with pool waits up to 6.3 s. The rerun on a faster host (probe 94 ms, 3.26 ms CPU/req) passed
  with p99 194 ms; 450 also passed with a better tail than 400. Near the edge single runs swing with host speed.
- 600 VUs passed although the host was slow at the start (probe 123 ms before, 91 after).
- `app` p95 stays ≈ 2 ms at every level: per-request Python work is small, but ≈ 2.2 ms of CPU per request across
  the event loop, HTTP parsing and the framework is what saturates the vCPU at ≈ 300 req/s.
- Time outside the app (client − server): p50 4–15 ms, p95 19–23 ms at every level.
- `app_log_tail.txt` has no errors at any level.

## Next idea
`python-fastapi-v03-feed-cache-1s` (parent v02): in-process cache of `GET /posts` (all pages, key limit + before,
TTL 1 s, single-flight, cached as the encoded JSON body), the only change — the same cache as node-express v06 /
node-http. Then uvloop + httptools, orjson, more workers.
