# node-express-v02-pool

## Summary
**Capacity: at least 500 VUs at 263.1 req/s (15,785 req/min)**, steady p50 30 ms / p95 233 ms / p99 520 ms,
0 % errors. All five tested levels (100–500) passed, so the real limit is still above 500 VUs. Compared with
v01-baseline-r2 (90 VUs / 42.8 req/s), that is at least **5.5× the users and 6.1× the throughput**.

- **The pool removed the bottleneck.** CPU per request fell from about 20 ms to about **2.2–2.9 ms (7–9× cheaper)**.
  At 500 VUs the droplet averages 57.8 % CPU (Node 25.8 %, Postgres 25.5 %), and no 1-second sample reached 95 %.
  In v01 it sat at 94–98 % at just 90–100 VUs. Postgres's share went from about 60 % of CPU to under 40 %, because it no longer starts a backend
  and checks a SCRAM password for every request.
- **The server is still not saturated.** Throughput tracks offered load (about 0.53 req/s per VU) at every level:
  53 → 80 → 106 → 209 → 263 req/s. p50 stays at 30–40 ms, which is the Mac → droplet network round trip.
- **Latency spreads out from 400 VUs, but CPU doesn't explain it.** p95 jumps from 55 ms at 200 VUs to 284 ms at 400
  VUs, yet CPU averages only 51 %. Then 500 VUs is *better* at p95 (233 ms) than 400, with a worse p99 (520 ms) and
  a 1.9 s max. That non-monotonic pattern, plus the same p95 on every endpoint, points to queueing outside the server's
  average CPU. Candidates: sub-second CPU/event-loop bursts that 1-second samples hide, the 10-connection pool queue
  during bursts, or the load generator (k6 with 400–500 VUs on a MacBook over home Wi-Fi). These runs cannot tell
  them apart. Server-side request timing would.
- **Memory is flat and modest.** Peak 458 MB used (503 MB still available) even at 500 VUs. Node about 109 MB,
  Postgres about 103 MB with 10 long-lived backends (vs. 41–66 MB of short-lived ones in v01). No swap.
- **No errors.** Postgres connections are capped at 10 by the pool, so `max_connections` (100) can no longer be hit.
- **Next:** the limit is still unknown. Extrapolating CPU (57.8 % at 263 req/s) puts the CPU ceiling near
  450 req/s, around 850 VUs. Latency will probably break the p95/p99 limits before that. Suggested next levels:
  700 and 900. The user picks the levels. Separately, add server-side timing (e.g. a `Server-Timing` header or a
  sampled log) so a slow server can be told apart from a slow network or load generator.

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
Levels chosen by the user: 100, 150, 200, then 400 and 500 in a second session.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Max ms | Error % | CPU % (app / PG) | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | PASS | 53.3 | 38 | 46 | 68 | 200 | 0.00 | 18.2 (8.7 / 6.3) | 101 | 68 | 410 |
| 150 | PASS | 79.8 | 38 | 51 | 154 | 715 | 0.00 | 26.2 (12.5 / 9.3) | 102 | 85 | 432 |
| 200 | PASS | 106.3 | 38 | 55 | 287 | 737 | 0.00 | 30.5 (14.5 / 11.5) | 104 | 89 | 443 |
| 400 | PASS | 209.4 | 40 | 284 | 447 | 644 | 0.00 | 50.9 (23.0 / 21.8) | 107 | 100 | 454 |
| **500** | **PASS** | **263.1** | **30** | **233** | **520** | 1900 | 0.00 | 57.8 (25.8 / 25.5) | 109 | 103 | 458 |

Same 100 VUs vs. v01-baseline-r2: 53.3 vs. 43.7 req/s, p95 46 vs. 890 ms, CPU 18 % vs. 98 %.

## Observations
- At 400–500 VUs per-endpoint p95 is 198–354 ms. Comments (4 round trips) are the slowest at 321–354 ms, but the
  spread is narrow. Up to 200 VUs, per-endpoint p95 is 41–68 ms at every level. Even write endpoints with 4 round trips (comment, like) add only a few
  ms over reads, because Postgres is local and the connection is already open.
- Steal time is 0.5–0.9 %, slightly higher than in v01 but still negligible.
- `app_log_tail.txt` has no errors at any level.
- Measured latency is now dominated by the network. Server-side gains from here on will mostly show up in capacity
  and in p99/max, not in p50.

## Next idea
Push `node-express-v02-pool` further (user to choose, e.g. 700 / 900) to find its limit, ideally with server-side
timing in place.
Then try `node-express-v03-pool-size` (vary max 5 / 20) to see whether the pool queue causes the p99 tail.
