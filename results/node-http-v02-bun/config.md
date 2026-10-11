# node-http-v02-bun

## Summary
**Capacity: 4000 VUs at 2082 req/s (124,896 req/min)**, steady p50 14 ms / p95 436 ms / p99 823 ms, 0 % errors.
The first failing level is **4500 VUs**: 2097 req/s, p95 902 ms / p99 1045 ms (limits 800 / 1000), still 0 %
errors. **+25 % VUs and +24 % req/s over node-http v01 on Node** (3200 VUs / 1678 req/s), with the same code and
driver: only the runtime changed. Best result so far.

- **Bun does less work per request.** At 3500 VUs (Node's first fail, Bun's easy pass) the app : Postgres CPU ratio
  is 1.28 vs. 1.48 on Node (Bun 45 % / PG 35 % at 1855 req/s vs. Node 52 % / PG 35 % at 1779 req/s), i.e. ≈ 13 %
  less app CPU per query, measured independently of host speed. CPU per request 0.48 vs. 0.54 ms although the host
  was slower for Bun's run (probe 109 vs. 83 ms before).
- **The ceiling is ≈ 2100 req/s, and it is the CPU.** 4000 → 4500 VUs adds only 15 req/s (2082 → 2097). At 4500 VUs
  the vCPU is at 100 % for the whole hold phase (Bun 51 % / Postgres 40 %), steal 0.4 %. The latency is inside the
  server: server time p95 884 ms, almost all pool wait (`conn` p95 861 ms); query time p95 15 ms.
- **Postgres is now ≈ 44 % of the busy CPU.** Further savings on the app side shrink in value; the Postgres share
  (the ≈ 53 % of requests that still run queries) is the next floor.
- **Memory is lower than on Node.** Bun PSS ≤ 113 MB (Node ≤ 147 MB), peak 499 MB used, ≥ 462 MB available, no swap.
- **The load generator is near its limit but did not decide the verdicts.** It averaged 46–53 % CPU and spiked to
  ≈ 90–100 % every ≈ 6–7 s (k6 RSS up to 2.6 GB). Time outside the app stayed at p95 16–18 ms at every level, and the
  4500 failure is server-side (100 % CPU, latency inside the handler).
- **Next:** user's request — a larger `pg.Pool` on Bun at 4500 VUs (node-express v03 showed pool 20 was worse on
  Node: more concurrent queries only add contention on 1 vCPU; Bun may behave differently). Then `Bun.serve` or Bun's
  native Postgres client (`Bun.sql`), or other stacks (Go, Rust).

## What changed vs. the previous tag
Parent: `node-http-v01-express-v06-port`. One change: **the runtime, Node v24.21.0 → Bun 1.4.2.** `start.sh` runs
`bun src/server.js` instead of `node src/server.js`. Same source (`node:http` server, `pg` 8.23.1 pool max 10,
prepared statements, CTE writes, 1 s in-process feed cache), same `node_modules` (`npm ci`). Bun is installed by
`scripts/server/setup.sh` as a pinned release binary (`/usr/local/bin/bun`, bun-linux-x64; the droplet has AVX2).
The parity check (39 requests on a fresh DB) gave responses identical to v01 on Node; headers are the same
(`Connection: keep-alive`, `Keep-Alive: timeout=5`). App code from commit `f64fc95`.

## Full configuration
- App: `apps/node-http` — plain `node:http` API on Bun's Node compatibility layer, pg 8.23.1, plain SQL, no ORM
  (app code from commit `f64fc95`)
- Runtime: **Bun 1.4.2**, `NODE_ENV=production`, no flags
- App processes/workers: 1 (systemd `bench-app`)
- DB connections: `pg.Pool` defaults, max 10
- Queries: prepared statements (named queries)
- Writes: single statement (CTE), no explicit transactions
- Cache: in-process, `GET /posts` only, all pages, key limit + before, TTL 1 s, single-flight, no invalidation
  (labelled trade-off: global feed up to 1 s stale)
- Server timing: `Server-Timing: conn, db, app, total` on every response (cache hit: conn 0, db 0)
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (nginx installed but disabled)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2

## Results
Levels chosen by the user: 3500 (Node's first fail), then 4000, then 4500.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB | Feed hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3500 | PASS | 1854.7 | 5.8 | 166.1 | 424.6 | 0.00 | 0.8 / 149.4 | 0 / 101.7 | 0.6 / 12.3 | 89.0 (45.2 / 35.4) | 0.48 | 109 / 80 | 498 | 99.7 % |
| **4000** | **PASS** | **2081.6** | **14.2** | **436.2** | **823.3** | 0.00 | 1.9 / 420.7 | 0 / 367.7 | 0.8 / 12.8 | 93.6 (47.0 / 37.6) | 0.45 | 79 / 105 | 489 | 99.7 % |
| 4500 | FAIL (p95, p99) | 2097.4 | 247.4 | 901.9 | 1044.6 | 0.00 | 217.3 / 883.6 | 59.7 / 861.2 | 3.8 / 15.4 | 100.0 (51.4 / 39.7) | 0.48 | 83 / 127 | 499 | 99.7 % |

**Capacity: 4000 VUs at 2081.6 req/s.** First fail: 4500 VUs. Node v01 at 3500 VUs: FAIL, 1779 req/s, p50 30 /
p95 471 / p99 1175 ms, CPU 95 % (Node 52 / PG 35), 0.54 ms CPU/req.

## Observations
- At 3500 and 4000 VUs the CPU was not pinned (89 % and 94 % average with dips to ≈ 80 %): Bun kept up with the
  offered load. At 4500 it was at 100 % throughout, and p50 jumped from 14 to 247 ms: the queue builds as soon as the
  offered load (≈ 2300 req/s) passes the ≈ 2100 req/s ceiling.
- The 4000-VU pass ran on a fast host (probe 79 ms before) and the host slowed during it (105 ms after); p99 823 ms
  leaves 18 % headroom, so the pass is not marginal, but a slower host could move the edge by one step.
- Time outside the handler (client − server) is small at every level (p50 5–30 ms, p95 16–18 ms): Bun's event loop
  and the load generator add little.
- `app_log_tail.txt` has no errors; feed-cache misses ≈ 25 per 10 s as on Node.

## Next idea
`node-http-v03-pool-20` (parent v02): `pg.Pool` max 10 → 20, the only change, tested at 4500 VUs (user's request).
On Node (node-express v03) pool 20 doubled query time and lowered capacity; check whether Bun's lower app overhead
changes that. Further: Bun's native Postgres client (`Bun.sql`) or `Bun.serve`, then Go / Rust.
