# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

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
   ("protocol v1"). If one must change, bump the protocol version in this file and README, and re-run the baselines.
3. **Never run the load generator on the droplet under test.** Preferred: a second droplet in the same region (e.g.
   2 vCPU / 4 GB, billed hourly, destroyed after a session) targeting the private VPC IP (`TARGET_HOST`). Acceptable:
   the Mac, but then latency includes the home network. `LOADGEN_LABEL` is recorded in every row; only compare rows
   with the same load source.
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
README.md                     results comparison tables (auto-updated by run_test.sh)
Twitterdatainsheets.xlsx      seed dataset (source of truth)
.env.example                  copy to .env (git-ignored): server IP, DB password, load-gen label
db/schema.sql                 shared Postgres schema (all stacks)
loadtest/stress.js            k6 stress test (all stacks)
apps/<stack>/                 one implementation per stack, e.g. apps/node-express/   (not created yet)
  build.sh                    optional; runs on the server as user `bench` (npm ci, go build, cargo build ...)
  start.sh                    required; must `exec` the server process; reads $PORT and $DATABASE_URL
results/CONFIG_TEMPLATE.md    template for results/<tag>/config.md
results/<tag>/                one directory per configuration
  config.md                   what changed + full config + observations
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
  run_test.sh <tag> [vus..]   full test for one configuration across a VU ladder
  summarize.py <run_dir>      k6 + server metrics -> summary + README row
  release.sh <tag>            commit results, git tag, GitHub release with build + results
  server/                     scripts executed ON the droplet via `ssh bash -s`
    setup.sh  seed.sh  reset_db.sh  install_app.sh  prepare_run.sh  collect_metrics.sh
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

## API contract (protocol v1)

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

## Load test protocol (protocol v1)

