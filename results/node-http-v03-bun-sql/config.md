# node-http-v03-bun-sql

## Summary
**Only one level tested: 4500 VUs FAIL** — 1955 req/s, steady p50 417 ms / p95 1088 ms / p99 1547 ms (limits 800 /
1000), 0 % errors. Capacity by the rule is therefore "< 4500" (not measured below); the parent v02 (`pg` on Bun)
passed 4200 VUs and also failed 4500. **No measurable gain from Bun's native Postgres client.** Kept as the base for
`Bun.serve` (v04) by the user's decision.

- **At most ≈ 5 % less app work per query.** The app : Postgres CPU ratio at 4500 VUs is 1.22 (Bun 49.9 % / PG
  40.8 %) vs. 1.29 for v02 (51.4 % / 39.7 %). This ratio does not depend on host speed. Query time is unchanged
  (`db` p95 17 vs. 15 ms): the native client does not make Postgres faster, only the client side slightly cheaper.
- **Throughput at the edge is confounded by host speed.** Both runs had the CPU at 100 % for the whole hold phase, so
  req/s follows the host: v03 started on a ≈ 30 % slower host (probe 108 ms before vs. 83 ms for v02). 1955 vs.
  2097 req/s (−7 %) and 0.51 vs. 0.48 ms CPU per request are within that difference.
- **Bottleneck unchanged:** CPU-bound, Bun ≈ 50 % / Postgres ≈ 41 %, latency past the edge is pool wait (`conn` p95
  999 ms). Memory 500 MB used, Bun PSS 109 MB, Postgres 132 MB, no swap. Load generator 48 % average, peaks 100 %;
  time outside the app p95 28 ms.
- **Next:** v04 = `Bun.serve` instead of `node:http` on top of this (user's plan).

## What changed vs. the previous tag
Parent: `node-http-v02-bun`. One change: **the Postgres client, node-postgres (`pg` 8.23.1) → Bun.sql** (Bun 1.4.2's
built-in client, `new SQL({ url, max: 10 })`). Every request still reserves one connection (`sql.reserve()`) for all
its queries, timed as `conn`; queries are tagged templates (prepared and cached per connection by Bun.sql), timed as
`db`. Adjustments needed for identical responses: every parameter has an explicit cast (`::bigint`, `::int`,
`::text`, `::boolean`) so numbers never travel as float8; Bun.sql returns int8 columns as strings, so `id`, `user_id`
and `post_id` are converted with `Number()` in the query wrapper (node-postgres did the same with a type parser);
the SQLSTATE of a server error is in `err.errno` (`err.code` is Bun's own code). The `pg` dependency is removed. The
parity check (39 requests on a fresh DB) gave responses identical to v01/v02. App code from commit `ed0c70a`.

## Full configuration
- App: `apps/node-http` — plain `node:http` API on Bun's Node compatibility layer, **Bun.sql**, plain SQL, no ORM
  (app code from commit `ed0c70a`)
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
Level chosen by the user: 4500 (v02's first fail).

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4500 | FAIL (p95, p99) | 1954.7 | 416.9 | 1087.9 | 1546.8 | 0.00 | 397.7 / 1060.0 | 95.5 / 998.8 | 4.0 / 17.0 | 99.8 (49.9 / 40.8) | 0.51 | 108 / 92 | 500 |

**Capacity: not established (< 4500 VUs).** Parent v02 at 4500 VUs: FAIL, 2097 req/s, p50 247 / p95 902 / p99
1045 ms, CPU 100 % (Bun 51.4 / PG 39.7), 0.48 ms CPU/req, probe 83 / 127 ms.

## Observations
- The CPU was at 97–100 % for the entire hold phase; no client stalls.
- Feed-cache hit rate 99.7 %, as before; `app_log_tail.txt` has no errors.
- A repeat run on a normal-speed host was offered and not chosen: the host-independent CPU split already bounds the
  gain at ≈ 5 %.

## Next idea
`node-http-v04-bun-serve` (parent v03): `Bun.serve` (Bun's native HTTP server, `fetch(Request) → Response`) instead
of `node:http` on Bun's compatibility layer, the only change. Test at 4500 VUs.
