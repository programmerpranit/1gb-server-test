# 1 GB Server Test

How far can a **$6/month DigitalOcean droplet** (1 vCPU, 1 GB RAM, 25 GB SSD, 1000 GB transfer) go running the same
small social-feed API written in different languages and frameworks, with Postgres on the same box?

Every configuration is hit with the same 2-minute k6 test (60 s ramp from 0 to N virtual users, 60 s hold) and tagged
as a GitHub release with its code and raw results. Methodology, API contract and plan live in [CLAUDE.md](CLAUDE.md).

## Capacity per configuration

A run **passes** when, during the 60 s steady phase, **p50 < 500 ms, p95 < 800 ms and p99 < 1000 ms**, and the
whole-run **error rate is < 1 %**. `scripts/run_test.sh` climbs the VU ladder until a level fails, then
binary-searches (25-VU resolution) between the last pass and the first fail. **Capacity** is the highest passing
VU level; this table is updated automatically. Every run's full data point set is in
[`results/results.csv`](results/results.csv).

<!-- CAPACITY:START -->
| Tag | Stack | What changed | Capacity (VUs) | First fail (VUs) | Steady req/s | Steady req/min | p50 ms | p95 ms | p99 ms | Error % | Peak used MB | Release |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | baseline: no pool, new connection per request (old criteria, no search) | < 100 | 100 | - | - | - | - | - | - | - | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v01-baseline) |
<!-- CAPACITY:END -->

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