Tool: [k6](https://k6.io) (`brew install k6` on macOS; on Ubuntu follow
<https://grafana.com/docs/k6/latest/set-up/install-k6/>), script `loadtest/stress.js`, driven by `scripts/run_test.sh`.

- **Shape:** `ramping-vus` — 0 → N VUs linearly over 60 s, then hold N for 60 s. 2 min total per run.
- **Virtual user:** picks a random user id once (`X-User-Id`), then loops: one weighted action, then 1–3 s think time.
- **Action mix:** global feed 40 % (30 % of those scroll a 2nd page), view post 15 %, user's posts 15 %, my posts 7 %,
  like 12 %, unlike 2 %, comment 4 %, create post 5 % (10 % of new posts private). ≈77 % reads / 23 % writes.
  Likes/comments mostly target posts the VU just saw in a feed (realistic hot rows).
- **Phases:** each request is tagged `phase=ramp|steady`; headline throughput and latency use the steady phase.
- **Error:** any non-2xx response or a request taking longer than 10 s (k6 timeout).
- **VU ladder:** each configuration runs at `100 250 500 1000 2000` VUs (override per run), with a full reset between
  levels. The ladder stops when a level's error rate exceeds 5 %.
- **Capacity:** the highest ladder level with error rate < 1 % and steady p95 < 500 ms. This is the headline number.
- At ~2 s per iteration, N VUs produce roughly N/2 req/s offered load (a bit more with feed scrolling).

## Metrics recorded per run

From k6 (`k6_summary.json`): total requests, avg req/s, steady req/s and req/min, max VUs, error rate (overall and
steady), latency avg / p50 / p90 / p95 / p99 / max (overall, steady, per endpoint).

From the server (`server_metrics.csv`, 1 s samples by `collect_metrics.sh`): CPU busy / user / sys / iowait /
**steal** %, app CPU % and Postgres CPU % (cgroup), memory used / available, swap used, app PSS MB, Postgres PSS MB,
established connections on the app port, load average.

`summarize.py` reduces both into `summary.json` / `summary.md` and upserts a row into README's "All runs" table.
The "Headline" table in README is filled in by hand (capacity per tag).

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
scripts/run_test.sh <stack>-vNN-<slug>            # or pass explicit VU levels
# 3. fill results/<tag>/config.md (what changed, observations, next idea)
# 4. update README headline row, then
scripts/release.sh <stack>-vNN-<slug>
```

Server-side config changes (Postgres settings, swap) are made over ssh, described in `config.md`, and reverted
before the next unrelated experiment unless they become the new baseline for that stack.

## Plan

### Phase 0 — Infrastructure (done 2026-10-10)
- [x] Dataset analysis and converter (`scripts/xlsx_to_csv.py`)
- [x] Shared schema, API contract, k6 test, metrics sampler, run/summarize/release scripts
- [x] Droplet created (Ubuntu 24.04.5, kernel 6.8.0-142, 961 MB usable RAM), `.env` filled. Scripts SSH as root
      with key auth using `SSH_KEY` from `.env` (`~/.ssh/do`).
- [x] Load generator decided: the MacBook (`LOADGEN_LABEL=macbook-home-wifi`). Latency includes the home network, so
      keep the same network for every run, avoid other heavy traffic during tests, and treat absolute latency as
      "client-observed". A same-region droplet can be added later as a separate load source label.
- [x] GitHub repo created: `programmerpranit/1gb-server-test` (private)
- [x] Provisioned (Node v24.21.0, PostgreSQL 16.15) and seeded (`bench_seed` = 62 MB).
      Idle after `prepare_run.sh` with Postgres + node-express running: ~350 MB used, ~605 MB available
      (DigitalOcean agent + OS take ~300 MB before anything is installed). Idle PSS: node 62 MB, Postgres ~25 MB.
- [x] Tooling smoke-tested: all endpoints via curl against a local Postgres; k6 v2.3.0 run (30 VUs, 10 s + 10 s,
      0 errors); `prepare_run.sh` and `collect_metrics.sh` on the droplet. Mac → droplet RTT ≈ 40 ms.
- Notes: macOS ships `openrsync` (no `--chmod`); the sampler is one long-lived python3 process because forking
  `awk`/`ss` every second cost ~10 % of the vCPU (now ~1–2 %).

### Phase 1 — Node.js + Express + Postgres baseline (`node-express-v01-baseline`)
- `apps/node-express/`: Express 5, `pg` (node-postgres), plain SQL, no ORM. **No connection pool** (user decision):
  every request opens a new `pg.Client`, runs its queries (incl. its transaction) on it, and closes it before
  responding. Expect failures once concurrent requests exceed Postgres `max_connections` (100): error `53300`
  `sorry, too many clients already`, plus per-request backend fork + SCRAM auth cost (~20 ms extra per request
  observed at idle).
- Single process (no cluster/pm2), no reverse proxy, no request logging, `NODE_ENV=production`, default heap.
- `build.sh`: `npm ci --omit=dev`. `start.sh`: `exec node src/server.js`.
- Postgres 16 defaults (shared_buffers 128 MB, max_connections 100). Swap off.
- Versions: express 5.3.0, pg 8.23.1 (exact pins in `package.json`), Node v24.21.0 on the droplet.
- Writes use explicit `BEGIN/COMMIT` with a checked-out client (like/unlike/comment: 3–4 round trips). Collapsing
  them into a single CTE statement is a Phase 2 candidate. Express defaults kept (ETag on, `x-powered-by` on).
- [x] Contract implemented and verified with curl (status codes, 400/401/404 paths, private posts, idempotent likes).
- [x] Deployed to the droplet (`scripts/deploy.sh node-express`).
- [ ] Commit, run the ladder (`scripts/run_test.sh node-express-v01-baseline`), fill `config.md`, release.
- Expectation to verify: 1 vCPU saturates before 1 GB RAM does; watch steal %, the pool queue, and OOM kills.

### Phase 2 — Node.js optimisations (one per tag, keep what helps)
Candidates, roughly in order: introduce `pg.Pool` (default max 10), then pool size (5 / 20 / 50); `pg-native` or prepared statements; Postgres tuning
(`shared_buffers`, `work_mem`, `synchronous_commit=off` as a labelled trade-off); 1 GB swap file; cluster with 2
workers (expected little gain on 1 vCPU — measure it); `--max-old-space-size`; Fastify instead of Express;
single-statement CTE writes instead of BEGIN/COMMIT; disable ETag; in-process cache of the first global feed page
(1 s TTL); PgBouncer; nginx in front (keep-alive, gzip on/off);
Bun runtime; uWebSockets.js / Hono.

### Phase 3 — Python
FastAPI + uvicorn + asyncpg (baseline: 1 worker), then gunicorn worker count, uvloop, orjson; optionally Django/DRF
for a "batteries included" data point.

### Phase 4 — Go
`net/http` + `pgx` pool baseline; then GOMAXPROCS / GOGC / memory limit, chi/fiber, sqlc.

### Phase 5 — Rust
axum + tokio + `sqlx` or `tokio-postgres` + deadpool; release build with LTO; then tuning.

### Phase 6 — Others and cross-stack
Bun/Hono, Java (Spring Boot vs. Quarkus native — interesting under 1 GB), .NET minimal APIs, Elixir/Phoenix,
PHP (FrankenPHP/Laravel Octane). Cross-stack experiments: Postgres over Unix socket, kernel tuning, swap sizes,
HTTP/1.1 keep-alive behaviour.

## Notes for Claude

- Keep this file current: tick plan items, add findings that change the plan, record protocol changes.
- New stack = new `apps/<stack>/` with `start.sh` (+ optional `build.sh`); add any runtime install to
  `scripts/server/setup.sh` (it is idempotent) — do not change other stacks' apps.
- Never edit files under an already released `results/<tag>/`.
- Before claiming an optimisation helped, compare at the same VU levels, same load source, and check steal %
  (a noisy neighbour can swing results; re-run if steal is high).
- Run Python scripts with `python3 -I`. `scripts/server/*.sh` run as root on the droplet via `ssh bash -s`.
