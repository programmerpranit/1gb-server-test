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
| node-express-v01-baseline | node-express | baseline: no pool, new connection per request (old criteria, no search) | < 100 | 100 | - | - | - | - | - | - | - | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline) |
| node-express-v01-baseline-r2 | node-express | baseline: no pool, new connection per request | 90 | 100 | 42.8 | 2569 | 234.4 | 658.5 | 979.8 | 0 | 428 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline-r2) |
<!-- CAPACITY:END -->

## Findings

One analysis summary per tag; the full report (summary, configuration, results, observations) is
`results/<tag>/config.md` and is also the GitHub release notes.

- **node-express-v01-baseline** — No connection pool (new Postgres connection per request). CPU-bound from 100 VUs
  (~97 % of the single vCPU); Postgres spends ~60 % of CPU on per-request connection setup (backend fork + SCRAM
  auth). 250 VUs → 24 % errors from connection exhaustion (`max_connections` 100). Memory is not the limit (530 MB
  peak). [Report](results/node-express-v01-baseline/config.md)
- **node-express-v01-baseline-r2** — Same build, new criteria + capacity search. **Capacity 75 VUs / 39.1 req/s**
  -> **90 VUs / 42.8 req/s** after an extra 90-VU run (marginal pass: p99 980 ms; 75 VUs is the comfortable level at
  p99 261 ms); 100 VUs fails on latency (p95 890 ms) at a ~44 req/s CPU ceiling. ~20 ms CPU per request, ~60 % of
  it in Postgres (connection setup). Memory ≤ 487 MB. Repeatable vs. v01 within 2 % throughput.
  [Report](results/node-express-v01-baseline-r2/config.md)

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

<!-- RESULTS:START -->
| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 100 | FAIL | 44.4 | 2666 | 4207 | 331.8 | 703.6 | 824.4 | 1001.7 | 1138 | 0 | 107 | 63 | 425 | 0 | 96.7 | 0.1 | macbook-home-wifi |
| node-express-v01-baseline | node-express | 250 | FAIL | 57.4 | 3441 | 5869 | 2694.0 | 3500.0 | 3764.9 | 4298.2 | 4780 | 24.08 | 114 | 124 | 530 | 0 | 100.0 | 0.3 | macbook-home-wifi |
| node-express-v01-baseline-r2 | node-express | 100 | FAIL | 43.7 | 2622 | 4100 | 460.6 | 792.8 | 889.5 | 1025.3 | 1132 | 0 | 106 | 66 | 487 | 0 | 97.9 | 0.3 | macbook-home-wifi |
| node-express-v01-baseline-r2 | node-express | 50 | PASS | 26.4 | 1584 | 2390 | 49.9 | 95.4 | 117.6 | 171.3 | 212 | 0 | 103 | 42 | 399 | 0 | 52.0 | 0.1 | macbook-home-wifi |
| node-express-v01-baseline-r2 | node-express | 75 | PASS | 39.1 | 2345 | 3536 | 80.7 | 164.5 | 202.1 | 261.2 | 323 | 0 | 106 | 41 | 409 | 0 | 78.2 | 0.1 | macbook-home-wifi |
| node-express-v01-baseline-r2 | node-express | 90 | PASS | 42.8 | 2569 | 3974 | 234.4 | 550.9 | 658.5 | 979.8 | 1177 | 0 | 103 | 59 | 428 | 0 | 94.1 | 0.3 | macbook-home-wifi |
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
