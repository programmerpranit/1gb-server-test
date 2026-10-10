# node-express-v03-pool-20 — 1350 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v03-pool-20 | node-express | 1350 | FAIL | 496.5 | 29789 | 48359 | 859.7 | 1198.3 | 1249.3 | 1325.9 | 1475 | 816.1 | 1201.2 | 1154.8 | 0 | 131 | 137 | 524 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 860>=500ms, p95 1249>=800ms, p99 1326>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 816.1 | 1201.2 | 1283.3 | 1430.8 |
| conn | 773.9 | 1154.8 | 1226.2 | 1311.2 |
| db | 25.3 | 101.7 | 166.1 | 292.6 |
| app | 0.2 | 1.9 | 3.6 | 17.9 |

Outside the app (client p − server total p): p50 43.6 ms, p95 48.1 ms. Responses without Server-Timing: 0.

Load generator: CPU 20.5 % avg steady / 60.8 % peak (all vCPUs), k6 RSS 721 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1297.9 / 1253.3
- `GET /me/posts`: 1213.3 / 1161.4
- `GET /posts`: 1214.8 / 1164.7
- `GET /posts/:id`: 1242.7 / 1192.9
- `GET /users/:id/posts`: 1218.5 / 1169.4
- `POST /posts`: 1216.0 / 1166.9
- `POST /posts/:id/comments`: 1290.7 / 1239.1
- `POST /posts/:id/like`: 1288.6 / 1240.1
