# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

**Start every session by reading [context.md](context.md)** (infrastructure state, results so far, open decisions,
working agreements). **Update context.md at the end of every session** (and after any change in infrastructure,
best configuration or open decisions), so the next session can resume without the chat history.

## Goal

Measure how far a **$6/month DigitalOcean droplet** can go when serving the same small social-feed API written in
different languages and frameworks (Node.js, Python, Go, Rust, ...), with Postgres running **on the same droplet**.
Start from a plain baseline, then optimise one variable at a time and record every result.

Every configuration gets:
1. the same 2-minute stress test (`loadtest/stress.js`),
2. its results stored under `results/<tag>/` and summarised in `README.md`,
3. a git tag + GitHub release holding the code ("build") and raw results.

## The server under test

| | |
|---|---|
| Provider / plan | DigitalOcean Basic droplet, $6/month |
| CPU | 1 vCPU (shared — watch **steal %**) |
| RAM | 1 GB (no swap by default) |
| Disk | 25 GB SSD |
| Transfer | 1000 GB/month |
| OS | Ubuntu 24.04 LTS (assumed by `scripts/server/setup.sh`) |
| Runs | Postgres (localhost only) + the app under test as systemd unit `bench-app` |

## Fairness rules

These keep results comparable across stacks. Do not break them without recording it.

1. **One variable per tag.** Each new tag changes exactly one thing vs. its parent tag and says what in `config.md`.
2. **Same protocol for every stack.** `loadtest/stress.js`, `db/schema.sql` and the API contract below are frozen
   (currently "protocol v2"). If one must change, bump the protocol version in this file and README, and re-run the baselines.
3. **All official runs come from the load-generator droplet** (`LOADGEN_HOST`): a separate DigitalOcean droplet in
   the **same region (blr1) and VPC** as the target, sending traffic to the target's **private IP** (`TARGET_HOST`,
   10.122.0.2). Never run k6 on the droplet under test. The MacBook is no longer an official load source: home Wi-Fi
   added ~40 ms RTT and stalls. `LOADGEN_LABEL` (e.g. `do-blr1-loadgen-2vcpu`) is recorded in every row; only compare
   rows with the same label. The load generator is stateless and destroyed after each session (see Phase 0).
4. **Identical start state.** Before every run: fresh DB cloned from the `bench_seed` template, Postgres restarted, OS
   page cache dropped, app restarted (`scripts/server/prepare_run.sh`).
5. **Configuration is data.** Swap on/off, Postgres settings, runtime flags (`NODE_ENV`, heap size), pool sizes,
   worker counts, reverse proxy — all are recorded in `results/<tag>/config.md`. Baseline = defaults, swap off.
6. **Commit the code before testing.** `run.json` stores the git SHA; `release.sh` refuses uncommitted app code.
7. **The load generator must not be the bottleneck.** `run_test.sh` raises `ulimit -n` (k6 needs ~1 socket per VU)
   and records it as `loadgen_nofile`. Watch the load generator's CPU too; a saturated k6 inflates latency.
8. **Auth is simulated** with an `X-User-Id` header (no passwords/JWT/bcrypt), so hashing does not dominate CPU.
   Deliberate simplification; real auth can be its own experiment later.

## Repository layout

