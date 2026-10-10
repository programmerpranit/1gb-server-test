# node-express-v04-cte-writes

## Summary
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

## What changed vs. the previous tag
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

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `4af516b`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: `pg.Pool` defaults, max 10
- Writes: **single statement (CTE)**, no explicit transactions
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2 (≈ 2 ms RTT)

## Results
Levels chosen by the user: 1300, 1400, 1500, then 1350.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1300 | FAIL (p50, p95, p99) | 542.2 | 532.4 | 1242.8 | 1515.5 | 0.00 | 506.3 / 1206.3 | 488.2 / 1184.3 | 14.7 / 37.8 | 99.5 (42.0 / 49.8) | 491 |
| 1350 | FAIL (p50, p95) | 569.0 | 510.8 | 847.1 | 952.8 | 0.00 | 488.8 / 819.5 | 471.5 / 802.5 | 14.4 / 34.4 | 100.0 (42.5 / 50.7) | 506 |
| **1400** | **PASS** (marginal) | **660.5** | **192.8** | **787.7** | **990.5** | 0.00 | 172.7 / 764.3 | 158.9 / 741.7 | 11.9 / 29.9 | 99.7 (41.2 / 51.8) | 486 |
| 1500 | FAIL (p95, p99) | 613.6 | 495.9 | 1315.9 | 1438.5 | 0.00 | 474.5 / 1273.7 | 458.3 / 1252.0 | 13.0 / 33.5 | 99.9 (42.5 / 50.1) | 516 |

**Capacity (rule): 1400 VUs at 660.5 req/s**, but 1300 and 1350 failed; see Summary. First fail above it: 1500 VUs.

Same levels, v02 (BEGIN/COMMIT writes) vs. v04 (single-statement writes), both pool 10:

| VUs | v02 req/s | v02 p95 / p99 ms | v04 req/s | v04 p95 / p99 ms | db p95 v02 → v04 |
|---|---|---|---|---|---|
| 1300 | 651.1 | 466 / 652 (PASS) | 542.2 | 1243 / 1516 (FAIL) | 37 → 38 |
| 1350 | 619.1 | 690 / 776 (PASS) | 569.0 | 847 / 953 (FAIL) | 40 → 34 |
| 1400 | 517.7 | 1320 / 1389 (FAIL) | 660.5 | 788 / 991 (PASS) | 48 → 30 |
| 1500 | 546.8 | 1377 / 1442 (FAIL) | 613.6 | 1316 / 1439 (FAIL) | 46 → 34 |

## Observations
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

## Next idea
`node-express-v05-prepared` (parent v04): named queries in `pg` (`{ name, text, values }`), so each pooled
connection parses and plans every statement once and reuses the plan. Postgres uses half the CPU; parse/plan is a
real part of it for these short indexed queries. Run one unsaturated level (1000 VUs) plus the edge levels.
