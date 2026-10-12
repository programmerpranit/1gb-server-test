# 1 GB Server Test

How far can a **$6/month DigitalOcean droplet** (1 vCPU, 1 GB RAM, 25 GB SSD, 1000 GB transfer) go running the same
small social-feed API written in different languages and frameworks, with Postgres on the same box?

Every configuration is hit with the same 2-minute k6 test (60 s ramp from 0 to N virtual users, 60 s hold) and tagged
as a GitHub release with its code and raw results. Methodology, API contract and plan live in [CLAUDE.md](CLAUDE.md).
**Reports with charts for every configuration: <https://programmerpranit.github.io/1gb-server-test/>**

## Capacity per configuration

A run **passes** when, during the 60 s steady phase, **p50 < 500 ms, p95 < 800 ms and p99 < 1000 ms**, and the
whole-run **error rate is < 1 %**. VU levels for each configuration are chosen by hand
(`scripts/run_test.sh <tag> <vus...>`; an automatic ladder + bisection exists behind `--search`). **Capacity** is
the highest passing VU level tested; this table is updated automatically. Every run's full data point set is in
[`results/results.csv`](results/results.csv).

<!-- CAPACITY:START -->
| Tag | Stack | What changed | Capacity (VUs) | First fail (VUs) | Steady req/s | Steady req/min | p50 ms | p95 ms | p99 ms | Error % | Peak used MB | Release |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | baseline: no pool, new connection per request, Server-Timing header | 100 | 110 | 46.7 | 2804 | 242.4 | 742.4 | 958.8 | 0 | 446 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline) |
| node-express-v02-pool | node-express | pg.Pool with default settings (max 10) instead of a new connection per request | 1350 | 1400 | 619.1 | 37149 | 324.7 | 689.8 | 775.8 | 0 | 484 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v02-pool) |
| node-express-v03-pool-20 | node-express | pg.Pool max 10 -> 20 | 1200 | 1300 | 574.0 | 34443 | 181.7 | 755.7 | 971.9 | 0 | 513 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v03-pool-20) |
| node-express-v04-cte-writes | node-express | single-statement writes (CTE) instead of BEGIN/queries/COMMIT; parent v02 (pool 10) | 1400 | 1500 | 660.5 | 39631 | 192.8 | 787.7 | 990.5 | 0 | 486 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v04-cte-writes) |
| node-express-v05-prepared | node-express | prepared statements (pg named queries); parent v04 | 1400 | 1500 | 645.1 | 38707 | 319.7 | 675.8 | 801.5 | 0 | 493 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v05-prepared) |
| node-express-v06-feed-cache-1s | node-express | in-process cache of GET /posts (all pages, key limit+before, TTL 1 s, single-flight); parent v05 | 3000 | 3200 | 1541.0 | 92462 | 29.4 | 573.0 | 854.6 | 0 | 541 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v06-feed-cache-1s) |
| node-http-v01-express-v06-port | node-http | port of node-express v06 to plain node:http (no Express, no ETag); same pool, prepared statements, CTE writes, 1 s feed cache | 3200 | 3500 | 1677.6 | 100656 | 10.9 | 392.4 | 835.3 | 0 | 523 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v01-express-v06-port) |
| node-http-v02-bun | node-http | runtime Node 24 -> Bun 1.4.2 (same node:http + pg code); parent node-http v01 | 4200 | 4500 | 2077.8 | 124666 | 46.7 | 752.4 | 850.6 | 0 | 498 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v02-bun) |
| node-http-v03-bun-sql | node-http | Postgres client pg 8.23.1 -> Bun.sql (native); parent node-http v02 | < 4500 | 4500 | - | - | - | - | - | - | - | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v03-bun-sql) |
| node-http-v04-bun-serve | node-http | HTTP server node:http -> Bun.serve; parent node-http v03 (Bun.sql) | 4500 | 4700 | 2324.2 | 139452 | 14.8 | 319.2 | 911.5 | 0 | 464 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v04-bun-serve) |
| python-fastapi-v01-baseline | python-fastapi | new stack: FastAPI baseline, no pool, no feed cache (like node-express v01) | 60 | 70 | 29.9 | 1793 | 115.2 | 490.0 | 618.8 | 0 | 397 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/python-fastapi-v01-baseline) |
| python-fastapi-v02-pool | python-fastapi | asyncpg pool (max 10) instead of a new connection per request; parent v01 | 600 | 650 | 306.9 | 18417 | 42.6 | 434.6 | 862.6 | 0 | 463 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/python-fastapi-v02-pool) |
<!-- CAPACITY:END -->

## Findings

One analysis summary per tag; the full report (summary, configuration, results, observations) is
`results/<tag>/config.md` and is also the GitHub release notes.

- **node-express-v01-baseline** — No pool, new Postgres connection per request. **Capacity 100 VUs / 46.7 req/s**
  (marginal: p99 959 ms); 110 VUs fails on p95 (852 ms). CPU-bound at 98 %; server time p50 227 ms of which **conn
  181 ms** (connect + SCRAM auth), db 38 ms, app 0.5 ms. Memory 446 MB peak, 0 % errors.
  [Report](results/node-express-v01-baseline/config.md)
- **node-express-v02-pool** — `pg.Pool` defaults (max 10). **Capacity 1350 VUs / 619 req/s** (p95 690 ms);
  1400 VUs fails (p50 895 ms). Peak 651 req/s at 1300 VUs; 13× v01. CPU-bound at 100 % (Node ≈ 42 % / Postgres
  ≈ 50 %), ≈ 1.5 ms CPU per request. Past the ceiling, latency is pool wait (`conn` p95 1276 ms at 1400 VUs) while
  queries stay at p95 ≤ 48 ms; 0 % errors at every level. Memory ≤ 509 MB.
  [Report](results/node-express-v02-pool/config.md)
- **node-express-v03-pool-20** — pool `max` 10 → 20. **Worse: capacity 1200 VUs / 574 req/s** (marginal: p99
  972 ms); 1300 VUs fails. CPU-bound as before, but twice as many concurrent queries on 1 vCPU double `db` time
  (p95 83–102 ms vs. 37–48 ms) and time outside the handler (≈ 35 vs. 15 ms). Overload p99 2450 ms at 1500 VUs.
  Keep pool 10. [Report](results/node-express-v03-pool-20/config.md)
- **node-express-v04-cte-writes** — single-statement (CTE) writes instead of BEGIN/COMMIT, pool 10 (parent v02).
  **No measurable gain:** rule capacity 1400 VUs / 660 req/s (marginal) but 1300 and 1350 failed; ≈ 597 vs. 584 req/s
  averaged over the same levels as v02 (+2 %, within noise). ≈ 30 % fewer queries, `db` p95 30–38 vs. 37–48 ms, CPU
  split unchanged. Kept as parent. [Report](results/node-express-v04-cte-writes/config.md)
- **node-express-v05-prepared** — prepared statements (named queries), parent v04. **Capacity 1400 VUs / 645 req/s**;
  1500 fails on p99 (688 req/s). Postgres's CPU share drops (≈ 43.5 vs. 50 %); 655 vs. 606 req/s averaged over
  1300–1500 VUs: likely a 5–10 % gain, within noise. A first 1500-VU pass at 802 req/s came from a ≈ 30 % faster
  host and was replaced by a rerun. [Report](results/node-express-v05-prepared/config.md)
- **node-express-v06-feed-cache-1s** — in-process cache of `GET /posts` (all pages, TTL 1 s, single-flight), parent
  v05; labelled trade-off: global feed up to 1 s stale. **Capacity 3000 VUs / 1541 req/s** (2.4× v05); 3200 fails on
  p99 (1604 req/s). 99.6 % feed hits; CPU per request 0.97 vs. 1.67 ms at 1000 VUs. Still CPU-bound, now Node ≈ 60 % /
  Postgres ≈ 30 %; overload is pool wait again, 0 % errors. [Report](results/node-express-v06-feed-cache-1s/config.md)
- **node-http-v01-express-v06-port** — new stack: node-express v06 on plain `node:http` (no Express, no ETag), same
  pool, queries and 1 s feed cache. **Capacity 3200 VUs / 1678 req/s**; 3500 fails on p99 (1175 ms, 1779 req/s).
  +7 % VUs / +9 % req/s vs. Express v06; Node : Postgres CPU 1.55 vs. 1.93 (≈ 20 % less Node work per request), part
  of the req/s gain is a ≈ 12 % faster host. CPU-bound, 0 % errors. [Report](results/node-http-v01-express-v06-port/config.md)
- **node-http-v02-bun** — node-http v01 on Bun 1.4.2 instead of Node (same code, same `pg` driver). **Capacity
  4200 VUs / 2078 req/s** (near-marginal p95 752 ms; +31 % VUs vs. Node); 4500 fails on p95/p99 at 2097 req/s with the CPU at 100 %: ceiling
  ≈ 2100 req/s. App : Postgres CPU 1.28 vs. 1.48 on Node (≈ 13 % less app work per query); Bun PSS ≤ 113 MB.
  0 % errors. [Report](results/node-http-v02-bun/config.md)
- **node-http-v03-bun-sql** — Bun.sql (native client) instead of `pg`, parent v02. **4500 VUs FAIL** (1955 req/s,
  slow host); app : Postgres CPU 1.22 vs. 1.29: at most ≈ 5 % less app work, no measurable gain. Kept as base for
  `Bun.serve`. [Report](results/node-http-v03-bun-sql/config.md)
