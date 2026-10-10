# node-express-v02-pool — 1000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1000 | PASS | 538.0 | 32282 | 49105 | 7.2 | 45.4 | 62.7 | 141.3 | 281 | 4.7 | 44.8 | 23.8 | 0 | 114 | 108 | 471 | 0 | 84.2 | 0.1 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 4.7 | 44.8 | 124.8 | 266.8 |
| conn | 0 | 23.8 | 104.5 | 222.9 |
| db | 4.4 | 24.5 | 43.6 | 105.5 |
| app | 0.2 | 0.4 | 2 | 7.4 |

Outside the app (client p − server total p): p50 2.5 ms, p95 17.9 ms. Responses without Server-Timing: 0.

Load generator: CPU 18.9 % avg steady / 62.0 % peak (all vCPUs), k6 RSS 553 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 73.4 / 60.2
- `GET /me/posts`: 46.1 / 29.1
- `GET /posts`: 48.6 / 30.5
- `GET /posts/:id`: 59.6 / 42.6
- `GET /users/:id/posts`: 46.1 / 28.2
- `POST /posts`: 47.9 / 30.9
- `POST /posts/:id/comments`: 77.3 / 60.6
- `POST /posts/:id/like`: 74.7 / 57.6
