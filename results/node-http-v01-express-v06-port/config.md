# node-http-v01-express-v06-port

## Summary
**Capacity: 3200 VUs at 1678 req/s (100,656 req/min)**, steady p50 11 ms / p95 392 ms / p99 835 ms, 0 % errors.
The first failing level is **3500 VUs**: 1779 req/s, p99 1175 ms (limit 1000), p50 30 ms / p95 471 ms, still
0 % errors. Express v06 failed 3200 VUs (p99 1641 ms) and passed 3000, so dropping the framework moves the edge by
one step: **+7 % VUs, +9 % req/s** vs. node-express v06 (3000 VUs / 1541 req/s). The gain is real but modest, and
part of the req/s difference is host speed.

- **Less Node work per request.** At 3200 VUs Node used 51 % of the CPU and Postgres 33 % (Express v06: 60 % / 31 %).
  The Node : Postgres ratio fell from 1.93 to 1.55. Postgres runs the same queries in both, so the ratio does not
  depend on host speed: Node does ≈ 20 % less work per request without Express (router, middleware, `res.json`,
  ETag sha1).
- **Host-speed caveat.** The probe read 81 ms before the 3200-VU run vs. 92 ms before Express's (≈ 12 % faster
  host). CPU per request was 0.55 vs. 0.62 ms (−10 %), which is about the host difference, so CPU per request alone
  does not prove a gain; the CPU split above does.
- **The ceiling is still the CPU.** At 3500 VUs the vCPU is 95 % busy on average and at 100 % for long stretches
  (Node 52 % / Postgres 35 %), steal 0.9 %. Latency past the edge is pool wait again (`conn` p95 360 ms, query time
  p95 16 ms). Postgres is now ≈ 40 % of the busy CPU, so further app-side savings pay off less and less.
- **Memory is not a constraint.** Peak 537 MB used, Node ≤ 147 MB PSS, Postgres ≤ 133 MB, no swap, ≥ 424 MB available.
- **The load generator is close to its limit.** It averaged 48 % CPU at both levels, but spiked to 73–90 % about every
  6 s (peak 99–100 %). The server's CPU dips do not line up with those spikes, so k6 did not cause the 3500 failure,
  but levels above ≈ 3500 VUs need a bigger load generator to be trustworthy.
- **Next:** the remaining big levers are a faster runtime / HTTP server (Bun, uWebSockets.js) and other stacks (Go,
  Rust). Postgres's ≈ 35 % share is the floor no Node change can remove; caching more of the reads, or a stack that
  spends less CPU per query in the driver, attacks it.

## What changed vs. the previous tag
New stack `apps/node-http/`. Parent: **`node-express-v06-feed-cache-1s`** (different stack). One change: **Express
removed** — the same app on plain `node:http`. Everything else is a 1:1 port of node-express v06: `pg.Pool` defaults
(max 10), prepared statements (named queries), single-statement CTE writes, the 1 s in-process cache of `GET /posts`
(same code), `Server-Timing` on every response. Done by hand instead of by Express: a small router (method + path
segments, trailing slash ignored), JSON body parsing (JSON content types only, 100 kB limit, like `express.json`),
JSON responses with `Content-Type: application/json; charset=utf-8` and `Content-Length`. Not carried over (not part
of the contract): the `ETag` and `X-Powered-By` headers. A parity check on a fresh DB (39 requests: every endpoint,
400 / 401 / 404, invalid JSON, idempotent like/unlike, FK errors) gave identical status codes, bodies and content types
for both apps. App code from commit `656bdc8`.

## Full configuration
- App: `apps/node-http` — plain `node:http`, pg 8.23.1, plain SQL, no ORM, no framework (app code from commit `656bdc8`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: `pg.Pool` defaults, max 10
- Queries: prepared statements (named queries)
- Writes: single statement (CTE), no explicit transactions
- Cache: in-process, `GET /posts` only, all pages, key limit + before, TTL 1 s, single-flight, no invalidation
  (labelled trade-off: global feed up to 1 s stale)
- Server timing: `Server-Timing: conn, db, app, total` on every response (cache hit: conn 0, db 0)
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (nginx installed on the droplet but disabled)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`), k6 v2.3.0,
  traffic to the target's private IP 10.122.0.2

## Results
Levels chosen by the user: 3200 (Express v06's first fail), then 3500.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB | Feed hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **3200** | **PASS** | **1677.6** | **10.9** | **392.4** | **835.3** | 0.00 | 1.6 / 361.6 | 0 / 262.6 | 0.8 / 14.7 | 92.4 (51.0 / 32.9) | 0.55 | 81 / 91 | 523 | 99.7 % |
| 3500 | FAIL (p99) | 1778.5 | 29.5 | 470.8 | 1175.4 | 0.00 | 7.0 / 428.4 | 0 / 359.6 | 1.4 / 16.2 | 95.4 (52.0 / 35.1) | 0.54 | 83 / 98 | 537 | 99.7 % |

**Capacity: 3200 VUs at 1677.6 req/s.** First fail: 3500 VUs. Express v06 at 3200 VUs: FAIL, 1604 req/s, p50 42 /
p95 725 / p99 1641 ms, CPU 98.7 % (Node 60 / PG 31), 0.62 ms CPU/req, probe 92 / 83 ms.

## Observations
- At 3200 VUs the CPU was not pinned (92 % average, dips to 82–89 %): the server kept up with the offered load
  (≈ 1680 req/s from 3200 VUs). At 3500 VUs it was at 100 % for long stretches, so the edge lies between the two.
- The p99 failure at 3500 VUs is queueing: p50 stays at 30 ms and p95 at 471 ms, only the tail crosses 1 s.
- `app` time p95 is 3.4 ms at 3200 VUs vs. 120 ms for Express at the same level. Most of that difference is not
  framework cost: `app` also holds the wait of requests sharing a feed-cache refresh (single-flight), which follows
  pool wait (`conn` p95 263 vs. 482 ms). At 3500 VUs, with pool wait at 360 ms, `app` p95 is 127 ms again.
- Time outside the handler (client − server p50) is 9 ms at 3200 VUs and 22 ms at 3500 VUs.
- The host slowed during the 3500-VU run (probe 83 → 98 ms); the verdict is clear enough (p99 17 % over) not to need
  a rerun for the capacity number.
- `app_log_tail.txt` has no errors; feed-cache misses ≈ 25 per 10 s, as in node-express v06.
- Not released (tested this session on node-express, parent v06): feed-cache TTL 5 s (3200 VUs: FAIL, 1487 req/s,
  no gain over 1 s), nginx as plain reverse proxy (3000 VUs: FAIL, 1103 req/s, nginx 15 % CPU) and nginx
  `proxy_cache` for the feed instead of the app cache (3000 VUs: FAIL, 1473 req/s, nginx 17 % CPU). On 1 vCPU a proxy
  costs about as much CPU as it saves.

## Next idea
A faster runtime / HTTP layer for the same code: **Bun** (`Bun.serve` or `node:http` on Bun) as `node-http`'s next
tag, or uWebSockets.js. Before pushing past ≈ 3500 VUs, recreate the load generator with 8 vCPU (new
`LOADGEN_LABEL`) and rerun the current best at its edge for comparability. Then other stacks (Go, Rust) with the same
1 s feed cache.