```
CLAUDE.md                     this file: goals, rules, contract, plan
context.md                    session handoff: infra state, results so far, open decisions (read first)
README.md                     results comparison tables (auto-updated by run_test.sh)
Twitterdatainsheets.xlsx      seed dataset (source of truth)
.env.example                  copy to .env (git-ignored): server IP, DB password, load-gen label
db/schema.sql                 shared Postgres schema (all stacks)
loadtest/stress.js            k6 stress test (all stacks)
apps/<stack>/                 one implementation per stack, e.g. apps/node-express/   (not created yet)
  build.sh                    optional; runs on the server as user `bench` (npm ci, go build, cargo build ...)
  bench.json                  required; stack metadata for results.csv: language, runtime, framework, db, db_driver,
                              db_pool, workers, proxy, change (update it in the same commit as each config change)
  start.sh                    required; must `exec` the server process; reads $PORT and $DATABASE_URL
  nginx.conf                  optional; if present, nginx (full nginx.conf) serves :3000 and the app gets PORT=3001
                              (install_app.sh); server_metrics.csv then has proxy_cpu_pct / proxy_pss_mb
results/CONFIG_TEMPLATE.md    template for results/<tag>/config.md
results/results.csv           every run, one row per (tag, VUs), all data points (auto-updated)
results/<tag>/                one directory per configuration
  config.md                   what changed + full config + observations
  bench.json                  stack metadata as deployed
  capacity.json               capacity search result (highest passing VUs, first fail, levels tested)
  vus-<n>/                    one directory per VU level
    run.json                  tag, stack, VUs, timing, load-gen label, git SHA, k6 version
    server_env.txt            kernel, OS, node/postgres versions, swap, shared_buffers ...
    k6_start.json             exact k6 start time (aligns server samples with phases)
    k6_summary.json           full k6 summary (all metrics, percentiles, per-endpoint)
    k6_report.html            k6 web-dashboard export (timeline charts)
    k6_stdout.txt             k6 console summary
    server_metrics.csv        1 s samples: CPU, steal, per-unit CPU, PSS memory, swap, connections
    app_log_tail.txt          last app log lines (look for crashes / OOM)
    summary.json / .md        combined headline numbers
scripts/
  lib.sh                      shared helpers (loads .env, ssh wrappers)
  xlsx_to_csv.py              dataset -> data/*.csv + data/meta.json (stdlib only)
  provision.sh                one-time droplet setup (runs server/setup.sh)
  seed_db.sh                  upload CSVs + schema, build bench_seed template (runs server/seed.sh)
  deploy.sh <stack>           rsync apps/<stack>, build, install + restart bench-app
  run_test.sh <tag> <vus..>   run one configuration at the given VU levels (--search: ladder + bisection)
  summarize.py <run_dir>      k6 + server metrics -> pass/fail, summary, README row, results.csv row
  release.sh <tag>            commit results, git tag, GitHub release with build + results
  release.sh --update <tag>   after adding VU levels to a released tag: push results, refresh release assets/notes
  report_html.py <tag_dir>    results/<tag>/report.html: summary, levels table, charts (k6 2-s snapshots decoded
                              from k6_report.html, server + load-gen samples); run by release.sh, attached to the release
  profile.sh <vus> [label]    profiling run (NOT official): perf system-wide + V8 --cpu-prof -> profiles/<date>-<label>/
  cpuprofile_summary.py       V8 .cpuprofile -> self time by category / function (used by profile.sh)
  readme_analysis.py          copies every tag's What changed / Summary / Observations / Next idea from
                              results/<tag>/config.md into README "Analysis per configuration"; run by release.sh
  server/                     scripts executed ON the droplet via `ssh bash -s`
    setup.sh  seed.sh  reset_db.sh  install_app.sh  prepare_run.sh  collect_metrics.sh
    cpu_probe.sh              host-speed probe: fixed CPU workload timed before and after every run
profiles/                     text reports of profiling runs (perf by process/dso/symbol, V8 profile summary)
data/                         generated CSVs (git-ignored); data/meta.json is tracked (load test needs the counts)
```

## Dataset

`Twitterdatainsheets.xlsx` has three sheets. Headers have leading spaces (`" Lang"`) and are stripped.

| Sheet | Rows | Columns |
|---|---|---|
| Tweet | 100,000 | TweetID, Weekday, Hour, Day, Lang, IsReshare, Reach, RetweetCount, Likes, Klout, Sentiment, text, LocationID, UserID |
| Location | 6,289 | LocationID, Country, State, StateCode, City |
| User | 100,000 | UserID, Gender |

Data quality findings, handled by `scripts/xlsx_to_csv.py`:
- Every sheet ends with an all-`"NULL"` row → dropped. `"NULL"` cells become SQL NULL.
- User sheet has 740 duplicate UserIDs → de-duplicated (first wins), and one malformed ID (`_x001A_nknow531394`) → dropped.
- One tweet author (`tw-832531394`) is missing from the User sheet → stub user added.
- Tweet text contains newlines, quotes and HTML entities (`&amp;`) → kept as-is, CSV-quoted.
- Weekday/Hour/Day are local time without a year; the real UTC timestamp is decoded from the tweet ID
  (Twitter snowflake). Tweets span 2016-01-01 → 2016-04-02.

