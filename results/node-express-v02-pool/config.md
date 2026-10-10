# node-express-v02-pool

## Summary
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

## What changed vs. the previous tag
One change from `node-express-v01-baseline`: a `pg.Pool` with default settings (max 10 connections, idle timeout
10 s) instead of a new `pg.Client` per request. Each request borrows one connection for all its queries and returns
it before the response is sent. A connection whose ROLLBACK failed is destroyed instead of being reused.
`Server-Timing` `conn` now measures the wait for a pooled connection (or the connect while the pool fills).

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `820e2e5`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: **`pg.Pool` defaults, max 10**
- Writes: explicit `BEGIN/COMMIT` on the request's connection
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2 (≈ 2 ms RTT)

## Results
Levels chosen by the user: 500, 1000, 1500, 1200, 1250, 1300, 1350, 1400 (in that order).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | PASS | 271.4 | 3.6 | 17.8 | 43.0 | 0.00 | 2.4 / 11.8 | 0 / 0.1 | 2.1 / 11.1 | 56.4 (26.0 / 24.3) | 458 |
| 1000 | PASS | 538.0 | 7.2 | 62.7 | 141.3 | 0.00 | 4.7 / 44.8 | 0 / 23.8 | 4.4 / 24.5 | 84.2 (36.0 / 41.4) | 471 |
| 1200 | PASS | 608.5 | 82.2 | 428.3 | 716.9 | 0.00 | 66.3 / 410.1 | 50.3 / 386.8 | 10.2 / 38.1 | 98.5 (42.0 / 50.1) | 477 |
| 1250 | PASS | 575.6 | 308.8 | 634.4 | 839.7 | 0.00 | 292.4 / 616.0 | 275.1 / 596.7 | 11.9 / 42.4 | 100.0 (42.9 / 50.3) | 501 |
| 1300 | PASS | 651.1 | 107.9 | 465.9 | 652.0 | 0.00 | 93.6 / 449.8 | 77.6 / 429.3 | 10.2 / 36.6 | 99.4 (42.4 / 50.9) | 478 |
| **1350** | **PASS** | **619.1** | **324.7** | **689.8** | **775.8** | 0.00 | 309.6 / 670.4 | 292.8 / 651.2 | 11.1 / 40.1 | 100.0 (43.0 / 50.6) | 484 |
| 1400 | FAIL (p50, p95, p99) | 517.7 | 895.2 | 1319.7 | 1389.0 | 0.00 | 878.7 / 1298.7 | 861.3 / 1275.7 | 12.9 / 48.1 | 100.0 (45.2 / 47.8) | 509 |
| 1500 | FAIL (p50, p95, p99) | 546.8 | 832.0 | 1377.3 | 1441.7 | 0.00 | 814.4 / 1348.5 | 795.5 / 1329.9 | 12.3 / 45.6 | 100.0 (45.7 / 47.5) | 506 |

**Capacity: 1350 VUs at 619.1 req/s.** First fail: 1400 VUs. Peak throughput: 651.1 req/s at 1300 VUs.

## Observations
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

## Next idea
`node-express-v03-pool-20` (or `-pool-5`): change only the pool size, to confirm the pool queue is a symptom of
CPU saturation and not a cause. Bigger gains should come from cutting CPU per request (prepared statements,
single-statement CTE writes, Postgres tuning).
