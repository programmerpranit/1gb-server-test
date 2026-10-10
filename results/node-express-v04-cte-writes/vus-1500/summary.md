# node-express-v04-cte-writes — 1500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v04-cte-writes | node-express | 1500 | FAIL | 613.6 | 36817 | 61506 | 495.9 | 1155.3 | 1315.9 | 1438.5 | 1531 | 474.5 | 1273.7 | 1252.0 | 0 | 136 | 111 | 516 | 0 | 99.9 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1316>=800ms, p99 1439>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 474.5 | 1273.7 | 1402.4 | 1512.7 |
| conn | 458.3 | 1252.0 | 1382.4 | 1478.8 |
| db | 13 | 33.5 | 57.2 | 162.4 |
| app | 0.2 | 0.6 | 2.3 | 50.7 |

Outside the app (client p − server total p): p50 21.4 ms, p95 42.2 ms. Responses without Server-Timing: 0.

Load generator: CPU 20.7 % avg steady / 65.3 % peak (all vCPUs), k6 RSS 797 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1215.5 / 1189.9
- `GET /me/posts`: 1213.7 / 1186.9
- `GET /posts`: 1194.2 / 1167.7
- `GET /posts/:id`: 1201.5 / 1173.2
- `GET /users/:id/posts`: 1177.7 / 1150.9
- `POST /posts`: 1220.3 / 1184.5
- `POST /posts/:id/comments`: 1158.1 / 1122.0
- `POST /posts/:id/like`: 1221.9 / 1196.4