Resulting data (`data/meta.json`): **99,260 users** (of which **33,213 authors**), **100,000 posts**, 6,289 locations.

ID strategy: internal `bigint` IDs (fast joins/indexes, simple for the load test). Users are numbered authors-first
(`1..33213` all have posts), then the rest. Posts are numbered `1..100000` in time order, so `id DESC` is newest
first and keyset pagination works on the primary key. Original IDs are kept in `users.handle` and `posts.external_id`.
Seed `like_count` comes from the dataset's Likes column; the `likes` and `comments` tables start empty.

## Database

Schema: `db/schema.sql` — `users`, `locations`, `posts`, `likes (post_id, user_id) PK`, `comments`.
Key indexes: partial `posts(id DESC) WHERE is_public` (global feed), `posts(user_id, id DESC)` (user feed),
`comments(post_id, id DESC)`.

`scripts/seed_db.sh` builds the database `bench_seed` once and marks it a template. Each run recreates the working
database `bench` with `CREATE DATABASE bench TEMPLATE bench_seed` (seconds, deterministic). The app always connects
to `bench` with role `bench` over `127.0.0.1:5432`.

## API contract (protocol v2)

Every implementation must match this exactly so `loadtest/stress.js` works unchanged.

General:
- Listens on `$PORT`; connects with `$DATABASE_URL`. Started by `start.sh`.
- JSON in/out. Acting user comes from header `X-User-Id: <users.id>`; missing/invalid where required → `401`.
- Pagination: `limit` (default 20, max 50) and `before` (post id, exclusive). Keyset only — no `OFFSET`.
  Response includes `next_before` = id of the last post returned, or `null` if fewer than `limit` rows.
- Validation error → `400 {"error": "..."}`. Unknown post → `404 {"error": "not found"}`.

Shapes:
```jsonc
// Post
{ "id": 123, "user_id": 45, "handle": "tw-40932430", "text": "...", "is_public": true,
  "like_count": 3, "comment_count": 1, "created_at": "2016-01-01T00:00:07.851Z" }
// Comment
{ "id": 9, "post_id": 123, "user_id": 45, "text": "...", "created_at": "..." }
```

| Method & path | Auth | Behaviour | Success |
|---|---|---|---|
| `GET /health` | – | `SELECT 1` against the DB | `200 {"status":"ok"}` |
| `GET /posts?limit&before` | – | Public posts, newest first (join users for `handle`) | `200 {"posts":[Post], "next_before"}` |
| `GET /posts/:id` | optional | Post + latest 20 comments. Private posts only visible to their owner, else 404 | `200 {"post":Post, "comments":[Comment]}` |
| `GET /users/:id/posts?limit&before` | – | That user's public posts, newest first (empty list if none) | `200 {"posts":[Post], "next_before"}` |
| `GET /me/posts?limit&before` | required | Caller's posts incl. private, newest first | `200 {"posts":[Post], "next_before"}` |
| `POST /posts` | required | Body `{"text": 1..1000 chars, "is_public"?: bool = true}` | `201 {"post":Post}` |
| `POST /posts/:id/like` | required | Idempotent; increments `like_count` only if newly liked | `200 {"liked":true, "like_count"}` |
| `DELETE /posts/:id/like` | required | Idempotent; decrements only if a like was removed | `200 {"liked":false, "like_count"}` |
| `POST /posts/:id/comments` | required | Body `{"text": 1..1000 chars}`; increments `comment_count` | `201 {"comment":Comment}` |

Writes that touch two tables (like + counter, comment + counter) run in one transaction.

**Server timing (required, protocol v2).** Every response, including errors, carries a `Server-Timing` header
measured inside the app:
```
Server-Timing: conn;dur=1.2, db;dur=3.4, app;dur=0.8, total;dur=5.4
```
- `total`: from the moment the app starts handling the request (first middleware) until the response is sent.
- `conn`: time to obtain a DB connection — connect + auth without a pool, waiting for a free connection with a pool.
- `db`: summed time spent executing queries (including BEGIN/COMMIT).
- `app`: `total - conn - db` (routing, validation, JSON serialisation, framework overhead).
All values are milliseconds with 0.1 ms precision. `/health` reports them too. k6 records them per endpoint and
phase, so client-observed latency can be split into server time vs. network/queueing outside the handler.

