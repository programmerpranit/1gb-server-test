# node-express-v06-feed-cache-1s

## Summary
**Capacity: 3000 VUs at 1541 req/s (92,462 req/min)**, steady p50 29 ms / p95 573 ms / p99 855 ms, 0 % errors.
The first failing level is **3200 VUs**: 1604 req/s, p99 1641 ms (limit 1000), still 0 % errors. Every level from
1000 to 3000 VUs passed. **2.1× v05's capacity in VUs (1400) and 2.4× in req/s (645)**, the biggest step since the
pool (v02). Labelled trade-off: the global feed can be up to 1 s stale.

- **The cache takes almost all feed queries off Postgres.** `GET /posts` is ≈ 47 % of requests (first page ≈ 36 %,
  second page ≈ 11 %); the first page is the same URL for every VU, and while it is cached its `next_before` is too,
  so the second page is a shared key as well. The app log shows **99.0–99.6 % hits** with 2 live keys; misses are
  ≈ 25 per 10 s (one per key per second, plus a few rare keys).
- **CPU per request fell ≈ 40 %.** At 1000 VUs: 0.97 ms vs. 1.67 ms for v05, total CPU 53 % vs. 89 %, Postgres
  12 % vs. 37 %, Node 33 % vs. 44 %. Host-speed probe 89 / 88 ms (normal). Cached responses skip the pool, the query,
  the `pg` row parsing and `JSON.stringify`; server time for a cached `GET /posts` is p95 0.3 ms.
- **The ceiling is still the CPU, and Node is now the larger share.** At 3000–3200 VUs the vCPU is 98–99 % busy
  (Node ≈ 60 %, Postgres ≈ 30 %), steal ≤ 0.4 %. Past ≈ 2500 VUs latency is again pool wait (`conn` p95 452 ms at 3000,
  482 ms at 3200) while query time stays at p95 ≈ 19 ms, the same overload pattern as v02–v05. 0 % errors at every
  level.
- **Memory is not a constraint.** Peak 548 MB used (3200 VUs: 3200 open sockets), Node ≤ 161 MB PSS, Postgres
  ≤ 131 MB, no swap; ≥ 400 MB still available.
- **The runs are clean** apart from short load-generator spikes: no CPU dips during any saturated hold phase,
  `app_log_tail.txt` has no errors, and the load generator averaged 18–40 % CPU. From 2000 VUs it peaked at
  96–98 % in single samples (8 samples > 70 % at 3000 and at 3200). 3000 passed with the same spikes, so they do
  not explain the 3200 failure, but they may add to the tail at the top levels.