- **node-http-v04-bun-serve** — `Bun.serve` instead of `node:http`, parent v03 (Bun.sql). **Capacity 4500 VUs /
  2324 req/s** (p99 912 ms); 4700 fails twice, both on slow hosts (probe 104 / 148 ms vs. 82). App : Postgres CPU 0.91 vs. 1.22:
  ≈ 25 % less app work; Postgres is now the larger share. Bun PSS 59 MB. Best result so far.
  [Report](results/node-http-v04-bun-serve/config.md)
- **python-fastapi-v01-baseline** — new stack: FastAPI + plain uvicorn (asyncio, h11) + asyncpg, 1 process, no pool,
  no cache (same design as node-express v01). **Capacity 60 VUs / 29.9 req/s**, first fail 70 (p99 1182 ms).
  CPU-bound, the wait is connection setup again; ≈ 29 ms CPU per request vs. ≈ 21 ms for Node (Python ≈ 12 ms vs.
  Node ≈ 7 ms, Postgres ≈ 16 vs. 13 ms). [Report](results/python-fastapi-v01-baseline/config.md)
- **python-fastapi-v02-pool** — asyncpg pool (min 10 / max 10), parent v01. **Capacity 600 VUs / 306.9 req/s** (10×
  v01), first fail 650 (no more req/s, CPU 99 %). CPU per request 29 → 3.1–3.5 ms; Python : Postgres CPU 2.5 (Node
  v02: 0.84) — Python's own work is the ceiling. node-express v02: 1350 VUs / 619 req/s.
  [Report](results/python-fastapi-v02-pool/config.md)

_Protocol-v1 results (MacBook load source) were dropped on 2026-10-10; see git history up to commit `e10904b`._

## Next steps