## Load test protocol (protocol v2)

Tool: [k6](https://k6.io) (`brew install k6` on macOS; on Ubuntu follow
<https://grafana.com/docs/k6/latest/set-up/install-k6/>), script `loadtest/stress.js`, driven by `scripts/run_test.sh`.

- **Shape:** `ramping-vus` — 0 → N VUs linearly over 60 s, then hold N for 60 s. 2 min total per run.
- **Virtual user:** picks a random user id once (`X-User-Id`), then loops: one weighted action, then 1–3 s think time.
- **Action mix:** global feed 40 % (30 % of those scroll a 2nd page), view post 15 %, user's posts 15 %, my posts 7 %,
  like 12 %, unlike 2 %, comment 4 %, create post 5 % (10 % of new posts private). ≈77 % reads / 23 % writes.
  Likes/comments mostly target posts the VU just saw in a feed (realistic hot rows).
- **Phases:** each request is tagged `phase=ramp|steady`; headline throughput and latency use the steady phase.
- **Error:** any non-2xx response or a request taking longer than 10 s (k6 timeout).
- **Pass criteria (per run):** steady-phase **p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms**, and whole-run
  **error rate < 1 %**. All four must hold. Configurable via `PASS_P50_MS`, `PASS_P95_MS`, `PASS_P99_MS`,
  `PASS_ERROR_PCT` in `.env` (changing them is a protocol change — note it).
- **VU levels are chosen by the user (manual mode, default).** `scripts/run_test.sh <tag> <vus...>` runs exactly
  those levels, each with a full reset, and does not stop on failures. **Claude must not pick or add VU levels on its
  own** — ask the user which levels to run (Claude may suggest some).
- **Capacity search (optional, `--search`):** climb the ladder `100 250 500 1000 2000` (`VU_LADDER`, override per run) until a level fails,
  then binary-search between the last passing level (or 0) and the first failing one, rounded to `SEARCH_STEP`
  (10) VUs, until the gap is ≤ 10. Example: 100 pass, 250 fail → 180 → 140 or 220 → ... Full reset between levels.
  A pass within ~5 % of a limit is "marginal" — call it out in the report summary.
- **Capacity:** the highest passing VU level run for the tag, with its steady req/s. This is the headline number
  (`results/<tag>/capacity.json`, README "Capacity per configuration").
- At ~2 s per iteration, N VUs produce roughly N/2 req/s offered load (a bit more with feed scrolling).

## Metrics recorded per run

From k6 (`k6_summary.json`): total requests, avg req/s, steady req/s and req/min, max VUs, error rate (overall and
steady), latency avg / p50 / p90 / p95 / p99 / max (overall, steady, per endpoint).

From the app's `Server-Timing` header (k6 Trends `server_total`, `server_conn`, `server_db`, `server_app`, per
endpoint and phase): p50 / p95 / p99 of time inside the app and how it splits. `k6 latency − server_total` is time
outside the handler: network, kernel/accept queues, event-loop wait, load generator.

From the server (`server_metrics.csv`, 1 s samples by `collect_metrics.sh`): CPU busy / user / sys / iowait /
**steal** %, app CPU % and Postgres CPU % (cgroup), memory used / available, swap used, app PSS MB, Postgres PSS MB,
established connections on the app port, load average.

Host speed: the shared vCPU's speed varies ±20–30 % without showing as steal. `cpu_probe.sh` times a fixed workload
(median of 15 × ≈ 80 ms) right before and after k6 (`cpu_probe_before_ms` / `cpu_probe_after_ms`, higher = slower
host), and `cpu_ms_per_req_steady` = steady CPU % × 10 / steady req/s. Compare CPU per request between tags only
with similar probe values.