- **Next:** v07 = the same cache with a 5 s TTL (user's plan). Since the hit rate is already 99.6 %, 5 s can only
  remove the ≈ 2 refresh queries per second and the stalls they cause (see Observations), so expect a small change.
  After that, Node is ≈ 2/3 of the CPU: Fastify instead of Express is the most promising next lever.

## What changed vs. the previous tag
Parent: `node-express-v05-prepared`. One change: **`GET /posts` (global feed, all pages) is cached in the Node
process for 1 s.** Key `limit:before` (validated values), value = the serialized JSON body, sent with
`res.type('json').send(...)` (same `Content-Type: application/json; charset=utf-8` and ETag as `res.json`). The TTL
counts from the moment the query starts. Concurrent misses for one key share one query (single-flight: the cache
holds the pending promise); a failed query is removed from the cache so the next request retries. Expired entries are
swept every 10 s, when the app also logs `feed cache: hit=… miss=… keys=…`. No invalidation on writes: a new post or a
new like/comment count shows in the global feed after at most 1 s (verified on the droplet). The other endpoints are
unchanged (`/posts/:id`, `/users/:id/posts` and `/me/posts` use random ids or are per user, so a cache would rarely
hit). App code from commit `887f64c`.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM (app code from commit `887f64c`)
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: `pg.Pool` defaults, max 10
- Queries: prepared statements (named queries)
- Writes: single statement (CTE), no explicit transactions
- **Cache: in-process, `GET /posts` only, all pages, key limit + before, TTL 1 s, single-flight, no invalidation**
- Server timing: `Server-Timing: conn, db, app, total` on every response (cache hit: conn 0, db 0)
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: DigitalOcean droplet in blr1, 4 vCPU / 8 GB shared (`do-blr1-loadgen-4vcpu-8gb`, a new droplet
  this session, private IP 10.122.0.4), k6 v2.3.0, traffic to the target's private IP 10.122.0.2

## Results
Levels chosen by the user: 1000, 1500, 2000, 2500, then 3000, then 3200.

| VUs | Result | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | Server p50 / p95 | conn p50 / p95 | db p50 / p95 | CPU % (app / PG) | CPU ms/req | Probe before / after ms | Used MB | Feed hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | PASS | 543.0 | 2.0 | 8.4 | 24.0 | 0.00 | 0.7 / 4.3 | 0 / 0.1 | 0.5 / 4.1 | 52.8 (33.4 / 12.3) | 0.97 | 89 / 88 | 472 | 99.0 % |
| 1500 | PASS | 810.1 | 3.2 | 32.8 | 62.3 | 0.00 | 0.8 / 13.2 | 0 / 0.1 | 0.6 / 10.6 | 72.5 (45.6 / 18.9) | 0.90 | 81 / 83 | 497 | 99.3 % |
| 2000 | PASS | 1079.1 | 3.7 | 48.5 | 95.9 | 0.00 | 0.8 / 25.5 | 0 / 7.9 | 0.6 / 11.4 | 78.7 (49.3 / 21.8) | 0.73 | 97 / 115 | 501 | 99.5 % |
| 2500 | PASS | 1324.8 | 12.4 | 192.3 | 435.9 | 0.00 | 1.4 / 165.6 | 0 / 126.6 | 0.9 / 18.3 | 91.9 (56.5 / 27.1) | 0.69 | 116 / 101 | 515 | 99.6 % |
| **3000** | **PASS** | **1541.0** | **29.4** | **573.0** | **854.6** | 0.00 | 7.6 / 551.7 | 0 / 451.8 | 1.9 / 19.0 | 98.0 (60.3 / 30.1) | 0.64 | 88 / 84 | 541 | 99.6 % |
| 3200 | FAIL (p99) | 1604.2 | 42.4 | 725.1 | 1640.9 | 0.00 | 19.2 / 709.8 | 0 / 481.8 | 2.5 / 18.4 | 98.7 (59.8 / 31.3) | 0.62 | 92 / 83 | 548 | 99.6 % |

**Capacity: 3000 VUs at 1541.0 req/s.** First fail: 3200 VUs. Same levels as v05 for comparison: 1000 VUs 534 →
543 req/s at 1.67 → 0.97 ms CPU/req; 1500 VUs FAIL 688 req/s → PASS 810 req/s (p99 1168 → 62 ms).

## Observations
- **CPU per request keeps falling as load rises** (0.97 → 0.62 ms from 1000 to 3200 VUs). The share of cached
  requests is constant, so this is per-request fixed cost being amortised: more requests per event-loop turn and
  per `epoll`/`writev`, and Postgres serving the remaining queries in batches. v05 showed the same trend, smaller.
- **Cached feed requests still see stalls at the top levels.** Server time for `GET /posts` is p95 0.3–1.2 ms up to
  2500 VUs but 204 ms at 3000 and 219 ms at 3200, although 99.6 % are hits. Likely cause: when a key expires, its
  refresh query waits in the same pool queue as everyone else (`conn` p95 ≈ 450 ms), and every feed request for that
  key arriving meanwhile waits on the same promise. Waiters record that wait as `app` time (they did not borrow a
  connection themselves), so the feed's `app` time at saturation is pool wait, not Express overhead. Serving the old
  body while one request refreshes (stale-while-revalidate) would remove these stalls.
- Edge case not reached here: the TTL counts from the query's start, so if a refresh waited > 1 s for the pool, the
  entry would expire before it resolves and single-flight would stop working. Pool wait stayed below ≈ 500 ms p95.
- Time outside the handler (client − server p50) grows from 1.3 ms at 1000 VUs to 22–23 ms at 3000–3200 VUs (event
  loop and accept queue under a busy CPU).
- Host speed varied: the probe read 116 ms before 2500 VUs and 115 ms after 2000 VUs (slow), 81–97 ms otherwise. 2500
  passed comfortably anyway; 3000 and 3200 ran at normal speed (88 / 92 ms before).
- ETag (sha1 of the body) is still computed for every cached response; disabling it is a separate tag.

## Next idea
`node-express-v07-feed-cache-5s` (parent v06): the same cache with TTL 5 s, the only change (user's plan). Compare at
1000 VUs (CPU per request) and at the edge (3000 / 3200 VUs). Expect a small difference: hits are already 99.6 %, so
5 s only removes ≈ 2 refresh queries per second and makes the refresh stalls 5× rarer.
