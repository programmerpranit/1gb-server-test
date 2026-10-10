# node-express-v05-prepared

## Summary
**Capacity: 1400 VUs at 645 req/s (38,707 req/min)**, steady p50 320 ms / p95 676 ms / p99 802 ms, 0 % errors.
The first failing level is **1500 VUs**: 688 req/s, p99 1168 ms (limit 1000), still 0 % errors. All levels from
1000 to 1400 VUs passed. **Likely a small gain over v04, not proven:** Postgres's CPU share dropped
consistently, but the throughput difference is within the host-speed noise.

- **Prepared statements cut Postgres's share of the CPU.** At saturation the split is Node ≈ 48 % / Postgres
  ≈ 43.5 % (v02/v04: ≈ 42 % / ≈ 50 %); at 1000 VUs Postgres uses 37 % vs. 42 % in v02. Skipping parse and plan
  on every query is visible as a lower Postgres share at every level, which does not depend on the host speed.
- **Throughput at saturation is the best so far, but by less than the noise.** v05 served 633 / 645 / 688 req/s
  at 1300 / 1400 / 1500 VUs (v04: 542 / 661 / 614; v02: 651 / 518 / 547). The average over those three levels is
  655 req/s vs. 606 (v04) and 572 (v02). Single runs swing ±60 req/s, so this is a hint of a ≈ 5–10 % gain.
- **The first 1500-VU run passed at 802 req/s and is not counted.** It reached p50 15 ms / p95 124 ms / p99 165 ms
  at only 92 % CPU, i.e. 1.15 ms CPU per request vs. 1.45–1.67 ms in every other run of every tag. The CPU cost
  per request was lower from the first seconds of the ramp (1.72 vs. ≈ 2.1 ms at the same 340 req/s), so the
  droplet's shared vCPU ran ≈ 30 % faster during that run (steal 0.07 %, so steal does not show it). The user asked
  for a rerun: 688 req/s, FAIL on p99. Only the rerun is in `vus-1500/`.
- **This explains much of the run-to-run noise in all tags.** A fixed CPU workload timed on the idle droplet varies
  ±20 % within seconds (67–98 ms). From the next tag on, every run records a host-speed probe before and after k6
  (`cpu_probe_before_ms` / `cpu_probe_after_ms`) and the CPU cost per request (`cpu_ms_per_req_steady`).
- **Memory is not a constraint.** Peak 497 MB used, Node ≤ 130 MB, Postgres ≤ 114 MB, no swap.
- **The runs are clean.** CPU never dropped below 70 % during any saturated hold phase, steal ≤ 0.9 %, the load
  generator averaged 19–22 % CPU, and `app_log_tail.txt` has no errors.