`summarize.py` reduces both into `summary.json` / `summary.md`, judges pass/fail, and upserts the run into README's
"All runs" table and into **`results/results.csv`** — one row per (tag, VUs) with ~75 columns: run identity, verdict
and criteria, stack (language, runtime + version, framework, DB + version, driver, pool, workers, change — from
`apps/<stack>/bench.json`), server (plan, vCPU, RAM, OS, kernel, swap, Postgres settings), load generator,
throughput, errors, steady and whole-run latency percentiles, per-endpoint p95, and server resource peaks/averages.
After the search, `summarize.py --capacity` writes `capacity.json` and upserts README's "Capacity" table.

## Tags and releases

- Tag format: `<stack>-v<NN>-<slug>` where `<stack>` is the `apps/` directory name and `NN` counts per stack.
  Examples: `node-express-v01-baseline`, `node-express-v02-pool-20`, `go-nethttp-v01-baseline`.
- Parent of each tag is the previous tag of the same stack unless `config.md` says otherwise.
- `scripts/release.sh <tag>` commits `results/<tag>/` + README, creates the annotated tag, pushes, and creates a
  GitHub release with `build-<tag>.tgz` (app source + shared scripts at that tag) and `results-<tag>.tgz`.
- Remote: `github.com/programmerpranit/1gb-server-test` (private). Requires `gh auth login` on the machine releasing.

## Workflow for one configuration

```bash
# 1. change exactly one thing in apps/<stack>/ (or server config), commit it
scripts/deploy.sh <stack>
# 2. run the ladder (creates results/<tag>/config.md from the template on first run)
scripts/run_test.sh <stack>-vNN-<slug> 100 150 200   # VU levels chosen by the user
# 3. fill results/<tag>/config.md (what changed, observations, next idea)
# 4. update README headline row, then
scripts/release.sh <stack>-vNN-<slug>
```

Server-side config changes (Postgres settings, swap) are made over ssh, described in `config.md`, and reverted
before the next unrelated experiment unless they become the new baseline for that stack.

## Plan

### Phase 0 — Infrastructure
- [x] Dataset analysis and converter (`scripts/xlsx_to_csv.py`)
- [x] Shared schema, API contract, k6 test, metrics sampler, run/summarize/release scripts
- [x] Target droplet created in **blr1** (Ubuntu 24.04.5, kernel 6.8.0-142, 961 MB usable RAM, private IP
      10.122.0.2), `.env` filled. Scripts SSH as root with key auth using `SSH_KEY` from `.env` (`~/.ssh/do`).
      The target is kept running between sessions (it holds the `bench_seed` template and installed stacks).
- [x] GitHub repo created: `programmerpranit/1gb-server-test` (private)
- [x] Provisioned (Node v24.21.0, PostgreSQL 16.15) and seeded (`bench_seed` = 62 MB).
      Idle after `prepare_run.sh` with Postgres + node-express running: ~350 MB used, ~605 MB available
      (DigitalOcean agent + OS take ~300 MB before anything is installed). Idle PSS: node 62 MB, Postgres ~25 MB.
- [x] Tooling smoke-tested (endpoints via curl, k6, `prepare_run.sh`, `collect_metrics.sh`).
- Notes: macOS ships `openrsync` (no `--chmod`); the sampler is one long-lived python3 process because forking
  `awk`/`ss` every second cost ~10 % of the vCPU (now ~1–2 %).
- [x] **Load-generator droplet** (created by the user each session; IP goes into `LOADGEN_HOST`): blr1, same VPC
      (private 10.122.0.3, /20), Ubuntu 24.04, same SSH key, **4 vCPU / 8 GB shared (DO-Regular 2.0 GHz)**,
      label `do-blr1-loadgen-4vcpu-8gb`. Stateless — destroyed after each session. RTT to target ≈ 2 ms.
  - [x] `scripts/provision_loadgen.sh` (→ `server/loadgen_setup.sh`): pinned k6 v2.3.0 binary, nofile 1048576,
        port range / tw_reuse sysctls; idempotent, ~1 min.
  - [x] `run_test.sh` orchestrates from the Mac: copies `loadtest/stress.js` to `/opt/loadgen/runs/<tag>/vus-<n>/`,
        runs k6 there against `TARGET_HOST` (10.122.0.2), copies `k6_summary.json`, `k6_start.json`,
        `k6_report.html` back; `loadgen_metrics.csv` samples load-generator CPU and k6 RSS (summary warns > 70 %).
  - [x] **Live dashboard:** k6 web dashboard bound to the load generator's 127.0.0.1:5665 (no auth, never public),
        tunnelled to **http://localhost:5665** on the Mac (2 s refresh) — by `run_test.sh` for its duration, or
        persistently with `scripts/dashboard.sh` (run_test reuses it). It exists only while k6 runs — refresh the
        page when a VU level starts. k6 would not exit while a browser held the page open; `run_k6` starts a
        watcher that closes dashboard connections once the report is exported.
  - [x] Target firewall already allows 3000/tcp (`ufw allow 3000/tcp`), so private-IP traffic works for any
        load-generator IP.
  - [x] Smoke test (20 VUs): all files back, Server-Timing recorded, outside-the-app p50 1.7 ms, load generator 1 % CPU.

