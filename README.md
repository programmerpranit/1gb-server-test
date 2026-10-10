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
| node-express-v02-pool | node-express | pg.Pool with default settings (max 10) instead of a new connection per request | 1350 | 1400 | 619.1 | 37149 | 324.7 | 689.8 | 775.8 | 0 | 484 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v02-pool) |
| node-express-v03-pool-20 | node-express | pg.Pool max 10 -> 20 | 1200 | 1300 | 574.0 | 34443 | 181.7 | 755.7 | 971.9 | 0 | 513 | [release](https://github.com/programmerpranit/1gb-server-test/releases/tag/node-express-v03-pool-20) |
<!-- CAPACITY:END -->

## Findings

One analysis summary per tag; the full report (summary, configuration, results, observations) is
`results/<tag>/config.md` and is also the GitHub release notes.

- **node-express-v01-baseline** — No pool, new Postgres connection per request. **Capacity 100 VUs / 46.7 req/s**
  (marginal: p99 959 ms); 110 VUs fails on p95 (852 ms). CPU-bound at 98 %; server time p50 227 ms of which **conn
  181 ms** (connect + SCRAM auth), db 38 ms, app 0.5 ms. Memory 446 MB peak, 0 % errors.
  [Report](results/node-express-v01-baseline/config.md)
- **node-express-v02-pool** — `pg.Pool` defaults (max 10). **Capacity 1350 VUs / 619 req/s** (p95 690 ms);
  1400 VUs fails (p50 895 ms). Peak 651 req/s at 1300 VUs; 13× v01. CPU-bound at 100 % (Node ≈ 42 % / Postgres
  ≈ 50 %), ≈ 1.5 ms CPU per request. Past the ceiling, latency is pool wait (`conn` p95 1276 ms at 1400 VUs) while
  queries stay at p95 ≤ 48 ms; 0 % errors at every level. Memory ≤ 509 MB.
  [Report](results/node-express-v02-pool/config.md)
- **node-express-v03-pool-20** — pool `max` 10 → 20. **Worse: capacity 1200 VUs / 574 req/s** (marginal: p99
  972 ms); 1300 VUs fails. CPU-bound as before, but twice as many concurrent queries on 1 vCPU double `db` time
  (p95 83–102 ms vs. 37–48 ms) and time outside the handler (≈ 35 vs. 15 ms). Overload p99 2450 ms at 1500 VUs.
  Keep pool 10. [Report](results/node-express-v03-pool-20/config.md)

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
| node-express-v02-pool | node-express | 500 | PASS | 271.4 | 16287 | 24650 | 3.6 | 10.5 | 17.8 | 43.0 | 108 | 2.4 | 11.8 | 0.1 | 0 | 107 | 104 | 458 | 0 | 56.4 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1000 | PASS | 538.0 | 32282 | 49105 | 7.2 | 45.4 | 62.7 | 141.3 | 281 | 4.7 | 44.8 | 23.8 | 0 | 114 | 108 | 471 | 0 | 84.2 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1500 | FAIL | 546.8 | 32810 | 54948 | 832.0 | 1273.1 | 1377.3 | 1441.7 | 1565 | 814.4 | 1348.5 | 1329.9 | 0 | 133 | 125 | 506 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1200 | PASS | 608.5 | 36512 | 55986 | 82.2 | 307.3 | 428.3 | 716.9 | 847 | 66.3 | 410.1 | 386.8 | 0 | 116 | 110 | 477 | 0 | 98.5 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1250 | PASS | 575.6 | 34538 | 54611 | 308.8 | 495.0 | 634.4 | 839.7 | 1100 | 292.4 | 616.0 | 596.7 | 0 | 122 | 109 | 501 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1300 | PASS | 651.1 | 39069 | 59600 | 107.9 | 365.0 | 465.9 | 652.0 | 752 | 93.6 | 449.8 | 429.3 | 0 | 119 | 108 | 478 | 0 | 99.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1350 | PASS | 619.1 | 37149 | 58671 | 324.7 | 577.7 | 689.8 | 775.8 | 864 | 309.6 | 670.4 | 651.2 | 0 | 124 | 108 | 484 | 0 | 100.0 | 0.1 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v02-pool | node-express | 1400 | FAIL | 517.7 | 31061 | 51671 | 895.2 | 1273.5 | 1319.7 | 1389.0 | 1491 | 878.7 | 1298.7 | 1275.7 | 0 | 131 | 125 | 509 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1400 | FAIL | 604.3 | 36259 | 58260 | 407.5 | 788.5 | 897.3 | 1144.6 | 1279 | 374.6 | 856.8 | 815.9 | 0 | 130 | 139 | 525 | 0 | 100.0 | 0.2 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1500 | FAIL | 524.5 | 31468 | 54877 | 909.1 | 1498.5 | 1935.5 | 2450.0 | 2648 | 874.9 | 1892.1 | 1832.1 | 0 | 136 | 155 | 542 | 0 | 100.0 | 0.5 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1300 | FAIL | 562.6 | 33755 | 54136 | 414.0 | 936.4 | 1031.1 | 1114.0 | 1237 | 379 | 990.3 | 942.6 | 0 | 126 | 137 | 518 | 0 | 99.2 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1350 | FAIL | 496.5 | 29789 | 48359 | 859.7 | 1198.3 | 1249.3 | 1325.9 | 1475 | 816.1 | 1201.2 | 1154.8 | 0 | 131 | 137 | 524 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |
| node-express-v03-pool-20 | node-express | 1200 | PASS | 574.0 | 34443 | 53684 | 181.7 | 567.0 | 755.7 | 971.9 | 1108 | 146.8 | 706.6 | 655.8 | 0 | 120 | 138 | 513 | 0 | 98.8 | 0.3 | do-blr1-loadgen-4vcpu-8gb |
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
