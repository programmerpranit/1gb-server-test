# 1 GB Server Test

How far can a **$6/month DigitalOcean droplet** (1 vCPU, 1 GB RAM, 25 GB SSD, 1000 GB transfer) go running the same
small social-feed API written in different languages and frameworks, with Postgres on the same box?

Every configuration is hit with the same 2-minute k6 test (60 s ramp from 0 to N virtual users, 60 s hold) and tagged
as a GitHub release with its code and raw results. Methodology, API contract and plan live in [CLAUDE.md](CLAUDE.md).

## Capacity per configuration

A run **passes** when, during the 60 s steady phase, **p50 < 500 ms, p95 < 800 ms and p99 < 1000 ms**, and the
whole-run **error rate is < 1 %**. VU levels for each configuration are chosen by hand
(`scripts/run_test.sh <tag> <vus...>`; an automatic ladder + bisection exists behind `--search`). **Capacity** is
the highest passing VU level tested; this table is updated automatically. Every run's full data point set is in
[`results/results.csv`](results/results.csv).

<!-- CAPACITY:START -->
| Tag | Stack | What changed | Capacity (VUs) | First fail (VUs) | Steady req/s | Steady req/min | p50 ms | p95 ms | p99 ms | Error % | Peak used MB | Release |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
<!-- CAPACITY:END -->

## Findings

One analysis summary per tag; the full report (summary, configuration, results, observations) is
`results/<tag>/config.md` and is also the GitHub release notes.

_No protocol-v2 results yet. Protocol-v1 results (MacBook load source) were dropped on 2026-10-10; see git history
up to commit `e10904b` and the "Restart under protocol v2" notes in CLAUDE.md._

## All runs

One row per (tag, VU level). `scripts/run_test.sh` upserts rows automatically.

- **Steady** columns cover only the 60 s hold phase; Total req and Error % cover the whole 2 min.
- Latency is k6 `http_req_duration` (server time + network to the load generator). Compare runs only with the same
  **Load from**.
- **App MB / PG MB** are PSS summed over the systemd unit's processes (Postgres shared memory is not double counted).
  **Used MB** is `MemTotal - MemAvailable` for the whole droplet.
- **CPU %** is whole-machine busy time out of one vCPU; **Steal %** is time taken by the hypervisor (noisy neighbours).
- **Error** = any non-2xx response or a request that exceeded the 10 s timeout.
- **Pass** uses the criteria above (steady p50/p95/p99, whole-run errors).
- **Srv / Conn** come from the app's `Server-Timing` header (steady phase): **Srv** = time inside the app,
  **Conn** = time to get a DB connection (connect + auth without a pool, waiting for a free connection with a pool).
  Client latency − Srv = time outside the handler (network, queues, load generator).

<!-- RESULTS:START -->
| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
<!-- RESULTS:END -->

## Reproducing

```bash
cp .env.example .env            # fill SERVER_HOST, DB_PASSWORD, LOADGEN_LABEL
brew install k6                 # on the load generator (Ubuntu: https://grafana.com/docs/k6/latest/set-up/install-k6/)
scripts/provision.sh            # once per droplet
scripts/seed_db.sh              # once, or when schema/converter changes
scripts/deploy.sh node-express  # each time the app changes
scripts/run_test.sh node-express-v01-baseline 100 250 500 1000
scripts/release.sh node-express-v01-baseline
```
