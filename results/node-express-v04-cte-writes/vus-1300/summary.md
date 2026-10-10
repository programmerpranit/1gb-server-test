# node-express-v04-cte-writes — 1300 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v04-cte-writes | node-express | 1300 | FAIL | 542.2 | 32532 | 53633 | 532.4 | 1060.1 | 1242.8 | 1515.5 | 1580 | 506.3 | 1206.3 | 1184.3 | 0 | 129 | 111 | 491 | 0 | 99.5 | 0.6 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 532>=500ms, p95 1243>=800ms, p99 1515>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 506.3 | 1206.3 | 1476.8 | 1552.3 |
| conn | 488.2 | 1184.3 | 1456.1 | 1520.5 |
| db | 14.7 | 37.8 | 62.2 | 168 |
| app | 0.2 | 1 | 2.6 | 11.2 |

Outside the app (client p − server total p): p50 26.1 ms, p95 36.5 ms. Responses without Server-Timing: 0.

Load generator: CPU 19.4 % avg steady / 64.8 % peak (all vCPUs), k6 RSS 694 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1131.7 / 1105.2
- `GET /me/posts`: 1109.3 / 1073.3
- `GET /posts`: 1123.8 / 1099.5
- `GET /posts/:id`: 1141.4 / 1118.2
- `GET /users/:id/posts`: 1125.2 / 1101.9
- `POST /posts`: 1145.2 / 1119.6
- `POST /posts/:id/comments`: 1094.4 / 1052.7
- `POST /posts/:id/like`: 1117.3 / 1089.5