### Restart under protocol v2 (2026-10-10)
Protocol v2 = protocol v1 + required `Server-Timing` header + all runs from the blr1 load-generator droplet.
All protocol-v1 results (MacBook load source) are dropped: their GitHub releases/tags are deleted and
`results/node-express-*`, the README tables and `results/results.csv` are cleared. They stay in git history up to
commit `e10904b`. Kept learnings from that round (MacBook load, ~40 ms RTT):
- No pool: ~20 ms CPU per request, ~60 % of it Postgres connection setup; capacity 90 VUs / 42.8 req/s.
- `pg.Pool` (max 10): ~1.7–2 ms CPU per request; capacity 1250 VUs / 627 req/s; CPU ceiling ≈ 600–630 req/s;
  overload degrades into queueing with 0 % errors. Memory never above ~500 MB.
- Unexplained p95/p99 tail from 400 VUs while CPU < 60 % — server timing should explain it.

### Phase 1 — Node.js + Express + Postgres (protocol v2)
- `apps/node-express/`: Express 5.3.0, pg 8.23.1, plain SQL, no ORM, single process, no reverse proxy, no request
  logging, `NODE_ENV=production`, default heap. `build.sh`: `npm ci --omit=dev`; `start.sh`: `exec node src/server.js`.
- Postgres 16 defaults (shared_buffers 128 MB, max_connections 100). Swap off.
- Writes use explicit `BEGIN/COMMIT` (like/unlike/comment: 3–4 round trips). Express defaults kept (ETag on,
  `x-powered-by` on).
- [x] `Server-Timing` implemented (first middleware patches `res.writeHead`; `withClient(req, fn)` times connect +
      close as `conn` and each query as `db`), k6 Trends `server_*`, summarizer/CSV/README columns. Verified locally:
      header on every response incl. 400/401/404; 30-VU smoke: server total p50 10.9 ms = conn 6.6 + db 3.5 + app 0.6.
- [x] **`node-express-v01-baseline`** — no pool (new `pg.Client` per request) + `Server-Timing`. Result: capacity
      100 VUs / 46.7 req/s (marginal), CPU-bound; `conn` (connect + auth) ≈ 80 % of server time; no `53300` errors.
- [x] **`node-express-v02-pool`** — one change: `pg.Pool` defaults (max 10) + `Server-Timing`. Result: capacity
      1350 VUs / 619 req/s, first fail 1400; peak 651 req/s. CPU-bound (Node ≈ 42 % / PG ≈ 50 %, ≈ 1.5 ms CPU/req);
      overload shows up as pool wait (`conn`), not query time or errors. The protocol-v1 tail from 400 VUs is gone
      (p99 43 ms at 500 VUs) — it was the MacBook/Wi-Fi path.
- [x] **`node-express-v03-pool-20`** — pool `max` 10 → 20. Worse: capacity 1200 VUs / 574 req/s (marginal), first
      fail 1300. `db` time ≈ 2× at every level; on 1 vCPU more concurrent queries only add contention. Keep pool 10.
- [x] **`node-express-v04-cte-writes`** (parent v02) — like/unlike/comment as one CTE statement instead of
      BEGIN/2 queries/COMMIT (≈ 30 % fewer queries). No measurable gain at the ceiling: 1400 pass (marginal) but
      1300/1350 fail; same 540–660 req/s band as v02. Kept as parent. Lesson: at 100 % CPU single runs swing ±60 req/s;
      include an unsaturated level (1000 VUs) to compare CPU per request.
