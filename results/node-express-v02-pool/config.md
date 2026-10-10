# node-express-v02-pool

## Summary
**Capacity: at least 900 VUs at 461.0 req/s (27,660 req/min)**, steady p50 66 ms / p95 318 ms / p99 458 ms,
0 % errors. All seven tested levels (100–900) passed. 900 VUs is close to the CPU ceiling, so the limit is
probably not far above it. Compared with v01-baseline-r2 (90 VUs / 42.8 req/s), that is at least **10× the users
and 10.8× the throughput**.

- **The pool removed the bottleneck.** CPU per request fell from about 20 ms to about **2.0–2.9 ms (7–10× cheaper)**.
  It gets cheaper as load rises because fixed overhead is spread over more requests. Postgres's share of CPU fell
  from about 60 % to about 50 %, because it no longer starts a backend and checks a SCRAM password for every request.
- **The CPU ceiling is now close.** Average CPU: 58 % at 500 VUs, 79 % at 700, **91 % at 900** (Node 39 %,
  Postgres 45 %). At 900 VUs, 27 of 140 one-second samples were ≥ 95 %. p50 rose from 30 ms to 66 ms, the first sign
  of requests queueing on the server. The ceiling is about 500 req/s (≈ 2 ms CPU per request), so capacity is
  probably around 950–1,000 VUs.
- **Throughput still matched offered load** at every level (about 0.51–0.53 req/s per VU): 263 → 367 → 461 req/s.
- **The p95/p99 tail does not follow server load.** From 400 to 900 VUs, CPU went from 51 % to 91 %, but p95 only
  moved 284 → 233 → 282 → 318 ms and p99 stayed at 450–520 ms. Max actually *fell* (1.9 s at 500 → 0.7 s at 900).
  The tail that appeared at 400 VUs is therefore mostly **not** server CPU. More likely it is the 10-connection pool
  queue during bursts, or the load generator (k6 driving 400–900 VUs from a MacBook over home Wi-Fi). Only
  server-side request timing can separate the two.
- **Memory is flat.** Peak 472 MB used (489 MB still available) at 900 VUs. Node about 113 MB, Postgres about 108 MB
  (10 long-lived backends). No swap. 900 open client sockets cost Node only about 10 MB more than 100 did.
- **No errors** at any level. Postgres connections are capped at 10 by the pool.
- **Next:** find where it breaks. Suggested levels: 1000 and 1100 (the user picks). Then add server-side timing
  (e.g. a `Server-Timing` header) to explain the tail, before tuning the pool size.

## What changed vs. the previous tag
Parent: `node-express-v01-baseline-r2`. One change: **`pg.Pool` with default settings (max 10)** instead of a new
`pg.Client` per request. Each request still borrows one connection for all its queries, including its transaction.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (commit `ed8a59c`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: `pg.Pool` defaults — max 10, idle timeout 10 s, no connection timeout (requests queue)
- Writes: explicit `BEGIN/COMMIT` on the borrowed connection
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: MacBook on home Wi-Fi (`macbook-home-wifi`), k6 v2.3.0, ~40 ms RTT to the droplet

## Results
Levels chosen by the user: 100, 150, 200; then 400, 500; then 700 → 900 (fallbacks 600/800 were not needed because both passed).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Max ms | Error % | CPU % (app / PG) | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | PASS | 53.3 | 38 | 46 | 68 | 200 | 0.00 | 18.2 (8.7 / 6.3) | 101 | 68 | 410 |
| 150 | PASS | 79.8 | 38 | 51 | 154 | 715 | 0.00 | 26.2 (12.5 / 9.3) | 102 | 85 | 432 |
| 200 | PASS | 106.3 | 38 | 55 | 287 | 737 | 0.00 | 30.5 (14.5 / 11.5) | 104 | 89 | 443 |
| 400 | PASS | 209.4 | 40 | 284 | 447 | 644 | 0.00 | 50.9 (23.0 / 21.8) | 107 | 100 | 454 |
| 500 | PASS | 263.1 | 30 | 233 | 520 | 1900 | 0.00 | 57.8 (25.8 / 25.5) | 109 | 103 | 458 |
| 700 | PASS | 367.0 | 30 | 282 | 494 | 683 | 0.00 | 78.6 (33.9 / 36.9) | 110 | 106 | 464 |
| **900** | **PASS** | **461.0** | **66** | **318** | **458** | 746 | 0.00 | 91.3 (39.0 / 45.3) | 113 | 108 | 472 |

Same 100 VUs vs. v01-baseline-r2: 53.3 vs. 43.7 req/s, p95 46 vs. 890 ms, CPU 18 % vs. 98 %.

## Observations
- Steal time peaked at 1.4 % (700 VUs). That is still small, but it is the highest seen so far.
- At 400–900 VUs per-endpoint p95 is 166–354 ms. Comments (4 round trips) are the slowest at 321–354 ms, but the
  spread is narrow. Up to 200 VUs, per-endpoint p95 is 41–68 ms at every level. Even write endpoints with 4 round trips (comment, like) add only a few
  ms over reads, because Postgres is local and the connection is already open.
- Steal time is 0.5–0.9 %, slightly higher than in v01 but still negligible.
- `app_log_tail.txt` has no errors at any level.
- Measured latency is now dominated by the network. Server-side gains from here on will mostly show up in capacity
  and in p99/max, not in p50.

## Next idea
Push `node-express-v02-pool` to 1000 / 1100 VUs (user to choose) to find the break point. Then add server-side
timing and test pool sizes (5 / 20) to explain the p95/p99 tail.
Then try `node-express-v03-pool-size` (vary max 5 / 20) to see whether the pool queue causes the p99 tail.
