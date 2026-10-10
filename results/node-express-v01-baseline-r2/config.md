# node-express-v01-baseline-r2

## Summary
**Capacity: 75 VUs at 39.1 req/s (2,345 req/min)**, steady p50 81 ms / p95 202 ms / p99 261 ms, 0 % errors.
The first failing level is 100 VUs: 43.7 req/s, p95 890 ms and p99 1025 ms, still with 0 % errors.

- **Bottleneck: CPU, and most of it is Postgres connection setup.** CPU use grows in step with load: 52 % at
  26 req/s, 78 % at 39 req/s, and 98 % at 44 req/s. That works out to about 20 ms of CPU per request: about 12 ms
  in Postgres and about 7 ms in Node. Postgres takes roughly 60 % of all CPU at every level. The queries themselves
  are cheap, indexed lookups of 20 rows. Most of Postgres's CPU therefore goes to opening a new connection per
  request: starting a backend process and checking the SCRAM password.
- **The ceiling is about 44 req/s.** Once the single vCPU is saturated, requests queue. Latency then jumps 4–5×
  between 75 and 100 VUs (p95 202 → 890 ms) while throughput rises only 12 %.
- **Memory is not a constraint.** Peak use is 487 MB of 961 MB, with no swap. Node holds steady at about 106 MB.
  Postgres stays at 41–66 MB because connections are short-lived.
- **No errors at or below 100 VUs.** In the earlier v01 run, errors only appeared at 250 VUs, when concurrent
  connections went over Postgres `max_connections` (100).
- **The results are repeatable.** At 100 VUs this run matches v01 within 1.6 % on throughput (43.7 vs. 44.4 req/s)
  and 8 % on p95 (890 vs. 824 ms). Steal time stayed at or below 0.3 %.
- **Next:** add a connection pool (`node-express-v02-pool`). It removes the per-request connection setup, which is
  more than half of the CPU used per request. Expect capacity to roughly double or better.

## What changed vs. the previous tag
Nothing in the app or server. This is a re-run of `node-express-v01-baseline` under the new protocol.
- New pass criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, and whole-run errors < 1 %.
- New capacity search: climb the ladder, then binary-search in 25-VU steps.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (commit `3632ae7`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: **no pool** — new `pg.Client` per request, closed before responding
- Writes: explicit `BEGIN/COMMIT` on the request's connection
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: MacBook on home Wi-Fi (`macbook-home-wifi`), k6 v2.3.0, ~40 ms RTT to the droplet

## Results
Search order: 100 (fail) → 50 (pass) → 75 (pass). The search stopped because the gap is 25 VUs.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | CPU % (app / PG) | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|
| 50 | PASS | 26.4 | 50 | 118 | 171 | 0.00 | 52.0 (17.7 / 31.2) | 103 | 42 | 399 |
| **75** | **PASS** | **39.1** | **81** | **202** | **261** | 0.00 | 78.2 (26.3 / 48.0) | 106 | 41 | 409 |
| 100 | FAIL (p95, p99) | 43.7 | 461 | 890 | 1025 | 0.00 | 97.9 (31.4 / 61.0) | 106 | 66 | 487 |

## Observations
- Per-endpoint p95 is nearly uniform: 102–125 ms at 50 VUs and 793–996 ms at 100 VUs. No endpoint is slow on its
  own. Every request pays the same fixed connection overhead and then waits in the same CPU queue.
- At 100 VUs, comment creation has the highest p95 (996 ms). It makes 4 round trips on one connection: BEGIN, INSERT,
  UPDATE, COMMIT. Write paths are next to benefit from fewer round trips, after pooling.
- Load average peaks at 3.4–5.2 on 1 vCPU, which shows queueing even at levels that pass.
- `app_log_tail.txt` has no errors at any level.
- The network floor is about 40 ms (Mac → droplet RTT), so the p50 of 50 ms at 50 VUs is mostly network.

## Next idea
`node-express-v02-pool`: `pg.Pool` with defaults (max 10). This is the one change. Then sweep the pool size.
