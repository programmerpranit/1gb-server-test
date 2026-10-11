# node-http-v04-bun-serve

## Summary
**Capacity: 4500 VUs at 2324 req/s (139,452 req/min)**, steady p50 15 ms / p95 319 ms / p99 912 ms, 0 % errors.
**First fail: 4700 VUs** (added after the first release), in two runs, both on a slow host: 2212 req/s (p95 934 /
p99 1093 ms, probe 104 ms) and, rerun, 2144 req/s (p95 1188 / p99 1547 ms, probe 148 ms); the 4500 pass ran at probe
82 ms. The CPU was at 100 % and the latency was pool wait in both, so the 4700 failures are server-side, but on a
normal-speed host 4700 might pass. **Best result of the project so far**: +7 % VUs over v02 (4200)
and +12 % req/s over v02's best (2078–2097 req/s at 4200–4500 VUs); v02 and v03 both failed 4500 VUs.

- **`Bun.serve` cuts the app's work per request by ≈ 25 %.** App : Postgres CPU ratio 0.91 (Bun 40.7 % / PG 44.6 %)
  vs. 1.22 in v03 (same `Bun.sql`, `node:http` on Bun's compatibility layer) and 1.30 in v02. CPU per request 0.40 ms
  vs. 0.48 ms (v02) at the same host speed (probe 82 vs. 83 ms before). Most of the app-side cost on Bun was the
  `node:http` compatibility layer, not the runtime.
- **Postgres is now the larger CPU user** (45 % vs. the app's 41 %). Further app-side savings matter less; the ≈ 53 %
  of requests that still run queries set the floor. Query time stays low (`db` p95 11 ms).
- **Not saturated yet:** CPU 94 % average with dips to 82–90 %; pool wait p95 194 ms (v02 at 4500: 861 ms).
- **Memory is the lowest of any configuration:** Bun PSS ≤ 59 MB (v02 113 MB, Node 147 MB), peak 464 MB used,
  ≥ 497 MB available, no swap.
- **The load generator is the limit for going further.** k6 averaged 58 % CPU (peaks 100 %, RSS 2.6 GB) and the time
  outside the app rose to p95 49 ms (18–28 ms in earlier 4500-VU runs). The next level (≈ 5000 VUs) needs an 8 vCPU
  load generator to give a trustworthy verdict.
- **Next (user's plan):** Node/Bun is saved here; move on to Python frameworks, then Go, then Rust, then C++, each
  with the same API, pool 10 and 1 s feed cache, and compare their edges with this result.

## What changed vs. the previous tag
Parent: `node-http-v03-bun-sql`. One change: **the HTTP server, `node:http` (Bun's Node compatibility layer) →
`Bun.serve`** (Bun's native server: `fetch(Request) → Response`). Same handlers, router, `Bun.sql` data access,
1 s feed cache and `Server-Timing` (now computed when the `Response` is created; Bun adds `Content-Length`). Request
helpers adapted to the Fetch API: `req.headers.get()`, body via `req.text()` (JSON only, 100 kB limit), the path
parsed from the absolute `req.url`. Bun.serve's keep-alive idle timeout is its default (10 s; node:http used 5 s);
k6 VUs send a request every 1–3 s, so connections never idle out in either. The parity check (39 requests on a fresh
DB) gave responses identical to v01–v03. App code from commit `d4b36f2`.

## Full configuration
- App: `apps/node-http` — **Bun.serve**, Bun.sql, plain SQL, no ORM, no framework (app code from commit `d4b36f2`)
- Runtime: Bun 1.4.2, `NODE_ENV=production`, no flags
- App processes/workers: 1 (systemd `bench-app`)
- DB connections: Bun.sql pool, max 10, one reserved connection per request
- Queries: prepared (Bun.sql default), explicit parameter casts
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
Levels chosen by the user: 4500 (first fail of v02 and v03), then 4700 twice (added after the first release; the
rerun replaces the first run in `vus-4700/`).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB | Feed hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **4500** | **PASS** | **2324.2** | **14.8** | **319.2** | **911.5** | 0.00 | 1.5 / 270.7 | 0 / 193.5 | 0.8 / 11.3 | 94.1 (40.7 / 44.6) | 0.40 | 82 / 96 | 464 | 99.7 % |
| 4700 | FAIL (p95, p99) | 2143.5 | 162.6 | 1188.2 | 1546.8 | 0.00 | 128.9 / 1157.9 | 0 / 1095.5 | 3.1 / 14.4 | 99.1 (43.6 / 46.1) | 0.46 | 148 / 95 | 461 | 99.7 % |

**Capacity: 4500 VUs at 2324.2 req/s.** First fail: 4700 VUs (slow host; see below). At 4500 VUs: v02 FAIL 2097 req/s (p99 1045 ms),
v03 FAIL 1955 req/s (p99 1547 ms, slow host).

## Observations
- p99 912 ms leaves 9 % headroom; p50 15 ms and p95 319 ms show the server mostly keeps up, and the tail comes from
  short CPU-saturated stretches (100 % for up to ≈ 6 s at a time).
- Time outside the app (client − server) p50 13 ms / p95 49 ms: the p95 is the highest so far and coincides with the
  load generator's CPU peaks, so part of the tail is on the client side.
- Feed-cache hit rate 99.7 %; `app_log_tail.txt` has no errors.
- 4700 VUs, first run (replaced): FAIL, 2211.7 req/s, p50 156 / p95 934 / p99 1093 ms, CPU 98.5 % (Bun 43.1 / PG 45.9),
  0.45 ms CPU/req, probe 104.5 / 83.0 ms, load generator 53 % average. Rerun (kept): probe 148 ms before, the slowest
  host of the session. Both runs: CPU pinned, `conn` p95 880–1096 ms, time outside the app p95 19–30 ms (not k6).

## Next idea
Node/Bun is saved here (user's decision). Next phase: Python frameworks (Phase 3: FastAPI + uvicorn + asyncpg first),
then Go, Rust and C++. Before any stack is pushed beyond ≈ 4500 VUs, recreate the load generator with 8 vCPU (new
`LOADGEN_LABEL`) and rerun this configuration at its edge for comparability.