- **Next:** a profiling run of this configuration (below) shows Postgres's Memoize step costs ≈ 10 % of Postgres CPU
  in the feed queries for no benefit. v06: `enable_memoize = off`. After that: Fastify (Express + router are ≈ 24 %
  of Node's JS time), then the 1 s feed cache.

## What changed vs. the previous tag
Parent: `node-express-v04-cte-writes`. One change: **every query is a prepared statement** (a `pg` named query,
`{ name, text, values }`). The app derives a stable name per SQL text (`q1`, `q2`, ...), so each pooled connection
parses and plans each statement once and then only binds and executes it. Verified on the droplet: a named query run
twice on one connection shows one entry in `pg_prepared_statements` with 2 executions. All endpoints return the same
responses and status codes as v04.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `f7166fe`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: `pg.Pool` defaults, max 10
- Queries: **prepared statements (named queries)**
- Writes: single statement (CTE), no explicit transactions
- Server timing: `Server-Timing: conn, db, app, total` on every response
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2 (≈ 2 ms RTT)

## Results
Levels chosen by the user: 1000, 1300, 1400, 1500, then 1500 again (rerun replaces the first 1500 run).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | PASS | 534.0 | 12.8 | 104.6 | 186.6 | 0.00 | 6.9 / 73.9 | 0 / 56.1 | 6.4 / 26.1 | 89.3 (44.5 / 37.1) | 1.67 | 477 |
| 1300 | PASS | 633.1 | 199.9 | 445.2 | 812.9 | 0.00 | 176.7 / 422.1 | 161.2 / 405.4 | 12.4 / 29.9 | 99.3 (48.3 / 43.5) | 1.57 | 483 |
| **1400** | **PASS** | **645.1** | **319.7** | **675.8** | **801.5** | 0.00 | 298.0 / 652.6 | 281.6 / 634.9 | 12.1 / 30.3 | 99.1 (47.7 / 43.5) | 1.54 | 493 |
| 1500 | FAIL (p99) | 687.6 | 318.0 | 730.9 | 1168.2 | 0.00 | 297.1 / 710.6 | 282.9 / 693.0 | 11.8 / 28.9 | 99.8 (49.0 / 43.6) | 1.45 | 497 |
| 1500 (first run, replaced) | PASS | 802.4 | 14.8 | 123.6 | 165.4 | 0.00 | 7.8 / 104.0 | 0 / 92.1 | 6.2 / 19.0 | 92.5 (43.9 / 42.0) | 1.15 | 484 |

**Capacity: 1400 VUs at 645.1 req/s.** First fail: 1500 VUs.

## Profile at 1000 VUs (not an official run)
`scripts/profile.sh 1000` on this configuration: `perf record` system-wide for 40 s of the hold phase plus V8's
`--cpu-prof`. Text reports in `profiles/2026-10-10-node-express-v05-1000vus/`. Profilers add ≈ 4 % overhead
(529 req/s here vs. 534 in the official run).

Where the single vCPU goes (perf, share of all CPU time):

| Who | Share | Of which |
|---|---|---|
| Node main thread | 44 % | JS/V8 33 % (node binary 25 + JIT code 8), kernel 8 % (sockets, TCP, virtio network), libc 2 % |
| Postgres | 35 % | postgres binary 23 %, kernel 6.5 %, libc 5.6 % |
| Idle | 14 % | |
| Profiler threads, htop | ≈ 5 % | |

Inside Node's JavaScript (V8 profile, excluding time attributed to `writev`, which is mostly the thread being
preempted by Postgres right after it sends a query): Node core HTTP/net/streams ≈ 34 %, Express + router ≈ 24 %,
`pg` driver ≈ 19 % (result parsing, `parseDate`, query config cloning), JSON serialisation (`res.json`) ≈ 10 %,
ETag (sha1 of every body) ≈ 5 %, app code ≈ 6 %, GC ≈ 4 %.

Inside Postgres: the hottest single spot (3.7 % of all CPU, ≈ 10 % of Postgres) is a libc memory routine called from
`ExecInitMemoize`. The feed queries join `posts` → `users` with a Nested Loop that the planner wraps in a Memoize
cache keyed on `user_id`. With 20 rows and almost no repeated authors it never hits (`Hits: 0 Misses: 20`), but
it is set up on every execution. In pgbench on the droplet, the global + user feed queries run **25–35 % faster with
`enable_memoize = off`** (0.19–0.21 ms vs. 0.24–0.31 ms per pair).

## Observations
- `conn` (pool wait) is still 92–95 % of server time at the saturated levels; `db` p95 is 29–30 ms, the lowest of
  any tag at saturation.
- At 1000 VUs (not saturated) the CPU cost per request is 1.67 ms vs. 1.57 ms for v02. This contradicts the lower
  Postgres share, so host speed differed between the two runs; v05 ran before the host-speed probe existed.
- Time outside the handler (client − server p50) is 21–23 ms at saturation, as in v04.
- Someone ran `htop` on the droplet during the profiling run (1.3 % CPU). Interactive tools on the droplet during
  official runs take CPU from the app; avoid them.

## Next idea
`node-express-v06-no-memoize` (parent v05): `enable_memoize = off` for the app's database role, the only change.
It removes the per-execution Memoize setup in the feed queries (≈ 10 % of Postgres CPU in the profile). Compare at
1000 VUs (CPU per request, now with the host-speed probe) plus edge levels.
