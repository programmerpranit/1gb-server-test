# node-express-v02-pool

## Summary
**Capacity: at least 200 VUs at 106.3 req/s (6,378 req/min)**, steady p50 38 ms / p95 55 ms / p99 287 ms,
0 % errors. Every tested level passed, so the real limit is still above 200 VUs. Compared with
v01-baseline-r2 (90 VUs / 42.8 req/s), that is at least **2.2× the users and 2.5× the throughput**.

- **The pool removed the bottleneck.** CPU per request fell from about 20 ms to about **2.9 ms (≈7× cheaper)**. At
  200 VUs the whole droplet averages only 30.5 % CPU (Node 14.5 %, Postgres 11.5 %). In v01 it sat at 94–98 % at
  just 90–100 VUs. Postgres's share went from about 60 % of CPU to under 40 %, because it no longer starts a backend
  and checks a SCRAM password for every request.
- **The server is not saturated.** Throughput tracks offered load exactly (about 0.53 req/s per VU): 53 → 80 →
  106 req/s. p50 stays flat at 38 ms, which is the Mac → droplet network round trip (about 40 ms). Server time is a
  few milliseconds. Load average stays below 0.7.
- **Tail latency is creeping up.** p99 goes 68 → 154 → 287 ms and max reaches about 0.7 s, while p95 stays at
  46–55 ms. Likely causes: short bursts where more than 10 requests wait for a pool connection, or Wi-Fi jitter on
  the load-generator side. This is still well within the 1000 ms limit. Watch it at higher levels.
- **Memory is flat and modest.** Peak 443 MB used (518 MB still available). Node about 104 MB, Postgres about 89 MB
  with 10 long-lived backends (vs. 41–66 MB of short-lived ones in v01). No swap.
- **No errors.** Postgres connections are capped at 10 by the pool, so `max_connections` (100) can no longer be hit.
- **Next:** find the real limit of this configuration before changing anything else. A rough CPU extrapolation
  (2.9 ms CPU per request) puts the ceiling near 300 req/s, around 550–600 VUs, though the pool size (10) or the
  event loop may cap it earlier. Suggested levels: 300, 400, 500, 600. The user picks the levels.

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
Levels chosen by the user: 100, 150, 200.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Max ms | Error % | CPU % (app / PG) | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | PASS | 53.3 | 38 | 46 | 68 | 200 | 0.00 | 18.2 (8.7 / 6.3) | 101 | 68 | 410 |
| 150 | PASS | 79.8 | 38 | 51 | 154 | 715 | 0.00 | 26.2 (12.5 / 9.3) | 102 | 85 | 432 |
| **200** | **PASS** | **106.3** | **38** | **55** | **287** | 737 | 0.00 | 30.5 (14.5 / 11.5) | 104 | 89 | 443 |

Same 100 VUs vs. v01-baseline-r2: 53.3 vs. 43.7 req/s, p95 46 vs. 890 ms, CPU 18 % vs. 98 %.

## Observations
- Per-endpoint p95 is 41–68 ms at every level. Even write endpoints with 4 round trips (comment, like) add only a few
  ms over reads, because Postgres is local and the connection is already open.
- Steal time is 0.5–0.9 %, slightly higher than in v01 but still negligible.
- `app_log_tail.txt` has no errors at any level.
- Measured latency is now dominated by the network. Server-side gains from here on will mostly show up in capacity
  and in p99/max, not in p50.

## Next idea
Push `node-express-v02-pool` to higher VU levels (user to choose, e.g. 300 / 400 / 500 / 600) to find its limit.
Then try `node-express-v03-pool-size` (vary max 5 / 20) to see whether the pool queue causes the p99 tail.
