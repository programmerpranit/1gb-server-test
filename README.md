# 1 GB Server Test

How far can a **$6/month DigitalOcean droplet** (1 vCPU, 1 GB RAM, 25 GB SSD, 1000 GB transfer) go running the same
small social-feed API written in different languages and frameworks, with Postgres on the same box?

Every configuration is hit with the same 2-minute k6 test (60 s ramp from 0 to N virtual users, 60 s hold) and tagged
as a GitHub release with its code and raw results. Methodology, API contract and plan live in [CLAUDE.md](CLAUDE.md).

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

_Protocol-v1 results (MacBook load source) were dropped on 2026-10-10; see git history up to commit `e10904b`._

## Next steps

Updated after every test. The plan with all candidates is in [CLAUDE.md](CLAUDE.md#plan).

**Where node-express stands:** the best configuration is `node-express-v02-pool` (pool 10): 1350 VUs / 619 req/s.
It is CPU-bound: one vCPU split about evenly between Node and Postgres, ≈ 1.5 ms CPU per request. Latency past the
ceiling is pool wait, not slow queries. A bigger pool (v03, 20) made it worse, so the next gains must come from
**less CPU per request** or **less concurrency inside Postgres**.

1. **`node-express-v04-pool-5`** (parent v02): pool `max` 10 → 5. Checks whether fewer concurrent queries cut
   `db` time and contention enough to raise throughput. Compare at 1200 / 1300 / 1350 / 1400 VUs.
2. **Prepared statements** (named queries in `pg`): skip parse/plan on every query. Postgres uses about half the CPU,
   so this targets the larger half.
3. **Single-statement writes** (CTE instead of `BEGIN` / 2–3 queries / `COMMIT`): like, unlike and comment drop from
   3–4 round trips to 1 and hold a pooled connection for less time.
4. **Postgres tuning** (`shared_buffers`, `work_mem`, `synchronous_commit=off` as a labelled trade-off).
5. Then framework/runtime swaps on the best configuration: Fastify, Bun, cluster (expected little gain on 1 vCPU).

Each step is one tag that changes one thing from the best configuration so far. VU levels are chosen per run.

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
