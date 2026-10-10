# node-express-v01-baseline

## Summary
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

## What changed vs. the previous tag
First tag under protocol v2 (Server-Timing header + same-region load-generator droplet). Baseline for the
node-express stack.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `c9f7f4e`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: **no pool**. A new `pg.Client` per request, closed before responding
- Writes: explicit `BEGIN/COMMIT` on the request's connection
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2 (≈ 2 ms RTT)

## Results
Levels chosen by the user: 100, then 110.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **100** | **PASS** (marginal) | **46.7** | **242** | **742** | **959** | 0.00 | 227 / 694 | 181 / 597 | 38 / 112 | 97.7 (31.9 / 60.9) | 446 |
| 110 | FAIL (p95) | 49.8 | 362 | 852 | 992 | 0.00 | 337 / 784 | 280 / 666 | 48 / 133 | 98.4 (31.5 / 62.1) | 432 |

## Observations
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

## Next idea
`node-express-v02-pool`: `pg.Pool` with default settings (max 10). One change, with Server-Timing kept.