- [x] **`node-express-v05-prepared`** (parent v04) — named queries (`pg` prepared statements). Capacity 1400 VUs /
      645 req/s; Postgres CPU share ≈ 43.5 % (was ≈ 50 %); likely 5–10 % gain, within noise. Found host-speed
      variance (one run ≈ 30 % faster, no steal) → added `cpu_probe.sh` + `cpu_ms_per_req_steady`.
- [x] Profile of v05 at 1000 VUs (`profiles/2026-10-10-node-express-v05-1000vus/`): Node 44 % / Postgres 35 % /
      idle 14 %; Memoize setup in feed queries ≈ 10 % of Postgres CPU; Express + router ≈ 24 % of Node JS time.
- [x] **`node-express-v06-feed-cache-1s`** (parent v05) — in-process cache of `GET /posts` (all pages, key
      limit + before, TTL 1 s, single-flight; ≈ 47 % of requests). Labelled trade-off: global feed up to 1 s stale.
      Capacity 3000 VUs / 1541 req/s (2.4× v05), first fail 3200; 99.6 % hits; CPU/req 0.97 vs. 1.67 ms at 1000 VUs.
      Still CPU-bound, now Node ≈ 60 % / PG ≈ 30 %. At saturation cached feed requests wait ≈ 200 ms p95 behind the
      refresh query's pool wait (stale-while-revalidate would fix it).
- [x] `feed-cache-5s` (parent v06), **not released**: 3200 VUs FAIL, 1487 req/s; hits already 99.6 %, no gain.
- [x] nginx (parent v06), **not released**: plain proxy 3000 VUs FAIL, 1103 req/s (nginx 15 % CPU); `proxy_cache` for the
      feed instead of the app cache 3000 VUs FAIL, 1473 req/s (nginx 17 % CPU). On 1 vCPU a proxy costs what it saves.
      Scripts keep optional `apps/<stack>/nginx.conf` support (app moves to :3001; sampler records nginx CPU/PSS).
- [ ] `enable_memoize = off` (moved down: the cache removes most feed queries, where Memoize cost was).
- VU levels are chosen by the user for every run.

### Phase 1b — plain Node.js `node:http` (`apps/node-http/`)
- [x] **`node-http-v01-express-v06-port`** (parent node-express v06) — Express removed, otherwise a 1:1 port (same
      pool, prepared statements, CTE writes, 1 s feed cache; no ETag). Parity check: 39 requests identical. Capacity
      3200 VUs / 1678 req/s, first fail 3500 (p99 1175 ms); Node : PG CPU 1.55 vs. 1.93 for Express.
- [x] **`node-http-v02-bun`** (parent v01) — runtime Node 24 → Bun 1.4.2, same code. Capacity 4200 VUs / 2078 req/s,
      first fail 4500 (CPU 100 %, ceiling ≈ 2100 req/s); app : PG CPU 1.28 vs. 1.48 on Node.
- [x] `pool-20` on Bun (parent v02), **not released**: 4500 VUs FAIL, 2104 req/s (= pool 10), query time 2×, p99
      1404 vs. 1045 ms. The CPU is the ceiling, not the pool; keep pool 10.
- [x] **`node-http-v03-bun-sql`** (parent v02) — Bun.sql instead of pg. 4500 VUs FAIL (1955 req/s, slow host); app : PG
      1.22 vs. 1.29, ≤ 5 % gain. Released as base for v04 (user decision).
- [x] **`node-http-v04-bun-serve`** (parent v03) — `Bun.serve` instead of `node:http`. **4500 VUs PASS, 2324 req/s**
      (p99 912 ms), no fail level tested (load generator near its limit); app : PG 0.91 (Postgres now the larger
      share), Bun PSS 59 MB. **Node/Bun phase closed here (user, 2026-10-11).**

