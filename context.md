# Session context

Handoff notes between working sessions: where things stand, what is decided, what is open. Read this first; update
it at the end of every session. Rules, protocol and the full plan stay in [CLAUDE.md](CLAUDE.md); numbers and
per-tag analysis in [README.md](README.md) and `results/<tag>/config.md`.

_Last updated: 2026-10-11, session 2 (v06 released)._

## Infrastructure state

| Machine | State | Notes |
|---|---|---|
| Target droplet `1gb-test` (blr1, $6, 1 vCPU / 1 GB) | **Running, keep it** | Public 143.110.255.234, private 10.122.0.2. Holds the `bench_seed` template DB and the installed app. |
| Load generator (blr1, 4 vCPU / 8 GB shared, `do-blr1-loadgen-4vcpu-8gb`) | **Running (session 2)**, destroy at end of session | Public 168.144.21.215, private 10.122.0.4. In `.env` as `LOADGEN_HOST`. (A 2 vCPU / 4 GB droplet, 64.227.156.31, was created by mistake and replaced.) |

- App deployed on the target: **node-express v06** (commit `887f64c`: v05 + 1 s in-process cache of `GET /posts`).
  `bench-app` service active.
- Postgres 16.15 at defaults; no server-side setting changed (no `enable_memoize` change yet).
- `/tmp/bench-prof/` on the target held the raw profiling data (perf.data, .cpuprofile); safe to delete.

### Start of next session
1. User creates a new load-generator droplet (blr1, same VPC, same SSH key `~/.ssh/do`, 4 vCPU / 8 GB shared) and
   gives the IP. Put it in `.env` as `LOADGEN_HOST` (keep `LOADGEN_LABEL=do-blr1-loadgen-4vcpu-8gb` if same size,
   otherwise a new label — rows are only comparable with the same label).
2. `scripts/provision_loadgen.sh` (≈ 1 min: pinned k6 v2.3.0, limits, sysctls; checks it reaches the target).
3. Optional live dashboard: `scripts/dashboard.sh` (tunnel to http://localhost:5665; refresh when a level starts).
4. Check the deployed app matches the tag about to be tested (`scripts/deploy.sh node-express` after committing).

## Results so far (protocol v2, all from the blr1 load generator)

| Tag | Change | Capacity | req/s at capacity | First fail | Verdict |
|---|---|---|---|---|---|
| node-express-v01-baseline | no pool, new connection per request | 100 VUs (marginal) | 46.7 | 110 | connect + auth ≈ 80 % of server time |
| node-express-v02-pool | `pg.Pool` max 10 | 1350 | 619 | 1400 | 13× v01; CPU-bound, Node ≈ 42 % / PG ≈ 50 % |
| node-express-v03-pool-20 | pool max 20 | 1200 (marginal) | 574 | 1300 | worse: 2× query time from contention; keep pool 10 |
| node-express-v04-cte-writes | single-statement writes (parent v02) | 1400 rule / ≈ 1300–1400 real | 540–660 | 1500 | no measurable gain; 1300/1350 failed; kept as parent |
| node-express-v05-prepared | prepared statements (parent v04) | 1400 | 645 | 1500 | PG share ≈ 43.5 %; likely 5–10 % gain, within noise |
| node-express-v06-feed-cache-1s | 1 s in-process cache of `GET /posts`, all pages (parent v05) | 3000 | 1541 | 3200 | 2.4× v05; 99.6 % hits; Node ≈ 60 % / PG ≈ 30 %; trade-off: feed ≤ 1 s stale |

All six are released on GitHub (build, results, `report-<tag>.html`). Best configuration: **v06** (cached; best
uncached: v05).

## Key learnings (beyond CLAUDE.md)
- **The ceiling is CPU** (≈ 600–690 req/s on this vCPU for node-express). Past it, latency is pool wait (`conn`),
  never errors (0 % errors in every run).
- **Host speed varies ±20–30 % without showing as steal.** v05's first 1500-VU run did 802 req/s at 1.15 ms CPU per
  request vs. 1.45–1.67 ms in every other run. Single saturated runs swing ±60 req/s. Since commit `88ba49d` every run
  records `cpu_probe_before_ms` / `cpu_probe_after_ms` (fixed workload; idle values seen 67–98 ms, median ≈ 76–85)
  and `cpu_ms_per_req_steady`. Compare tags at an unsaturated level (1000 VUs) plus edge levels.
- **Profile of v05 at 1000 VUs** (`profiles/2026-10-10-node-express-v05-1000vus/`): Node 44 % (8 points kernel
  networking), Postgres 35 %, idle 14 %. Node JS time: core HTTP ≈ 34 %, Express + router ≈ 24 %, pg driver ≈ 19 %,
  JSON ≈ 10 %, ETag ≈ 5 %, GC ≈ 4 %. Postgres: Memoize setup in the feed queries ≈ 10 % of Postgres CPU, never hits;
  pgbench shows feed queries 25–35 % faster with `enable_memoize = off`.
- V8's `--cpu-prof` attributes preemption time to `writev` (≈ 50 %); use perf for the real CPU split.
- No hardware perf counters on the droplet (`<not supported>` for instructions/cycles); perf samples cpu-clock.

## Open decisions / next steps
1. **v07 `node-express-v07-feed-cache-5s`** (parent v06): only `FEED_CACHE_TTL_MS` 1000 → 5000 in
   `apps/node-express/src/server.js` (+ header comment "1 s" and `bench.json` change). User's plan. VU levels not
   chosen yet; suggest the v06 levels (1000 … 3000, 3200) for a direct comparison.
2. Then: Fastify (Node is ≈ 2/3 of CPU now); stale-while-revalidate for the feed cache (cached feed requests wait
   ≈ 200 ms p95 at 3000 VUs behind the refresh query's pool wait); ETag off; `enable_memoize = off` (less valuable
   now: feed queries are mostly cached); then Bun / cluster; then other stacks (Phase 3+).
3. From 2000 VUs the load generator peaks at ≈ 97 % CPU in single samples (average ≤ 40 %). If v07+ goes past
   ≈ 3500 VUs, consider a bigger load generator (would need a new `LOADGEN_LABEL`).
4. Maybe later: repeat runs per level (needs run-dir naming like `vus-1500-r2`; today a rerun overwrites the level).

## Working agreements with the user
- **The user picks every VU level.** Claude may suggest, never runs levels on its own.
- After every test: write `results/<tag>/config.md` (Summary, What changed, Results, Observations, Next idea), a README
  Findings entry and README **Next steps**, then `scripts/release.sh <tag>` (README "Analysis per configuration" is
  generated from config.md). Release only when the user says so.
- **Never publish claude.ai Artifacts**; the GitHub release (with `report-<tag>.html`) is enough.
- Flag marginal passes (within ≈ 5 % of a limit), CPU dips (client stalls) and host-speed outliers before trusting
  a verdict; propose a rerun when it matters.
- Commits end with the Co-Authored-By trailer (+ Claude-Session when a session URL is known); push to `main` (private repo
  `programmerpranit/1gb-server-test`).

## Tooling fixes made this session (all committed)
- `deploy.sh` health check runs on the droplet (the Mac cannot reach the private `TARGET_HOST`).
- `run_test.sh` only reuses a *listening* dashboard tunnel (leftover browser sockets fooled the old check).
- `scripts/readme_analysis.py` (README per-tag analysis), `scripts/server/cpu_probe.sh`, `scripts/profile.sh`,
  `scripts/cpuprofile_summary.py`; `summarize.py` adds probe + CPU-per-request columns to `results.csv`.
