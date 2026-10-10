# node-express-v02-pool — 1400 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1400 | FAIL | 517.7 | 31061 | 51671 | 895.2 | 1273.5 | 1319.7 | 1389.0 | 1491 | 878.7 | 1298.7 | 1275.7 | 0 | 131 | 125 | 509 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 895>=500ms, p95 1320>=800ms, p99 1389>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 878.7 | 1298.7 | 1370.2 | 1479.5 |
| conn | 861.3 | 1275.7 | 1347.5 | 1414 |
| db | 12.9 | 48.1 | 79 | 209.6 |
| app | 0.2 | 1.8 | 3.5 | 14.3 |

Outside the app (client p − server total p): p50 16.5 ms, p95 21.0 ms. Responses without Server-Timing: 0.

Load generator: CPU 19.0 % avg steady / 63.7 % peak (all vCPUs), k6 RSS 742 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1305.6 / 1284.4
- `GET /me/posts`: 1277.7 / 1255.0
- `GET /posts`: 1280.6 / 1254.8
- `GET /posts/:id`: 1295.8 / 1271.9
- `GET /users/:id/posts`: 1283.8 / 1259.2
- `POST /posts`: 1291.7 / 1263.0
- `POST /posts/:id/comments`: 1308.2 / 1286.9
- `POST /posts/:id/like`: 1319.8 / 1294.4
