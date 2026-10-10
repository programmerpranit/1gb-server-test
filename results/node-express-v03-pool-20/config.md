# node-express-v03-pool-20

## Summary
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

## What changed vs. the previous tag
One change from `node-express-v02-pool`: `pg.Pool` `max` 10 → **20**. All other pool settings stay default.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `2a1e171`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: **`pg.Pool` max 20** (other settings default, idle timeout 10 s)
- Writes: explicit `BEGIN/COMMIT` on the request's connection
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2 (≈ 2 ms RTT)

## Results
Levels chosen by the user: 1400, 1500, 1300, 1350, 1200 (in that order).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1200** | **PASS** (marginal) | **574.0** | **181.7** | **755.7** | **971.9** | 0.00 | 146.8 / 706.6 | 113.3 / 655.8 | 21.5 / 85.1 | 98.8 (40.5 / 48.5) | 513 |
| 1300 | FAIL (p95, p99) | 562.6 | 414.0 | 1031.1 | 1114.0 | 0.00 | 379.0 / 990.3 | 347.2 / 942.6 | 22.9 / 89.9 | 99.2 (41.1 / 48.2) | 518 |
| 1350 | FAIL (p50, p95, p99) | 496.5 | 859.7 | 1249.3 | 1325.9 | 0.00 | 816.1 / 1201.2 | 773.9 / 1154.8 | 25.3 / 101.7 | 100.0 (42.8 / 46.8) | 524 |
| 1400 | FAIL (p95, p99) | 604.3 | 407.5 | 897.3 | 1144.6 | 0.00 | 374.6 / 856.8 | 342.2 / 815.9 | 21.1 / 82.8 | 100.0 (41.3 / 49.1) | 525 |
| 1500 | FAIL (p50, p95, p99) | 524.5 | 909.1 | 1935.5 | 2450.0 | 0.00 | 874.9 / 1892.1 | 836.0 / 1832.1 | 24.5 / 99.7 | 100.0 (43.4 / 46.3) | 542 |

**Capacity: 1200 VUs at 574.0 req/s.** First fail: 1300 VUs.

Same levels, v02 (pool 10) vs. v03 (pool 20):

| VUs | v02 req/s | v02 p95 / p99 ms | v03 req/s | v03 p95 / p99 ms | db p95 v02 → v03 |
|---|---|---|---|---|---|
| 1200 | 608.5 | 428 / 717 (PASS) | 574.0 | 756 / 972 (PASS) | 38 → 85 |
| 1300 | 651.1 | 466 / 652 (PASS) | 562.6 | 1031 / 1114 (FAIL) | 37 → 90 |
| 1350 | 619.1 | 690 / 776 (PASS) | 496.5 | 1249 / 1326 (FAIL) | 40 → 102 |
| 1400 | 517.7 | 1320 / 1389 (FAIL) | 604.3 | 897 / 1145 (FAIL) | 48 → 83 |
| 1500 | 546.8 | 1377 / 1442 (FAIL) | 524.5 | 1936 / 2450 (FAIL) | 46 → 100 |

## Observations
- 1400 VUs is the only level where v03 beat v02 (604 vs. 518 req/s), but both failed, and single runs near the
  ceiling swing this much (v02 itself scored 576 req/s at 1250 and 651 at 1300). The other four levels all favour
  pool 10, and `db` time is about 2× higher at every level, so the direction is clear.
- `app` time (routing, validation, JSON) is unchanged: p50 0.2 ms, p95 ≤ 1.9 ms.
- Per-endpoint p95 at 1200 VUs is uniform (591–836 ms client): every endpoint waits in the same pool queue. The
  write paths with 3–4 round trips (like/unlike, comment) are slowest because they hold a connection longest.
- No `53300 too many clients` errors: 20 pooled connections stay well under `max_connections=100`.

## Next idea
`node-express-v04-pool-5` (parent v02): pool `max` 10 → 5, to see whether fewer concurrent queries cut `db` time
enough to raise throughput. If not, keep pool 10 and move to per-request CPU savings.