Updated after every test. The plan with all candidates is in [CLAUDE.md](CLAUDE.md#plan).

**Where Node / Bun stands (phase closed):** best configuration `node-http-v04-bun-serve` (Bun 1.4.2, `Bun.serve`,
`Bun.sql`, pool 10, prepared statements, single-statement writes, 1 s in-process cache of the global feed):
**4500 VUs / 2324 req/s**, first fail 4700 (on slow hosts). Path: Express + pool 1400 VUs (v05) → feed cache 3000 (v06) →
plain `node:http` 3200 → Bun 4200 → `Bun.sql` + `Bun.serve` 4500. Without a cache the best is
`node-express-v05-prepared`, 1400 VUs / 645 req/s. At the edge Postgres is now the larger CPU user (≈ 45 % vs. the
app's ≈ 41 %).

**Tried and not released** (node-express / node-http): feed-cache TTL 5 s (no gain); nginx as plain reverse proxy
(−28 % req/s, nginx 15 % CPU); nginx `proxy_cache` for the feed (−4 %, FAIL at 3000); pool 20 on Bun (same req/s,
query time 2×, worse tail). On 1 vCPU a proxy costs about what it saves, and the CPU, not the pool, is the limit.

**Measurement caveats:** the shared vCPU's speed varies ±20–30 % (probe before/after every run); compare tags by
the app : Postgres CPU split or at the same probe values. The 4 vCPU load generator averages ≈ 58 % CPU at 4500 VUs
with 100 % peaks; levels above ≈ 4500 VUs need an 8 vCPU one (new `LOADGEN_LABEL`, rerun the reference at its edge).

**Next (user's order): Python → Go → Rust → C++.** Each stack must pass the parity check first.
1. **Python** (in progress): the user chose to start from a plain baseline like node-express v01 —
   `python-fastapi-v01-baseline` (no pool, no cache) = 60 VUs / 29.9 req/s → `v02-pool` = 600 VUs / 306.9 req/s
   (Python CPU 2.5× Postgres's). Next `python-fastapi-v03-feed-cache-1s` (the cache that took Node from 1400 to
   3000 VUs), then uvloop + httptools, orjson, worker count; optionally Django.
2. **Go**: `net/http` + pgx.
3. **Rust**: axum + tokio-postgres (or sqlx) + deadpool, release build with LTO.
4. **C++**: e.g. Drogon or Boost.Beast + libpq, release build.

Each step is one tag that changes one thing from the best configuration so far. VU levels are chosen per run.
Profiling: `scripts/profile.sh <vus>` (not an official run) writes perf + V8 reports to `profiles/`.

## Analysis per configuration

The full analysis of every released tag, copied from `results/<tag>/config.md` by `scripts/readme_analysis.py`
(run by `release.sh`). The tables above hold the numbers; this section explains them.

<!-- ANALYSIS:START -->
### node-express-v01-baseline

[Full report](results/node-express-v01-baseline/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline)

#### What changed

First tag under protocol v2 (Server-Timing header + same-region load-generator droplet). Baseline for the
node-express stack.

#### Summary

**Capacity: 100 VUs at 46.7 req/s (2,804 req/min)**, steady p50 242 ms / p95 742 ms / p99 959 ms, 0 % errors.
This is a **marginal pass**: p99 was only 4 % under the 1000 ms limit. The first failing level is **110 VUs**:
49.8 req/s, p95 852 ms (limit 800), still 0 % errors.

- **The bottleneck is CPU, and most of it goes to opening a database connection for every request.** CPU is at
  98 % at both levels (Node about 32 %, Postgres about 61 %). Server timing shows where each request's time goes. At
  100 VUs, server p50 is 227 ms: **conn 181 ms**, db 38 ms, app 0.5 ms. About 80 % of the time is spent getting a
  connection. Postgres starts a new backend process and checks a SCRAM password for every request, and all of it
  competes for the single vCPU.
- **More users only means more queueing.** Going from 100 to 110 VUs adds 10 % load but only 7 % throughput
  (46.7 → 49.8 req/s). Nearly all the extra wait is in `conn` (p50 181 → 280 ms, p95 597 → 666 ms). `db` grows a
  little (38 → 48 ms) and `app` stays under 1 ms. The ceiling is about 50 req/s.
- **The network no longer distorts the numbers.** The load generator sits in the same region and VPC. Time outside the
  app is 15 ms at p50 (25 ms at 110 VUs), and most of that is likely queueing on the saturated CPU before Node handles
  the request, not network. In protocol v1 the MacBook added about 40 ms of round trip plus Wi-Fi stalls.
- **Memory is not a constraint.** Peak 446 MB used (515 MB still available), Node about 108 MB, Postgres about
  70 MB, no swap. No errors and no Postgres connection-limit failures: at 100–110 concurrent requests we stay just
  around `max_connections` (100) because each connection is short-lived.
- **The load generator is not a factor.** It peaked at 6–15 % CPU across 4 vCPUs, with k6 using about 96 MB.
- **Next:** `node-express-v02-pool`. A connection pool removes the per-request connect + auth that accounts for
  about 80 % of server time, so capacity should rise by an order of magnitude. `conn` will then measure time spent
  waiting for a pooled connection.

#### Observations

- Per-endpoint server p95 is uniform: 502–888 ms at 100 VUs, 665–912 ms at 110 VUs. Every endpoint pays the same
  connection setup and waits in the same CPU queue. The write paths with 3–4 round trips (comment, like/unlike) are
  only slightly slower.
- `DELETE /posts/:id/like` has the highest p95 at 100 VUs (888 ms server). It is the rarest action (2 % of the mix),
  so its percentile rests on few samples.
- Load average peaks at 4.0–4.7 on 1 vCPU. Steal time is 0.2 %, so no noisy-neighbour effect.
- `app_log_tail.txt` has no errors at either level.
- The live dashboard surfaced a tooling bug during the 100-VU run: k6 does not exit while a browser keeps the dashboard
  open. The run completed after the dashboard connections were closed, and `run_test.sh` now closes them
  automatically once the report is exported. Results are unaffected.

#### Next idea

`node-express-v02-pool`: `pg.Pool` with default settings (max 10). One change, with Server-Timing kept.

### node-express-v02-pool

[Full report](results/node-express-v02-pool/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v02-pool)

#### What changed

One change from `node-express-v01-baseline`: a `pg.Pool` with default settings (max 10 connections, idle timeout
10 s) instead of a new `pg.Client` per request. Each request borrows one connection for all its queries and returns
it before the response is sent. A connection whose ROLLBACK failed is destroyed instead of being reused.
`Server-Timing` `conn` now measures the wait for a pooled connection (or the connect while the pool fills).

#### Summary

**Capacity: 1350 VUs at 619 req/s (37,149 req/min)**, steady p50 325 ms / p95 690 ms / p99 776 ms, 0 % errors.
The first failing level is **1400 VUs**: 518 req/s, p50 895 ms (limit 500), p95 1320 ms, p99 1389 ms, still 0 % errors.
Peak throughput was **651 req/s at 1300 VUs**. Compared with v01 (100 VUs, 46.7 req/s) that is **13.5× the users and
about 13× the throughput**, from one change: a connection pool.

- **The bottleneck is now the CPU running queries, not connection setup.** From 1200 VUs on, CPU is at 98–100 %,
  split about evenly between Node (≈ 42 %) and Postgres (≈ 50 %). CPU per request fell from about 20 ms in v01
  to **about 1.4–1.9 ms** (e.g. 93 % CPU / 651 req/s at 1300 VUs). The ceiling on this vCPU is about 600–650 req/s.
- **Past the ceiling, load turns into waiting for a pooled connection, not into errors.** Query time stays small at
  every level: `db` p95 is 24–48 ms. `conn` (waiting for one of the 10 pooled connections) is what grows:
  p95 0.1 ms at 500 VUs, 24 ms at 1000, 387–651 ms at 1200–1350, and 1276 ms at 1400. At 1400 VUs, 98 % of server
  time is pool wait. The pool queue is a symptom of the saturated CPU: Postgres already gets half the CPU, so
  more connections would not run queries faster.
- **The edge is sharp.** From 1350 to 1400 VUs (+4 %), p50 jumps from 325 to 895 ms and throughput drops from 619
  to 518 req/s. In this closed-loop test, once a queue forms it does not drain during the hold phase.
- **Results near the ceiling are noisy.** 1250 VUs (576 req/s, p95 634 ms) did worse than 1300 VUs (651 req/s,
  p95 466 ms) with the same CPU split, no CPU dips and steal ≤ 0.4 %. Whether a queue builds up during the ramp
  decides the outcome. Treat 1200–1350 VUs as one band: about 600–650 req/s, p95 430–690 ms.
- **Memory is not a constraint.** Peak 509 MB used (452 MB still available), Node ≤ 133 MB, Postgres ≤ 125 MB,
  no swap.
- **The load generator is not a factor.** It averaged 11–23 % CPU in the hold phase. Short peaks of 44–72 %
  happen at k6 start-up and during the ramp. k6 used up to 789 MB.
- **Next:** CPU per request is the lever now. Phase 2 starts with pool size (5 / 20) to confirm it changes little
  while the CPU is saturated. After that, cut CPU per request: prepared statements, single-statement writes
  instead of BEGIN/COMMIT, or Postgres tuning.

#### Observations

- `app` time (routing, validation, JSON) stays at p50 0.2 ms and p95 ≤ 1.8 ms at every level. Express itself is
  not where the time goes.
- At overload (1400–1500 VUs), Node's CPU share rises (45 %) and Postgres's falls (48 %), and throughput drops below
  the 1300-VU peak. Node likely spends more CPU managing more open sockets and queued requests, leaving less for queries.
- Time outside the app (client latency − server total) stays small: p50 1.2 ms at 500 VUs, 2.5 ms at 1000,
  17.6 ms at 1500. The network and the load generator add little; nearly all latency is inside the handler.
- Per-endpoint p95 is uniform at the overloaded levels (all endpoints wait in the same pool queue). At 500 VUs the
  writes are slowest (client p95: like/unlike 24–27 ms vs. reads 14–18 ms): they hold a connection for 3–4 round trips.
- Server CPU never dropped below 70 % during the hold phase of any level from 1200 VUs on, so no level was distorted
  by a client or network stall. Steal ≤ 0.4 % everywhere.
- `app_log_tail.txt` has no errors at any level. 0 % errors overall: the pool queues instead of failing, and
  Postgres sees at most 10 connections.
- Protocol v1 (MacBook) measured the same configuration at 1250 VUs / 627 req/s. Protocol v2 confirms the ceiling
  (≈ 600–650 req/s) with the network removed. The p95/p99 tail seen from 400 VUs in protocol v1 does not appear
  here: at 500 VUs p99 is 43 ms. It was the MacBook/Wi-Fi path, not the server.
- Tooling fixes made during this tag (no effect on results): `deploy.sh` now runs its health check on the droplet
  (the Mac cannot reach the private `TARGET_HOST`), and `run_test.sh` only reuses a listening dashboard tunnel.

#### Next idea

`node-express-v03-pool-20` (or `-pool-5`): change only the pool size, to confirm the pool queue is a symptom of
CPU saturation and not a cause. Bigger gains should come from cutting CPU per request (prepared statements,
single-statement CTE writes, Postgres tuning).

### node-express-v03-pool-20

[Full report](results/node-express-v03-pool-20/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v03-pool-20)

#### What changed

One change from `node-express-v02-pool`: `pg.Pool` `max` 10 → **20**. All other pool settings stay default.

#### Summary

**Capacity: 1200 VUs at 574 req/s (34,443 req/min)**, steady p50 182 ms / p95 756 ms / p99 972 ms, 0 % errors.
This is a **marginal pass**: p99 was only 2.8 % under the 1000 ms limit (p95 5.5 % under 800 ms). The first failing
level is **1300 VUs**: 563 req/s, p95 1031 ms, p99 1114 ms. **Pool 20 is worse than the parent tag** (v02, pool 10:
1350 VUs / 619 req/s): lower capacity, lower throughput and higher latency at 4 of the 5 levels run on both tags.

- **A bigger pool makes each query slower, not more of them possible.** CPU is at 99–100 % at every level, split
  the same as v02 (Node ≈ 41 % / Postgres ≈ 48 %). With up to 20 queries running at once on one vCPU, each takes
  about twice as long: `db` p50 21–25 ms (v02: 10–13 ms) and p95 83–102 ms (v02: 37–48 ms). Postgres gets no more
  CPU than before, so it spreads the same CPU over more concurrent backends and adds context switching.
- **Waiting moves, it does not go away.** `conn` (pool wait) is still most of server time (p95 656 ms at 1200 VUs,
  943 ms at 1300), because the CPU, not the pool, limits throughput.
- **Time outside the handler doubled:** client − server p50 is 33–44 ms at every v03 level vs. 14–18 ms in v02 at
  the same levels. With 20 runnable Postgres backends competing with Node for the vCPU, Node likely gets scheduled
  less often, so requests wait longer in the socket and the event loop before the handler starts.
- **The overload tail is worse.** At 1500 VUs p99 is 2450 ms (v02: 1442 ms).
- **Memory is not a constraint.** Peak 542 MB used (419 MB still available); Postgres PSS rises to 137–155 MB
  (v02: 108–125 MB) for the extra backends. Node ≤ 136 MB. No swap.
- **The runs are clean.** CPU never dropped below 70 % during any hold phase, steal ≤ 0.5 %, the load generator
  averaged 18–21 % CPU, and `app_log_tail.txt` has no errors.
- **Next:** keep pool 10, or try pool 5 to see whether fewer concurrent queries help further. Bigger gains should
  come from cutting CPU per request (prepared statements, single-statement writes, Postgres tuning).

#### Observations

- 1400 VUs is the only level where v03 beat v02 (604 vs. 518 req/s), but both failed, and single runs near the
  ceiling swing this much (v02 itself scored 576 req/s at 1250 and 651 at 1300). The other four levels all favour
  pool 10, and `db` time is about 2× higher at every level, so the direction is clear.
- `app` time (routing, validation, JSON) is unchanged: p50 0.2 ms, p95 ≤ 1.9 ms.
- Per-endpoint p95 at 1200 VUs is uniform (591–836 ms client): every endpoint waits in the same pool queue. The
  write paths with 3–4 round trips (like/unlike, comment) are slowest because they hold a connection longest.
- No `53300 too many clients` errors: 20 pooled connections stay well under `max_connections=100`.

#### Next idea

`node-express-v04-pool-5` (parent v02): pool `max` 10 → 5, to see whether fewer concurrent queries cut `db` time
enough to raise throughput. If not, keep pool 10 and move to per-request CPU savings.

### node-express-v04-cte-writes

[Full report](results/node-express-v04-cte-writes/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v04-cte-writes)

#### What changed

Parent: `node-express-v02-pool` (pool 10). v03 (pool 20) was worse and is not carried forward.
One change: the writes that touch two tables are now **one SQL statement with data-modifying CTEs** instead of
`BEGIN` / 2 queries / `COMMIT`:
- like: `INSERT INTO likes ... SELECT FROM posts WHERE id = $1 ON CONFLICT DO NOTHING`, then `UPDATE posts SET
  like_count = like_count + 1` only for the inserted row; the count comes from the UPDATE or, for an existing like,
  from `posts`.
- unlike: `DELETE FROM likes ... RETURNING`, then decrement only for the deleted row.
- comment: `INSERT INTO comments ... RETURNING`, then `UPDATE posts SET comment_count = comment_count + 1`.
A single statement is one transaction, so the writes stay atomic. Responses and status codes are unchanged
(verified: new/repeat like and unlike, unknown post 404, unknown user 401, empty text 400). A concurrency check of
30 parallel likes by one user, 40 by different users and 20 parallel unlikes left `like_count` = rows in `likes` (31).

#### Summary

**No measurable gain over v02.** By the capacity rule (highest passing level) v04 scores **1400 VUs at 660 req/s**,
but that pass is **marginal** (p95 788 ms, 1.5 % under 800; p99 991 ms, 1 % under 1000), and the lower levels
**1300 and 1350 VUs both failed**. Read the capacity as "about 1300–1400 VUs, 540–660 req/s", the same band as the
parent tag (v02, pool 10: 1350 VUs / 619 req/s). 1500 VUs fails (614 req/s, p95 1316 ms). 0 % errors everywhere.

- **The change works as designed, but the effect is smaller than the run-to-run noise at the ceiling.** Like,
  unlike and comment now take 1 round trip instead of 4. That removes about 30 % of all queries (≈ 1.6 → ≈ 1.1 per
  request across the action mix). `db` p95 dropped a little (30–38 ms vs. 37–48 ms in v02 at the same levels).
- **The CPU split did not change:** Node ≈ 42 % / Postgres ≈ 50 %, CPU at 99.5–100 % at every level. The removed
  queries were the cheapest ones (BEGIN, COMMIT, and short single-row updates), so the saving per request is small.
- **At 100 % CPU, the outcome is decided by whether a queue forms during the ramp, not by the code.** Over the four
  shared levels v04 averages 597 req/s and v02 584 req/s (+2 %), while single runs of either tag swing ±60 req/s.
  v04 passed 1400 but failed 1300 and 1350; v02 passed 1300 and 1350 but failed 1400.
- **Memory is not a constraint.** Peak 516 MB used (445 MB still available), Node ≤ 136 MB, Postgres ≤ 127 MB, no swap.
- **The runs are clean.** CPU never dropped below 70 % during any hold phase, steal ≤ 0.6 %, the load generator
  averaged 19–21 % CPU, and `app_log_tail.txt` has no errors.
- **Kept as the parent of the next tag:** it is correct, atomic, does no harm, and lowers `db` time slightly.
- **Next:** prepared statements (`pg` named queries) to skip parse/plan in Postgres, which uses half the CPU. To see
  small gains, also compare at a level below saturation (e.g. 1000 VUs, where v02 used 84 % CPU for 538 req/s):
  the CPU cost per request is measurable there, unlike at the ceiling.

#### Observations

- Latency is still almost all pool wait: `conn` is 92–97 % of server time at every level. Queries themselves stay
  fast (`db` p50 12–15 ms).
- Time outside the handler (client − server p50) is 20–26 ms, a bit above v02 (14–18 ms). With the same CPU
  saturation, this is likely run-to-run variation in how long requests wait for Node to be scheduled.
- Per-endpoint p95 at 1400 VUs is uniform (716–763 ms client): every endpoint waits in the same pool queue, so the
  shorter write path does not show up in per-endpoint latency at saturation.
- The k6 summary only keeps `server_db` overall and per phase, not per endpoint, so the write-path saving cannot be
  isolated from these runs. A run below saturation would show it in total CPU per request.
- Near the ceiling, the pass/fail verdict of a single run is not reliable for changes worth less than ≈ 10 %. Future
  comparisons should include one unsaturated level (CPU per request) besides the edge levels.

#### Next idea

`node-express-v05-prepared` (parent v04): named queries in `pg` (`{ name, text, values }`), so each pooled
connection parses and plans every statement once and reuses the plan. Postgres uses half the CPU; parse/plan is a
real part of it for these short indexed queries. Run one unsaturated level (1000 VUs) plus the edge levels.

### node-express-v05-prepared

[Full report](results/node-express-v05-prepared/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v05-prepared)

#### What changed

Parent: `node-express-v04-cte-writes`. One change: **every query is a prepared statement** (a `pg` named query,
`{ name, text, values }`). The app derives a stable name per SQL text (`q1`, `q2`, ...), so each pooled connection
parses and plans each statement once and then only binds and executes it. Verified on the droplet: a named query run
twice on one connection shows one entry in `pg_prepared_statements` with 2 executions. All endpoints return the same
responses and status codes as v04.

#### Summary

**Capacity: 1400 VUs at 645 req/s (38,707 req/min)**, steady p50 320 ms / p95 676 ms / p99 802 ms, 0 % errors.
The first failing level is **1500 VUs**: 688 req/s, p99 1168 ms (limit 1000), still 0 % errors. All levels from
1000 to 1400 VUs passed. **Likely a small gain over v04, not proven:** Postgres's CPU share dropped
consistently, but the throughput difference is within the host-speed noise.

- **Prepared statements cut Postgres's share of the CPU.** At saturation the split is Node ≈ 48 % / Postgres
  ≈ 43.5 % (v02/v04: ≈ 42 % / ≈ 50 %); at 1000 VUs Postgres uses 37 % vs. 42 % in v02. Skipping parse and plan
  on every query is visible as a lower Postgres share at every level, which does not depend on the host speed.
- **Throughput at saturation is the best so far, but by less than the noise.** v05 served 633 / 645 / 688 req/s
  at 1300 / 1400 / 1500 VUs (v04: 542 / 661 / 614; v02: 651 / 518 / 547). The average over those three levels is
  655 req/s vs. 606 (v04) and 572 (v02). Single runs swing ±60 req/s, so this is a hint of a ≈ 5–10 % gain.
- **The first 1500-VU run passed at 802 req/s and is not counted.** It reached p50 15 ms / p95 124 ms / p99 165 ms
  at only 92 % CPU, i.e. 1.15 ms CPU per request vs. 1.45–1.67 ms in every other run of every tag. The CPU cost
  per request was lower from the first seconds of the ramp (1.72 vs. ≈ 2.1 ms at the same 340 req/s), so the
  droplet's shared vCPU ran ≈ 30 % faster during that run (steal 0.07 %, so steal does not show it). The user asked
  for a rerun: 688 req/s, FAIL on p99. Only the rerun is in `vus-1500/`.
- **This explains much of the run-to-run noise in all tags.** A fixed CPU workload timed on the idle droplet varies
  ±20 % within seconds (67–98 ms). From the next tag on, every run records a host-speed probe before and after k6
  (`cpu_probe_before_ms` / `cpu_probe_after_ms`) and the CPU cost per request (`cpu_ms_per_req_steady`).
- **Memory is not a constraint.** Peak 497 MB used, Node ≤ 130 MB, Postgres ≤ 114 MB, no swap.
- **The runs are clean.** CPU never dropped below 70 % during any saturated hold phase, steal ≤ 0.9 %, the load
  generator averaged 19–22 % CPU, and `app_log_tail.txt` has no errors.
- **Next:** a profiling run of this configuration (below) shows Postgres's Memoize step costs ≈ 10 % of Postgres CPU
  in the feed queries for no benefit. v06: `enable_memoize = off`. After that: Fastify (Express + router are ≈ 24 %
  of Node's JS time), then the 1 s feed cache.

#### Observations

- `conn` (pool wait) is still 92–95 % of server time at the saturated levels; `db` p95 is 29–30 ms, the lowest of
  any tag at saturation.
- At 1000 VUs (not saturated) the CPU cost per request is 1.67 ms vs. 1.57 ms for v02. This contradicts the lower
  Postgres share, so host speed differed between the two runs; v05 ran before the host-speed probe existed.
- Time outside the handler (client − server p50) is 21–23 ms at saturation, as in v04.
- Someone ran `htop` on the droplet during the profiling run (1.3 % CPU). Interactive tools on the droplet during
  official runs take CPU from the app; avoid them.

#### Next idea

`node-express-v06-no-memoize` (parent v05): `enable_memoize = off` for the app's database role, the only change.
It removes the per-execution Memoize setup in the feed queries (≈ 10 % of Postgres CPU in the profile). Compare at
1000 VUs (CPU per request, now with the host-speed probe) plus edge levels.

### node-express-v06-feed-cache-1s

[Full report](results/node-express-v06-feed-cache-1s/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v06-feed-cache-1s)

#### What changed

Parent: `node-express-v05-prepared`. One change: **`GET /posts` (global feed, all pages) is cached in the Node
process for 1 s.** Key `limit:before` (validated values), value = the serialized JSON body, sent with
`res.type('json').send(...)` (same `Content-Type: application/json; charset=utf-8` and ETag as `res.json`). The TTL
counts from the moment the query starts. Concurrent misses for one key share one query (single-flight: the cache
holds the pending promise); a failed query is removed from the cache so the next request retries. Expired entries are
swept every 10 s, when the app also logs `feed cache: hit=… miss=… keys=…`. No invalidation on writes: a new post or a
new like/comment count shows in the global feed after at most 1 s (verified on the droplet). The other endpoints are
unchanged (`/posts/:id`, `/users/:id/posts` and `/me/posts` use random ids or are per user, so a cache would rarely
hit). App code from commit `887f64c`.

#### Summary

**Capacity: 3000 VUs at 1541 req/s (92,462 req/min)**, steady p50 29 ms / p95 573 ms / p99 855 ms, 0 % errors.
The first failing level is **3200 VUs**: 1604 req/s, p99 1641 ms (limit 1000), still 0 % errors. Every level from
1000 to 3000 VUs passed. **2.1× v05's capacity in VUs (1400) and 2.4× in req/s (645)**, the biggest step since the
pool (v02). Labelled trade-off: the global feed can be up to 1 s stale.

- **The cache takes almost all feed queries off Postgres.** `GET /posts` is ≈ 47 % of requests (first page ≈ 36 %,
  second page ≈ 11 %); the first page is the same URL for every VU, and while it is cached its `next_before` is too,
  so the second page is a shared key as well. The app log shows **99.0–99.6 % hits** with 2 live keys; misses are
  ≈ 25 per 10 s (one per key per second, plus a few rare keys).
- **CPU per request fell ≈ 40 %.** At 1000 VUs: 0.97 ms vs. 1.67 ms for v05, total CPU 53 % vs. 89 %, Postgres
  12 % vs. 37 %, Node 33 % vs. 44 %. Host-speed probe 89 / 88 ms (normal). Cached responses skip the pool, the query,
  the `pg` row parsing and `JSON.stringify`; server time for a cached `GET /posts` is p95 0.3 ms.
- **The ceiling is still the CPU, and Node is now the larger share.** At 3000–3200 VUs the vCPU is 98–99 % busy
  (Node ≈ 60 %, Postgres ≈ 30 %), steal ≤ 0.4 %. Past ≈ 2500 VUs latency is again pool wait (`conn` p95 452 ms at 3000,
  482 ms at 3200) while query time stays at p95 ≈ 19 ms, the same overload pattern as v02–v05. 0 % errors at every
  level.
- **Memory is not a constraint.** Peak 548 MB used (3200 VUs: 3200 open sockets), Node ≤ 161 MB PSS, Postgres
  ≤ 131 MB, no swap; ≥ 400 MB still available.
- **The runs are clean** apart from short load-generator spikes: no CPU dips during any saturated hold phase,
  `app_log_tail.txt` has no errors, and the load generator averaged 18–40 % CPU. From 2000 VUs it peaked at
  96–98 % in single samples (8 samples > 70 % at 3000 and at 3200). 3000 passed with the same spikes, so they do
  not explain the 3200 failure, but they may add to the tail at the top levels.
- **Next:** v07 = the same cache with a 5 s TTL (user's plan). Since the hit rate is already 99.6 %, 5 s can only
  remove the ≈ 2 refresh queries per second and the stalls they cause (see Observations), so expect a small change.
  After that, Node is ≈ 2/3 of the CPU: Fastify instead of Express is the most promising next lever.

#### Observations

- **CPU per request keeps falling as load rises** (0.97 → 0.62 ms from 1000 to 3200 VUs). The share of cached
  requests is constant, so this is per-request fixed cost being amortised: more requests per event-loop turn and
  per `epoll`/`writev`, and Postgres serving the remaining queries in batches. v05 showed the same trend, smaller.
- **Cached feed requests still see stalls at the top levels.** Server time for `GET /posts` is p95 0.3–1.2 ms up to
  2500 VUs but 204 ms at 3000 and 219 ms at 3200, although 99.6 % are hits. Likely cause: when a key expires, its
  refresh query waits in the same pool queue as everyone else (`conn` p95 ≈ 450 ms), and every feed request for that
  key arriving meanwhile waits on the same promise. Waiters record that wait as `app` time (they did not borrow a
  connection themselves), so the feed's `app` time at saturation is pool wait, not Express overhead. Serving the old
  body while one request refreshes (stale-while-revalidate) would remove these stalls.
- Edge case not reached here: the TTL counts from the query's start, so if a refresh waited > 1 s for the pool, the
  entry would expire before it resolves and single-flight would stop working. Pool wait stayed below ≈ 500 ms p95.
- Time outside the handler (client − server p50) grows from 1.3 ms at 1000 VUs to 22–23 ms at 3000–3200 VUs (event
  loop and accept queue under a busy CPU).
- Host speed varied: the probe read 116 ms before 2500 VUs and 115 ms after 2000 VUs (slow), 81–97 ms otherwise. 2500
  passed comfortably anyway; 3000 and 3200 ran at normal speed (88 / 92 ms before).
- ETag (sha1 of the body) is still computed for every cached response; disabling it is a separate tag.

#### Next idea

`node-express-v07-feed-cache-5s` (parent v06): the same cache with TTL 5 s, the only change (user's plan). Compare at
1000 VUs (CPU per request) and at the edge (3000 / 3200 VUs). Expect a small difference: hits are already 99.6 %, so
5 s only removes ≈ 2 refresh queries per second and makes the refresh stalls 5× rarer.

### node-http-v02-bun

[Full report](results/node-http-v02-bun/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v02-bun)

#### What changed

Parent: `node-http-v01-express-v06-port`. One change: **the runtime, Node v24.21.0 → Bun 1.4.2.** `start.sh` runs
`bun src/server.js` instead of `node src/server.js`. Same source (`node:http` server, `pg` 8.23.1 pool max 10,
prepared statements, CTE writes, 1 s in-process feed cache), same `node_modules` (`npm ci`). Bun is installed by
`scripts/server/setup.sh` as a pinned release binary (`/usr/local/bin/bun`, bun-linux-x64; the droplet has AVX2).
The parity check (39 requests on a fresh DB) gave responses identical to v01 on Node; headers are the same
(`Connection: keep-alive`, `Keep-Alive: timeout=5`). App code from commit `f64fc95`.

#### Summary

**Capacity: 4200 VUs at 2078 req/s (124,668 req/min)**, steady p50 47 ms / p95 752 ms / p99 851 ms, 0 % errors
(added after the first release; near-marginal: p95 6 % under its limit, fast host). 4000 VUs passed comfortably at
2082 req/s (p95 436 / p99 823 ms). The first failing level is **4500 VUs**: 2097 req/s, p95 902 ms / p99 1045 ms
(limits 800 / 1000), still 0 % errors. **+31 % VUs and +24 % req/s over node-http v01 on Node** (3200 VUs /
1678 req/s), with the same code and driver: only the runtime changed. Best result so far.

- **Bun does less work per request.** At 3500 VUs (Node's first fail, Bun's easy pass) the app : Postgres CPU ratio
  is 1.28 vs. 1.48 on Node (Bun 45 % / PG 35 % at 1855 req/s vs. Node 52 % / PG 35 % at 1779 req/s), i.e. ≈ 13 %
  less app CPU per query, measured independently of host speed. CPU per request 0.48 vs. 0.54 ms although the host
  was slower for Bun's run (probe 109 vs. 83 ms before).
- **The ceiling is ≈ 2100 req/s, and it is the CPU.** 4000 → 4500 VUs adds only 15 req/s (2082 → 2097). At 4500 VUs
  the vCPU is at 100 % for the whole hold phase (Bun 51 % / Postgres 40 %), steal 0.4 %. The latency is inside the
  server: server time p95 884 ms, almost all pool wait (`conn` p95 861 ms); query time p95 15 ms.
- **Postgres is now ≈ 44 % of the busy CPU.** Further savings on the app side shrink in value; the Postgres share
  (the ≈ 53 % of requests that still run queries) is the next floor.
- **Memory is lower than on Node.** Bun PSS ≤ 113 MB (Node ≤ 147 MB), peak 499 MB used, ≥ 462 MB available, no swap.
- **The load generator is near its limit but did not decide the verdicts.** It averaged 46–53 % CPU and spiked to
  ≈ 90–100 % every ≈ 6–7 s (k6 RSS up to 2.6 GB). Time outside the app stayed at p95 16–18 ms at every level, and the
  4500 failure is server-side (100 % CPU, latency inside the handler).
- **Next:** user's request — a larger `pg.Pool` on Bun at 4500 VUs (node-express v03 showed pool 20 was worse on
  Node: more concurrent queries only add contention on 1 vCPU; Bun may behave differently). Then `Bun.serve` or Bun's
  native Postgres client (`Bun.sql`), or other stacks (Go, Rust).

#### Observations

- At 3500 and 4000 VUs the CPU was not pinned (89 % and 94 % average with dips to ≈ 80 %): Bun kept up with the
  offered load. At 4500 it was at 100 % throughout, and p50 jumped from 14 to 247 ms: the queue builds as soon as the
  offered load (≈ 2300 req/s) passes the ≈ 2100 req/s ceiling.
- The 4000-VU pass ran on a fast host (probe 79 ms before) and the host slowed during it (105 ms after); p99 823 ms
  leaves 18 % headroom, so the pass is not marginal, but a slower host could move the edge by one step.
- Time outside the handler (client − server) is small at every level (p50 5–30 ms, p95 16–18 ms): Bun's event loop
  and the load generator add little.
- `app_log_tail.txt` has no errors; feed-cache misses ≈ 25 per 10 s as on Node.

#### Next idea

`node-http-v03-pool-20` (parent v02): `pg.Pool` max 10 → 20, the only change, tested at 4500 VUs (user's request).
On Node (node-express v03) pool 20 doubled query time and lowered capacity; check whether Bun's lower app overhead
changes that. Further: Bun's native Postgres client (`Bun.sql`) or `Bun.serve`, then Go / Rust.

### node-http-v03-bun-sql

[Full report](results/node-http-v03-bun-sql/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v03-bun-sql)

#### What changed

Parent: `node-http-v02-bun`. One change: **the Postgres client, node-postgres (`pg` 8.23.1) → Bun.sql** (Bun 1.4.2's
built-in client, `new SQL({ url, max: 10 })`). Every request still reserves one connection (`sql.reserve()`) for all
its queries, timed as `conn`; queries are tagged templates (prepared and cached per connection by Bun.sql), timed as
`db`. Adjustments needed for identical responses: every parameter has an explicit cast (`::bigint`, `::int`,
`::text`, `::boolean`) so numbers never travel as float8; Bun.sql returns int8 columns as strings, so `id`, `user_id`
and `post_id` are converted with `Number()` in the query wrapper (node-postgres did the same with a type parser);
the SQLSTATE of a server error is in `err.errno` (`err.code` is Bun's own code). The `pg` dependency is removed. The
parity check (39 requests on a fresh DB) gave responses identical to v01/v02. App code from commit `ed0c70a`.

#### Summary

**Only one level tested: 4500 VUs FAIL** — 1955 req/s, steady p50 417 ms / p95 1088 ms / p99 1547 ms (limits 800 /
1000), 0 % errors. Capacity by the rule is therefore "< 4500" (not measured below); the parent v02 (`pg` on Bun)
passed 4200 VUs and also failed 4500. **No measurable gain from Bun's native Postgres client.** Kept as the base for
`Bun.serve` (v04) by the user's decision.

- **At most ≈ 5 % less app work per query.** The app : Postgres CPU ratio at 4500 VUs is 1.22 (Bun 49.9 % / PG
  40.8 %) vs. 1.29 for v02 (51.4 % / 39.7 %). This ratio does not depend on host speed. Query time is unchanged
  (`db` p95 17 vs. 15 ms): the native client does not make Postgres faster, only the client side slightly cheaper.
- **Throughput at the edge is confounded by host speed.** Both runs had the CPU at 100 % for the whole hold phase, so
  req/s follows the host: v03 started on a ≈ 30 % slower host (probe 108 ms before vs. 83 ms for v02). 1955 vs.
  2097 req/s (−7 %) and 0.51 vs. 0.48 ms CPU per request are within that difference.
- **Bottleneck unchanged:** CPU-bound, Bun ≈ 50 % / Postgres ≈ 41 %, latency past the edge is pool wait (`conn` p95
  999 ms). Memory 500 MB used, Bun PSS 109 MB, Postgres 132 MB, no swap. Load generator 48 % average, peaks 100 %;
  time outside the app p95 28 ms.
- **Next:** v04 = `Bun.serve` instead of `node:http` on top of this (user's plan).

#### Observations

- The CPU was at 97–100 % for the entire hold phase; no client stalls.
- Feed-cache hit rate 99.7 %, as before; `app_log_tail.txt` has no errors.
- A repeat run on a normal-speed host was offered and not chosen: the host-independent CPU split already bounds the
  gain at ≈ 5 %.

#### Next idea

`node-http-v04-bun-serve` (parent v03): `Bun.serve` (Bun's native HTTP server, `fetch(Request) → Response`) instead
of `node:http` on Bun's compatibility layer, the only change. Test at 4500 VUs.

### node-http-v04-bun-serve

[Full report](results/node-http-v04-bun-serve/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v04-bun-serve)

#### What changed

Parent: `node-http-v03-bun-sql`. One change: **the HTTP server, `node:http` (Bun's Node compatibility layer) →
`Bun.serve`** (Bun's native server: `fetch(Request) → Response`). Same handlers, router, `Bun.sql` data access,
1 s feed cache and `Server-Timing` (now computed when the `Response` is created; Bun adds `Content-Length`). Request
helpers adapted to the Fetch API: `req.headers.get()`, body via `req.text()` (JSON only, 100 kB limit), the path
parsed from the absolute `req.url`. Bun.serve's keep-alive idle timeout is its default (10 s; node:http used 5 s);
k6 VUs send a request every 1–3 s, so connections never idle out in either. The parity check (39 requests on a fresh
DB) gave responses identical to v01–v03. App code from commit `d4b36f2`.

#### Summary

**Capacity: 4500 VUs at 2324 req/s (139,452 req/min)**, steady p50 15 ms / p95 319 ms / p99 912 ms, 0 % errors.
**First fail: 4700 VUs** (added after the first release), in two runs, both on a slow host: 2212 req/s (p95 934 /
p99 1093 ms, probe 104 ms) and, rerun, 2144 req/s (p95 1188 / p99 1547 ms, probe 148 ms); the 4500 pass ran at probe
82 ms. The CPU was at 100 % and the latency was pool wait in both, so the 4700 failures are server-side, but on a
normal-speed host 4700 might pass. **Best result of the project so far**: +7 % VUs over v02 (4200)
and +12 % req/s over v02's best (2078–2097 req/s at 4200–4500 VUs); v02 and v03 both failed 4500 VUs.

- **`Bun.serve` cuts the app's work per request by ≈ 25 %.** App : Postgres CPU ratio 0.91 (Bun 40.7 % / PG 44.6 %)
  vs. 1.22 in v03 (same `Bun.sql`, `node:http` on Bun's compatibility layer) and 1.30 in v02. CPU per request 0.40 ms
  vs. 0.48 ms (v02) at the same host speed (probe 82 vs. 83 ms before). Most of the app-side cost on Bun was the
  `node:http` compatibility layer, not the runtime.
- **Postgres is now the larger CPU user** (45 % vs. the app's 41 %). Further app-side savings matter less; the ≈ 53 %
  of requests that still run queries set the floor. Query time stays low (`db` p95 11 ms).
- **Not saturated yet:** CPU 94 % average with dips to 82–90 %; pool wait p95 194 ms (v02 at 4500: 861 ms).
- **Memory is the lowest of any configuration:** Bun PSS ≤ 59 MB (v02 113 MB, Node 147 MB), peak 464 MB used,
  ≥ 497 MB available, no swap.
- **The load generator is the limit for going further.** k6 averaged 58 % CPU (peaks 100 %, RSS 2.6 GB) and the time
  outside the app rose to p95 49 ms (18–28 ms in earlier 4500-VU runs). The next level (≈ 5000 VUs) needs an 8 vCPU
  load generator to give a trustworthy verdict.
- **Next (user's plan):** Node/Bun is saved here; move on to Python frameworks, then Go, then Rust, then C++, each
  with the same API, pool 10 and 1 s feed cache, and compare their edges with this result.

#### Observations

- p99 912 ms leaves 9 % headroom; p50 15 ms and p95 319 ms show the server mostly keeps up, and the tail comes from
  short CPU-saturated stretches (100 % for up to ≈ 6 s at a time).
- Time outside the app (client − server) p50 13 ms / p95 49 ms: the p95 is the highest so far and coincides with the
  load generator's CPU peaks, so part of the tail is on the client side.
- Feed-cache hit rate 99.7 %; `app_log_tail.txt` has no errors.
- 4700 VUs, first run (replaced): FAIL, 2211.7 req/s, p50 156 / p95 934 / p99 1093 ms, CPU 98.5 % (Bun 43.1 / PG 45.9),
  0.45 ms CPU/req, probe 104.5 / 83.0 ms, load generator 53 % average. Rerun (kept): probe 148 ms before, the slowest
  host of the session. Both runs: CPU pinned, `conn` p95 880–1096 ms, time outside the app p95 19–30 ms (not k6).

#### Next idea

Node/Bun is saved here (user's decision). Next phase: Python frameworks (Phase 3: FastAPI + uvicorn + asyncpg first),
then Go, Rust and C++. Before any stack is pushed beyond ≈ 4500 VUs, recreate the load generator with 8 vCPU (new
`LOADGEN_LABEL`) and rerun this configuration at its edge for comparability.

### node-http-v01-express-v06-port

[Full report](results/node-http-v01-express-v06-port/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-http-v01-express-v06-port)

#### What changed

New stack `apps/node-http/`. Parent: **`node-express-v06-feed-cache-1s`** (different stack). One change: **Express
removed** — the same app on plain `node:http`. Everything else is a 1:1 port of node-express v06: `pg.Pool` defaults
(max 10), prepared statements (named queries), single-statement CTE writes, the 1 s in-process cache of `GET /posts`
(same code), `Server-Timing` on every response. Done by hand instead of by Express: a small router (method + path
segments, trailing slash ignored), JSON body parsing (JSON content types only, 100 kB limit, like `express.json`),
JSON responses with `Content-Type: application/json; charset=utf-8` and `Content-Length`. Not carried over (not part
of the contract): the `ETag` and `X-Powered-By` headers. A parity check on a fresh DB (39 requests: every endpoint,
400 / 401 / 404, invalid JSON, idempotent like/unlike, FK errors) gave identical status codes, bodies and content types
for both apps. App code from commit `656bdc8`.

#### Summary

**Capacity: 3200 VUs at 1678 req/s (100,656 req/min)**, steady p50 11 ms / p95 392 ms / p99 835 ms, 0 % errors.
The first failing level is **3500 VUs**: 1779 req/s, p99 1175 ms (limit 1000), p50 30 ms / p95 471 ms, still
0 % errors. Express v06 failed 3200 VUs (p99 1641 ms) and passed 3000, so dropping the framework moves the edge by
one step: **+7 % VUs, +9 % req/s** vs. node-express v06 (3000 VUs / 1541 req/s). The gain is real but modest, and
part of the req/s difference is host speed.

- **Less Node work per request.** At 3200 VUs Node used 51 % of the CPU and Postgres 33 % (Express v06: 60 % / 31 %).
  The Node : Postgres ratio fell from 1.93 to 1.55. Postgres runs the same queries in both, so the ratio does not
  depend on host speed: Node does ≈ 20 % less work per request without Express (router, middleware, `res.json`,
  ETag sha1).
- **Host-speed caveat.** The probe read 81 ms before the 3200-VU run vs. 92 ms before Express's (≈ 12 % faster
  host). CPU per request was 0.55 vs. 0.62 ms (−10 %), which is about the host difference, so CPU per request alone
  does not prove a gain; the CPU split above does.
- **The ceiling is still the CPU.** At 3500 VUs the vCPU is 95 % busy on average and at 100 % for long stretches
  (Node 52 % / Postgres 35 %), steal 0.9 %. Latency past the edge is pool wait again (`conn` p95 360 ms, query time
  p95 16 ms). Postgres is now ≈ 40 % of the busy CPU, so further app-side savings pay off less and less.
- **Memory is not a constraint.** Peak 537 MB used, Node ≤ 147 MB PSS, Postgres ≤ 133 MB, no swap, ≥ 424 MB available.
- **The load generator is close to its limit.** It averaged 48 % CPU at both levels, but spiked to 73–90 % about every
  6 s (peak 99–100 %). The server's CPU dips do not line up with those spikes, so k6 did not cause the 3500 failure,
  but levels above ≈ 3500 VUs need a bigger load generator to be trustworthy.
- **Next:** the remaining big levers are a faster runtime / HTTP server (Bun, uWebSockets.js) and other stacks (Go,
  Rust). Postgres's ≈ 35 % share is the floor no Node change can remove; caching more of the reads, or a stack that
  spends less CPU per query in the driver, attacks it.

#### Observations

- At 3200 VUs the CPU was not pinned (92 % average, dips to 82–89 %): the server kept up with the offered load
  (≈ 1680 req/s from 3200 VUs). At 3500 VUs it was at 100 % for long stretches, so the edge lies between the two.
- The p99 failure at 3500 VUs is queueing: p50 stays at 30 ms and p95 at 471 ms, only the tail crosses 1 s.
- `app` time p95 is 3.4 ms at 3200 VUs vs. 120 ms for Express at the same level. Most of that difference is not
  framework cost: `app` also holds the wait of requests sharing a feed-cache refresh (single-flight), which follows
  pool wait (`conn` p95 263 vs. 482 ms). At 3500 VUs, with pool wait at 360 ms, `app` p95 is 127 ms again.
- Time outside the handler (client − server p50) is 9 ms at 3200 VUs and 22 ms at 3500 VUs.
- The host slowed during the 3500-VU run (probe 83 → 98 ms); the verdict is clear enough (p99 17 % over) not to need
  a rerun for the capacity number.
- `app_log_tail.txt` has no errors; feed-cache misses ≈ 25 per 10 s, as in node-express v06.
- Not released (tested this session on node-express, parent v06): feed-cache TTL 5 s (3200 VUs: FAIL, 1487 req/s,
  no gain over 1 s), nginx as plain reverse proxy (3000 VUs: FAIL, 1103 req/s, nginx 15 % CPU) and nginx
  `proxy_cache` for the feed instead of the app cache (3000 VUs: FAIL, 1473 req/s, nginx 17 % CPU). On 1 vCPU a proxy
  costs about as much CPU as it saves.

#### Next idea

A faster runtime / HTTP layer for the same code: **Bun** (`Bun.serve` or `node:http` on Bun) as `node-http`'s next
tag, or uWebSockets.js. Before pushing past ≈ 3500 VUs, recreate the load generator with 8 vCPU (new
`LOADGEN_LABEL`) and rerun the current best at its edge for comparability. Then other stacks (Go, Rust) with the same
1 s feed cache.

### python-fastapi-v01-baseline

[Full report](results/python-fastapi-v01-baseline/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/python-fastapi-v01-baseline)

#### What changed

New stack `apps/python-fastapi/`, no parent (first Python tag). The design matches **node-express v01** (the Node
baseline): one process, **no connection pool** (a new asyncpg connection per request, closed before the response is
sent; `conn` = connect + auth + close), **no feed cache**, writes as one CTE statement (as in every current stack),
`Server-Timing` on every response. Idiomatic FastAPI: route decorators, handlers return dicts that FastAPI encodes
(`jsonable_encoder` + `json.dumps`). Path, query and body parsing are done by hand so status codes and error bodies
match the other stacks (FastAPI's own validation would answer 422 with a different body); unknown routes and methods
answer 404 `{"error":"not found"}`; `/docs` and `/openapi.json` are off. `Server-Timing` comes from a plain ASGI
middleware (outermost app middleware), which also ignores trailing slashes like the JavaScript routers. The parity
check (39 requests on a fresh DB) gave responses identical to the node-http reference. App code from commit `d21ccdf`.

#### Summary

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

#### Observations

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

#### Next idea

`python-fastapi-v02-pool` (parent v01): `asyncpg.create_pool(max_size=10)`, one pooled connection per request, the
only change (prepared statements are then cached per pooled connection). Start near the expected order of magnitude
(Node v02: 1350 VUs; Python's higher app CPU per request suggests well below that, e.g. 400–800 VUs).

### python-fastapi-v02-pool

[Full report](results/python-fastapi-v02-pool/config.md) · [Release](https://github.com/programmerpranit/1gb-server-test/releases/tag/python-fastapi-v02-pool)

#### What changed

Parent: `python-fastapi-v01-baseline`. One change: **a connection pool** — `asyncpg.create_pool(min_size=10,
max_size=10)` created at startup (FastAPI lifespan), instead of a new connection per request. Every request acquires
one connection for all its queries and releases it before the response is sent. asyncpg's pool defaults otherwise:
on release it runs the reset query (`SELECT pg_advisory_unlock_all(); CLOSE ALL; UNLISTEN *; RESET ALL;`, one round
trip), and prepared statements are cached per connection (100 statements). `conn` now measures pool acquire (waiting
for a free connection) plus release. The 10 connections are opened at startup (asyncpg's default `min_size=10`);
the Node pools opened them on demand. The parity check gave responses identical to the node-http reference. App code
from commit `57434bf`.

#### Summary

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

#### Observations

- 500 VUs, first run (replaced by the rerun): FAIL on p99 only — 246.8 req/s, p50 34 / p95 517 / p99 4363 ms, CPU
  91.6 % (Python 61.8 / PG 24.4), 3.71 ms CPU/req, probe 111 / 85 ms. A ≈ 6 s stretch at 100 % CPU (app CPU up to
  78 %) built a queue with pool waits up to 6.3 s. The rerun on a faster host (probe 94 ms, 3.26 ms CPU/req) passed
  with p99 194 ms; 450 also passed with a better tail than 400. Near the edge single runs swing with host speed.
- 600 VUs passed although the host was slow at the start (probe 123 ms before, 91 after).
- `app` p95 stays ≈ 2 ms at every level: per-request Python work is small, but ≈ 2.2 ms of CPU per request across
  the event loop, HTTP parsing and the framework is what saturates the vCPU at ≈ 300 req/s.
- Time outside the app (client − server): p50 4–15 ms, p95 19–23 ms at every level.
- `app_log_tail.txt` has no errors at any level.

#### Next idea

`python-fastapi-v03-feed-cache-1s` (parent v02): in-process cache of `GET /posts` (all pages, key limit + before,
TTL 1 s, single-flight, cached as the encoded JSON body), the only change — the same cache as node-express v06 /
node-http. Then uvloop + httptools, orjson, more workers.
<!-- ANALYSIS:END -->

## All runs

One row per (tag, VU level). `scripts/run_test.sh` upserts rows automatically.

- **Steady** columns cover only the 60 s hold phase; Total req and Error % cover the whole 2 min.
- Latency is k6 `http_req_duration` (server time + network to the load generator). Compare runs only with the same
  **Load from**.
- **App MB / PG MB** are PSS summed over the systemd unit's processes (Postgres shared memory is not double counted).
  **Used MB** is `MemTotal - MemAvailable` for the whole droplet.
- **CPU %** is whole-machine busy time out of one vCPU; **Steal %** is time taken by the hypervisor (noisy neighbours).
- **Error** = any non-2xx response or a request that exceeded the 10 s timeout.
- **Pass** uses the criteria above (steady p50/p95/p99, whole-run errors).
- **Srv / Conn** come from the app's `Server-Timing` header (steady phase): **Srv** = time inside the app,
  **Conn** = time to get a DB connection (connect + auth without a pool, waiting for a free connection with a pool).
  Client latency − Srv = time outside the handler (network, queues, load generator).

<!-- RESULTS:START -->
| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 100 | PASS | 46.7 | 2804 | 4368 | 242.4 | 548.9 | 742.4 | 958.8 | 1141 | 227.1 | 693.7 | 596.6 | 0 | 108 | 70 | 446 | 0 | 97.7 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v01-baseline | node-express | 110 | FAIL | 49.8 | 2986 | 4643 | 362.3 | 704.6 | 852.2 | 991.6 | 1096 | 337.2 | 783.8 | 665.6 | 0 | 104 | 64 | 432 | 0 | 98.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 500 | PASS | 271.4 | 16287 | 24650 | 3.6 | 10.5 | 17.8 | 43.0 | 108 | 2.4 | 11.8 | 0.1 | 0 | 107 | 104 | 458 | 0 | 56.4 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1000 | PASS | 538.0 | 32282 | 49105 | 7.2 | 45.4 | 62.7 | 141.3 | 281 | 4.7 | 44.8 | 23.8 | 0 | 114 | 108 | 471 | 0 | 84.2 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1500 | FAIL | 546.8 | 32810 | 54948 | 832.0 | 1273.1 | 1377.3 | 1441.7 | 1565 | 814.4 | 1348.5 | 1329.9 | 0 | 133 | 125 | 506 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1200 | PASS | 608.5 | 36512 | 55986 | 82.2 | 307.3 | 428.3 | 716.9 | 847 | 66.3 | 410.1 | 386.8 | 0 | 116 | 110 | 477 | 0 | 98.5 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1250 | PASS | 575.6 | 34538 | 54611 | 308.8 | 495.0 | 634.4 | 839.7 | 1100 | 292.4 | 616.0 | 596.7 | 0 | 122 | 109 | 501 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1300 | PASS | 651.1 | 39069 | 59600 | 107.9 | 365.0 | 465.9 | 652.0 | 752 | 93.6 | 449.8 | 429.3 | 0 | 119 | 108 | 478 | 0 | 99.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1350 | PASS | 619.1 | 37149 | 58671 | 324.7 | 577.7 | 689.8 | 775.8 | 864 | 309.6 | 670.4 | 651.2 | 0 | 124 | 108 | 484 | 0 | 100.0 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1400 | FAIL | 517.7 | 31061 | 51671 | 895.2 | 1273.5 | 1319.7 | 1389.0 | 1491 | 878.7 | 1298.7 | 1275.7 | 0 | 131 | 125 | 509 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1400 | FAIL | 604.3 | 36259 | 58260 | 407.5 | 788.5 | 897.3 | 1144.6 | 1279 | 374.6 | 856.8 | 815.9 | 0 | 130 | 139 | 525 | 0 | 100.0 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1500 | FAIL | 524.5 | 31468 | 54877 | 909.1 | 1498.5 | 1935.5 | 2450.0 | 2648 | 874.9 | 1892.1 | 1832.1 | 0 | 136 | 155 | 542 | 0 | 100.0 | 0.5 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1300 | FAIL | 562.6 | 33755 | 54136 | 414.0 | 936.4 | 1031.1 | 1114.0 | 1237 | 379 | 990.3 | 942.6 | 0 | 126 | 137 | 518 | 0 | 99.2 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1350 | FAIL | 496.5 | 29789 | 48359 | 859.7 | 1198.3 | 1249.3 | 1325.9 | 1475 | 816.1 | 1201.2 | 1154.8 | 0 | 131 | 137 | 524 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1200 | PASS | 574.0 | 34443 | 53684 | 181.7 | 567.0 | 755.7 | 971.9 | 1108 | 146.8 | 706.6 | 655.8 | 0 | 120 | 138 | 513 | 0 | 98.8 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v04-cte-writes | node-express | 1300 | FAIL | 542.2 | 32532 | 53633 | 532.4 | 1060.1 | 1242.8 | 1515.5 | 1580 | 506.3 | 1206.3 | 1184.3 | 0 | 129 | 111 | 491 | 0 | 99.5 | 0.6 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v04-cte-writes | node-express | 1400 | PASS | 660.5 | 39631 | 61864 | 192.8 | 671.6 | 787.7 | 990.5 | 1092 | 172.7 | 764.3 | 741.7 | 0 | 126 | 110 | 486 | 0 | 99.7 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v04-cte-writes | node-express | 1500 | FAIL | 613.6 | 36817 | 61506 | 495.9 | 1155.3 | 1315.9 | 1438.5 | 1531 | 474.5 | 1273.7 | 1252.0 | 0 | 136 | 111 | 516 | 0 | 99.9 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v04-cte-writes | node-express | 1350 | FAIL | 569.0 | 34139 | 54435 | 510.8 | 766.3 | 847.1 | 952.8 | 1018 | 488.8 | 819.5 | 802.5 | 0 | 126 | 127 | 506 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v05-prepared | node-express | 1000 | PASS | 534.0 | 32038 | 48780 | 12.8 | 80.3 | 104.6 | 186.6 | 306 | 6.9 | 73.9 | 56.1 | 0 | 114 | 113 | 477 | 0 | 89.3 | 0.8 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v05-prepared | node-express | 1300 | PASS | 633.1 | 37984 | 59537 | 199.9 | 367.6 | 445.2 | 812.9 | 914 | 176.7 | 422.1 | 405.4 | 0 | 119 | 113 | 483 | 0 | 99.3 | 0.7 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v05-prepared | node-express | 1400 | PASS | 645.1 | 38707 | 61337 | 319.7 | 605.8 | 675.8 | 801.5 | 891 | 298 | 652.6 | 634.9 | 0 | 127 | 114 | 493 | 0 | 99.1 | 0.9 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v05-prepared | node-express | 1500 | FAIL | 687.6 | 41254 | 65030 | 318.0 | 598.9 | 730.9 | 1168.2 | 1271 | 297.1 | 710.6 | 693.0 | 0 | 130 | 114 | 497 | 0 | 99.8 | 0.5 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 1000 | PASS | 543.0 | 32577 | 49477 | 2.0 | 5.4 | 8.4 | 24.0 | 90 | 0.7 | 4.3 | 0.1 | 0 | 113 | 111 | 472 | 0 | 52.8 | 0.5 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 1500 | PASS | 810.1 | 48609 | 73764 | 3.2 | 18.8 | 32.8 | 62.3 | 132 | 0.8 | 13.2 | 0.1 | 0 | 121 | 114 | 497 | 0 | 72.5 | 1.5 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 2000 | PASS | 1079.1 | 64746 | 98287 | 3.7 | 26.8 | 48.5 | 95.9 | 154 | 0.8 | 25.5 | 7.9 | 0 | 127 | 115 | 501 | 0 | 78.7 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 2500 | PASS | 1324.8 | 79488 | 121159 | 12.4 | 112.7 | 192.3 | 435.9 | 496 | 1.4 | 165.6 | 126.6 | 0 | 132 | 116 | 515 | 0 | 91.9 | 0.7 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 3000 | PASS | 1541.0 | 92462 | 141899 | 29.4 | 342.6 | 573.0 | 854.6 | 966 | 7.6 | 551.7 | 451.8 | 0 | 156 | 130 | 541 | 0 | 98.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v06-feed-cache-1s | node-express | 3200 | FAIL | 1604.2 | 96250 | 149284 | 42.4 | 388.4 | 725.1 | 1640.9 | 1775 | 19.2 | 709.8 | 481.8 | 0 | 161 | 131 | 548 | 0 | 98.7 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v01-express-v06-port | node-http | 3200 | PASS | 1677.6 | 100656 | 154434 | 10.9 | 196.9 | 392.4 | 835.3 | 990 | 1.6 | 361.6 | 262.6 | 0 | 144 | 133 | 523 | 0 | 92.4 | 0.6 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v01-express-v06-port | node-http | 3500 | FAIL | 1778.5 | 106711 | 165366 | 29.5 | 335.9 | 470.8 | 1175.4 | 1303 | 7 | 428.4 | 359.6 | 0 | 147 | 133 | 537 | 0 | 95.4 | 0.9 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v02-bun | node-http | 3500 | PASS | 1854.7 | 111279 | 168427 | 5.8 | 75.1 | 166.1 | 424.6 | 591 | 0.8 | 149.4 | 101.7 | 0 | 102 | 129 | 498 | 0 | 89.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v02-bun | node-http | 4000 | PASS | 2081.6 | 124896 | 191899 | 14.2 | 280.3 | 436.2 | 823.3 | 976 | 1.9 | 420.7 | 367.7 | 0 | 101 | 131 | 489 | 0 | 93.6 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v02-bun | node-http | 4500 | FAIL | 2097.4 | 125845 | 199838 | 247.4 | 744.3 | 901.9 | 1044.6 | 1547 | 217.3 | 883.6 | 861.2 | 0 | 113 | 136 | 499 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v02-bun | node-http | 4200 | PASS | 2077.8 | 124666 | 194707 | 46.7 | 589.2 | 752.4 | 850.6 | 1208 | 21.9 | 726.4 | 687.0 | 0 | 108 | 136 | 498 | 0 | 97.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v03-bun-sql | node-http | 4500 | FAIL | 1954.7 | 117280 | 189837 | 416.9 | 956.9 | 1087.9 | 1546.8 | 1785 | 397.7 | 1060 | 998.8 | 0 | 109 | 132 | 500 | 0 | 99.8 | 0.7 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v04-bun-serve | node-http | 4500 | PASS | 2324.2 | 139452 | 214994 | 14.8 | 174.4 | 319.2 | 911.5 | 1485 | 1.5 | 270.7 | 193.5 | 0 | 59 | 133 | 464 | 0 | 94.1 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-http-v04-bun-serve | node-http | 4700 | FAIL | 2143.5 | 128609 | 204841 | 162.6 | 1001.0 | 1188.2 | 1546.8 | 1837 | 128.9 | 1157.9 | 1095.5 | 0 | 61 | 133 | 461 | 0 | 99.1 | 0.6 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v01-baseline | python-fastapi | 100 | FAIL | 35.8 | 2146 | 3601 | 954.8 | 1475.6 | 1721.6 | 1969.3 | 2220 | 885.9 | 1606.9 | 1273.2 | 0 | 65 | 71 | 449 | 0 | 100.0 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v01-baseline | python-fastapi | 70 | FAIL | 32.2 | 1930 | 3005 | 213.2 | 734.7 | 1006.0 | 1182.4 | 1401 | 199.3 | 934.5 | 739.2 | 0 | 58 | 52 | 414 | 0 | 92.6 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v01-baseline | python-fastapi | 60 | PASS | 29.9 | 1793 | 2752 | 115.2 | 364.8 | 490.0 | 618.8 | 713 | 109.1 | 456.5 | 364.8 | 0 | 53 | 46 | 397 | 0 | 86.9 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v02-pool | python-fastapi | 400 | PASS | 211.9 | 12712 | 19417 | 17.8 | 127.9 | 199.2 | 384.4 | 1322 | 13.5 | 176.2 | 154.0 | 0 | 65 | 108 | 455 | 0 | 83.8 | 2.3 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v02-pool | python-fastapi | 450 | PASS | 239.8 | 14388 | 21929 | 16.0 | 73.2 | 104.3 | 245.7 | 634 | 12.2 | 82.9 | 61.3 | 0 | 69 | 108 | 459 | 0 | 84.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v02-pool | python-fastapi | 500 | PASS | 266.1 | 15965 | 24327 | 20.2 | 85.1 | 114.0 | 193.8 | 530 | 15.3 | 95.4 | 77.4 | 0 | 70 | 110 | 462 | 0 | 86.7 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v02-pool | python-fastapi | 600 | PASS | 306.9 | 18417 | 28367 | 42.6 | 293.9 | 434.6 | 862.6 | 2715 | 32.6 | 415.1 | 398.7 | 0 | 71 | 112 | 463 | 0 | 94.3 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| python-fastapi-v02-pool | python-fastapi | 650 | FAIL | 297.8 | 17865 | 28604 | 168.7 | 813.5 | 1152.8 | 2015.9 | 4945 | 154.1 | 1130.5 | 1109.7 | 0 | 76 | 113 | 469 | 0 | 99.2 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
<!-- RESULTS:END -->

## Reproducing

```bash
cp .env.example .env            # fill SERVER_HOST, DB_PASSWORD, LOADGEN_HOST, TARGET_HOST, LOADGEN_LABEL
scripts/provision.sh            # once per target droplet
scripts/seed_db.sh              # once, or when schema/converter changes
scripts/provision_loadgen.sh    # once per load-generator droplet (installs pinned k6)
scripts/deploy.sh node-express  # each time the app changes
scripts/run_test.sh node-express-v01-baseline 100 200 300   # live dashboard: http://localhost:5665
scripts/release.sh node-express-v01-baseline
```