### Phase 2 — Node.js optimisations (one per tag, keep what helps)
Candidates, roughly in order: pool size (5 / 20 / 50); `pg-native` or prepared statements; Postgres tuning
(`shared_buffers`, `work_mem`, `synchronous_commit=off` as a labelled trade-off); 1 GB swap file; cluster with 2
workers (expected little gain on 1 vCPU — measure it); `--max-old-space-size`; Fastify instead of Express;
single-statement CTE writes instead of BEGIN/COMMIT; disable ETag; in-process cache of the first global feed page
(1 s TTL); PgBouncer; nginx in front (keep-alive, gzip on/off);
Bun runtime; uWebSockets.js / Hono.

### Cross-stack baseline (decided 2026-10-11)
Order: **Python → Go → Rust → C++**. Each new stack starts as a port of the best Node/Bun logic so results compare
directly: same API, single-statement CTE writes, prepared statements, DB pool max 10, the **1 s in-process cache of
`GET /posts`** (single-flight, all pages), `Server-Timing`. Run the 39-request parity check (`parity.sh`-style:
status + body + content type vs. node-http) before the first load test. Reference: `node-http-v04-bun-serve`
≥ 4500 VUs / 2324 req/s. Levels above ≈ 4500 VUs need an 8 vCPU load generator (new `LOADGEN_LABEL`).

### Phase 3 — Python
FastAPI + uvicorn + asyncpg (baseline: 1 worker), then gunicorn worker count, uvloop, orjson; optionally Django/DRF
for a "batteries included" data point.

### Phase 4 — Go
`net/http` + `pgx` pool baseline; then GOMAXPROCS / GOGC / memory limit, chi/fiber, sqlc.

### Phase 5 — Rust
axum + tokio + `sqlx` or `tokio-postgres` + deadpool; release build with LTO; then tuning.

### Phase 6 — C++
To be chosen when Rust is done (e.g. Drogon with its async Postgres client, or a minimal server on Boost.Beast +
libpq / libpqxx); release build, same contract and cache.

### Phase 7 — Others and cross-stack
Bun/Hono, Java (Spring Boot vs. Quarkus native — interesting under 1 GB), .NET minimal APIs, Elixir/Phoenix,
PHP (FrankenPHP/Laravel Octane). Cross-stack experiments: Postgres over Unix socket, kernel tuning, swap sizes,
HTTP/1.1 keep-alive behaviour.

## Notes for Claude

- **After every test, write the analysis summary into the report** before releasing:
  `results/<tag>/config.md` → `## Summary` (verdict: capacity + req/s; the bottleneck and the evidence — CPU split
  app/Postgres, memory, connections, error messages from `app_log_tail.txt`, steal; comparison with the parent tag;
  recommended next experiment), plus the Results/Observations sections, and a 2–3 line entry in README "Findings".
  `release.sh` refuses to release while the template placeholders are still there.
- **Keep README "Next steps" current** after every test (user request): where the best configuration stands, and
  the ordered list of next experiments with the reason for each. README "Analysis per configuration" is generated
  from `config.md` by `scripts/readme_analysis.py` (run by `release.sh`), so write the analysis in `config.md` only.
- **Do not publish reports as claude.ai Artifacts** (user decision). The `report-<tag>.html` attached to the GitHub
  release by `release.sh` is enough; it is generated by `scripts/report_html.py` without spending tokens.

- Keep this file current: tick plan items, add findings that change the plan, record protocol changes.
- New stack = new `apps/<stack>/` with `start.sh` (+ optional `build.sh`); add any runtime install to
  `scripts/server/setup.sh` (it is idempotent) — do not change other stacks' apps.
- Never edit files under an already released `results/<tag>/`.
- Before claiming an optimisation helped, compare at the same VU levels, same load source, and check steal %
  (a noisy neighbour can swing results; re-run if steal is high).
- To compare changes worth < 10 %, suggest one unsaturated level (CPU per request, e.g. 1000 VUs for node-express
  up to v05, 1000–1500 VUs with the feed cache) in
  addition to edge levels; at the ceiling single runs swing ±60 req/s.
- Near the CPU ceiling single runs are noisy (v02: 1200 VUs scored worse than 1250 after a load-generator stall).
  Check `server_metrics.csv` for CPU dips with connections still open (= client/network stall) before trusting a
  fail/pass at the edge; suggest a repeat run when it matters.
- Run Python scripts with `python3 -I`. `scripts/server/*.sh` run as root on the droplet via `ssh bash -s`.
