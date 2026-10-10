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
| node-express-v01-baseline | node-express | baseline: no pool, new connection per request, Server-Timing header | 100 | 110 | 46.7 | 2804 | 242.4 | 742.4 | 958.8 | 0 | 446 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline) |
<!-- CAPACITY:END -->

## Findings

One analysis summary per tag; the full report (summary, configuration, results, observations) is
`results/<tag>/config.md` and is also the GitHub release notes.

- **node-express-v01-baseline** — No pool, new Postgres connection per request. **Capacity 100 VUs / 46.7 req/s**
  (marginal: p99 959 ms); 110 VUs fails on p95 (852 ms). CPU-bound at 98 %; server time p50 227 ms of which **conn
  181 ms** (connect + SCRAM auth), db 38 ms, app 0.5 ms. Memory 446 MB peak, 0 % errors.
  [Report](results/node-express-v01-baseline/config.md)

_Protocol-v1 results (MacBook load source) were dropped on 2026-10-10; see git history up to commit `e10904b`._

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
| node-express-v01-baseline | node-express | 100 | PASS | 46.7 | 2804 | 4368 | 242.4 | 548.9 | 742.4 | 958.8 | 1141 | 227.1 | 693.7 | 596.6 | 0 | 108 | 70 | 446 | 0 | 97.7 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v01-baseline | node-express | 110 | FAIL | 49.8 | 2986 | 4643 | 362.3 | 704.6 | 852.2 | 991.6 | 1096 | 337.2 | 783.8 | 665.6 | 0 | 104 | 64 | 432 | 0 | 98.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
<!-- RESULTS:END -->

## Reproducing

```bash
cp .env.example .env            # fill SERVER_HOST, DB_PASSWORD, LOADGEN_HOST, TARGET_HOST, LOADGEN_LABEL
scripts/provision.sh            # once per target droplet
scripts/seed_db.sh              # once, or when schema/converter changes
scripts/provision_loadgen.sh    # once per load-generator droplet (installs pinned k6)
scripts/deploy.sh node-express  # each time the app changes
scripts/run_test.sh node-express-v01-baseline 100 200 300   # live dashboard: http://localhost:5665
scripts/release.sh node-express-v01-baseline
```
