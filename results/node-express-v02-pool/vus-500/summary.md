# node-express-v02-pool — 500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 500 | PASS | 271.4 | 16287 | 24650 | 3.6 | 10.5 | 17.8 | 43.0 | 108 | 2.4 | 11.8 | 0.1 | 0 | 107 | 104 | 458 | 0 | 56.4 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 2.4 | 11.8 | 27.8 | 96.4 |
| conn | 0 | 0.1 | 0.5 | 86.6 |
| db | 2.1 | 11.1 | 25.8 | 82.2 |
| app | 0.2 | 0.4 | 1.4 | 8.3 |

Outside the app (client p − server total p): p50 1.2 ms, p95 6.0 ms. Responses without Server-Timing: 0.

Load generator: CPU 11.5 % avg steady / 29.8 % peak (all vCPUs), k6 RSS 301 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 27.1 / 23.0
- `GET /me/posts`: 13.6 / 7.5
- `GET /posts`: 15.1 / 9.1
- `GET /posts/:id`: 17.7 / 12.4
- `GET /users/:id/posts`: 14.2 / 8.4
- `POST /posts`: 16.6 / 11.5
- `POST /posts/:id/comments`: 24.0 / 17.3
- `POST /posts/:id/like`: 24.5 / 19.0
