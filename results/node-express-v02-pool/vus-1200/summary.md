# node-express-v02-pool — 1200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1200 | PASS | 608.5 | 36512 | 55986 | 82.2 | 307.3 | 428.3 | 716.9 | 847 | 66.3 | 410.1 | 386.8 | 0 | 116 | 110 | 477 | 0 | 98.5 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 66.3 | 410.1 | 695.4 | 838.7 |
| conn | 50.3 | 386.8 | 676.5 | 771.3 |
| db | 10.2 | 38.1 | 57.5 | 160.7 |
| app | 0.2 | 1.4 | 2.8 | 10.6 |

Outside the app (client p − server total p): p50 15.9 ms, p95 18.1 ms. Responses without Server-Timing: 0.

Load generator: CPU 20.9 % avg steady / 68.5 % peak (all vCPUs), k6 RSS 657 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 386.1 / 373.4
- `GET /me/posts`: 384.0 / 360.5
- `GET /posts`: 377.8 / 358.6
- `GET /posts/:id`: 386.6 / 367.7
- `GET /users/:id/posts`: 380.9 / 361.1
- `POST /posts`: 400.4 / 384.8
- `POST /posts/:id/comments`: 426.0 / 413.3
- `POST /posts/:id/like`: 404.5 / 388.6
