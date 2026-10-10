# node-express-v02-pool

## Summary
**Capacity: 1200 VUs at 564.5 req/s (33,867 req/min)**, steady p50 225 ms / p95 729 ms / p99 845 ms, 0 % errors.
This passes with little headroom: p95 is 9 % under its limit and p99 is 15 % under. The first failing level is
**1500 VUs**, where the droplet is CPU-saturated at **≈ 600 req/s**: p50 667 ms, p95 1143 ms, p99 1263 ms, still
0 % errors. Compared with v01-baseline-r2 (90 VUs / 42.8 req/s), that is **13× the users and 13.2× the throughput**.

- **The pool removed the bottleneck.** CPU per request fell from about 20 ms to about **1.7–2.9 ms (7–12× cheaper)**.
  It gets cheaper as load rises because fixed overhead is spread over more requests. Postgres's share of CPU fell
  from about 60 % to about 50 %, because it no longer starts a backend and checks a SCRAM password for every request.
- **The ceiling is about 600 req/s, reached at about 1150–1200 VUs.** Average CPU: 58 % at 500 VUs, 79 % at 700,
  91 % at 900, **95 % at 1200** (Node 39 %, Postgres 49 %), and **100 % at 1500** (Node 43 %, Postgres 50 %).
  At 1200 VUs, throughput (564.5 req/s) still almost matches offered load (about 0.47 req/s per VU), but latency
  has started to climb steeply: p50 went 66 → 225 ms and p95 went 318 → 729 ms from 900 to 1200 VUs. In the 1500-VU ramp, CPU hit 100 % at about 50 s,
  which is about 1200 VUs, and stayed there. Offered load at 1500 VUs is about 780 req/s, but only 599 req/s were
  served. The ceiling is higher than the earlier ~500 req/s estimate because CPU per request keeps falling under load.
- **Overload degrades gracefully: slow, not broken.** At 1500 VUs there were 0 errors, no timeouts and no crashes.
  Requests queue on the single CPU, and every endpoint lands on the same p95 (1100–1134 ms). Because k6 users wait
  for each response, the queue limits itself. Latency settles at about 1.1–1.3 s instead of growing without bound.
- **The p95/p99 tail below saturation does not follow server load.** From 400 to 900 VUs, CPU went from 51 % to 91 %,
  but p95 only moved 284 → 233 → 282 → 318 ms and p99 stayed at 450–520 ms. That tail is mostly **not** server CPU.
  More likely it is the 10-connection pool queue during bursts, or the load generator (k6 driving 400–900 VUs from a
  MacBook over home Wi-Fi). Only server-side request timing can separate the two.
- **Memory is still not a factor.** Peak 497 MB used (464 MB still available) at 1500 VUs. Node about 134 MB with
  1500 open sockets, Postgres about 109 MB (10 backends). No swap.
- **One CPU dip at 1200 VUs.** Around t = 91 s, CPU briefly fell to 54 % while all 1200 connections stayed open. That
  means the server was waiting for requests, which points to a stall on the load-generator or network side (Wi-Fi),
  not the server.
- **Next:** this configuration is mapped. Capacity is 1200 VUs, and the break lies between 1200 and 1500 VUs at a
  ~600 req/s CPU ceiling. To raise that ceiling, cut CPU per request. Options: server-side timing first, then pool
  size, single-statement writes, turning off ETag, or swapping Express for Fastify. Each change is its own tag.

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
Levels chosen by the user: 100, 150, 200; then 400, 500; then 700 → 900 (fallbacks 600/800 were not needed because both passed); then 1500; then 1200.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Max ms | Error % | CPU % (app / PG) | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | PASS | 53.3 | 38 | 46 | 68 | 200 | 0.00 | 18.2 (8.7 / 6.3) | 101 | 68 | 410 |
| 150 | PASS | 79.8 | 38 | 51 | 154 | 715 | 0.00 | 26.2 (12.5 / 9.3) | 102 | 85 | 432 |
| 200 | PASS | 106.3 | 38 | 55 | 287 | 737 | 0.00 | 30.5 (14.5 / 11.5) | 104 | 89 | 443 |
| 400 | PASS | 209.4 | 40 | 284 | 447 | 644 | 0.00 | 50.9 (23.0 / 21.8) | 107 | 100 | 454 |
| 500 | PASS | 263.1 | 30 | 233 | 520 | 1900 | 0.00 | 57.8 (25.8 / 25.5) | 109 | 103 | 458 |
| 700 | PASS | 367.0 | 30 | 282 | 494 | 683 | 0.00 | 78.6 (33.9 / 36.9) | 110 | 106 | 464 |
| 900 | PASS | 461.0 | 66 | 318 | 458 | 746 | 0.00 | 91.3 (39.0 / 45.3) | 113 | 108 | 472 |
| **1200** | **PASS** | **564.5** | **225** | **729** | **845** | 934 | 0.00 | 95.3 (39.4 / 49.0) | 120 | 108 | 480 |
| 1500 | FAIL (p50, p95, p99) | 598.9 | 667 | 1143 | 1263 | 1378 | 0.00 | 100.0 (43.1 / 50.1) | 134 | 109 | 497 |

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
Configuration mapped (capacity 1200 VUs, CPU ceiling ~600 req/s). Move on to experiments that cut CPU per request. Then add server-side
timing and test pool sizes (5 / 20) to explain the p95/p99 tail.
Then try `node-express-v03-pool-size` (vary max 5 / 20) to see whether the pool queue causes the p99 tail.
