# node-express-v02-pool — 1300 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1300 | PASS | 651.1 | 39069 | 59600 | 107.9 | 365.0 | 465.9 | 652.0 | 752 | 93.6 | 449.8 | 429.3 | 0 | 119 | 108 | 478 | 0 | 99.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 93.6 | 449.8 | 629.3 | 737.3 |
| conn | 77.6 | 429.3 | 610.9 | 688.5 |
| db | 10.2 | 36.6 | 54 | 153.5 |
| app | 0.2 | 1.4 | 2.8 | 8.7 |

Outside the app (client p − server total p): p50 14.3 ms, p95 16.1 ms. Responses without Server-Timing: 0.

Load generator: CPU 23.4 % avg steady / 44.1 % peak (all vCPUs), k6 RSS 706 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 550.0 / 535.1
- `GET /me/posts`: 519.3 / 503.6
- `GET /posts`: 512.7 / 494.1
- `GET /posts/:id`: 535.5 / 521.5
- `GET /users/:id/posts`: 538.7 / 521.5
- `POST /posts`: 504.2 / 483.4
- `POST /posts/:id/comments`: 564.0 / 543.6
- `POST /posts/:id/like`: 532.1 / 509.7
