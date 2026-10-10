# node-express-v02-pool — 1500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1500 | FAIL | 546.8 | 32810 | 54948 | 832.0 | 1273.1 | 1377.3 | 1441.7 | 1565 | 814.4 | 1348.5 | 1329.9 | 0 | 133 | 125 | 506 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 832>=500ms, p95 1377>=800ms, p99 1442>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 814.4 | 1348.5 | 1419.5 | 1548 |
| conn | 795.5 | 1329.9 | 1398 | 1500.4 |
| db | 12.3 | 45.6 | 77.5 | 218.1 |
| app | 0.2 | 1.7 | 3.4 | 15.6 |

Outside the app (client p − server total p): p50 17.6 ms, p95 28.8 ms. Responses without Server-Timing: 0.

Load generator: CPU 19.9 % avg steady / 72.4 % peak (all vCPUs), k6 RSS 789 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1405.8 / 1368.4
- `GET /me/posts`: 1285.2 / 1260.5
- `GET /posts`: 1297.4 / 1270.8
- `GET /posts/:id`: 1313.7 / 1289.7
- `GET /users/:id/posts`: 1301.4 / 1273.7
- `POST /posts`: 1298.0 / 1276.0
- `POST /posts/:id/comments`: 1333.1 / 1309.6
- `POST /posts/:id/like`: 1322.2 / 1288.3
