# node-express-v02-pool — 1350 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1350 | PASS | 619.1 | 37149 | 58671 | 324.7 | 577.7 | 689.8 | 775.8 | 864 | 309.6 | 670.4 | 651.2 | 0 | 124 | 108 | 484 | 0 | 100.0 | 0.1 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 309.6 | 670.4 | 760.7 | 843.6 |
| conn | 292.8 | 651.2 | 742.8 | 809.5 |
| db | 11.1 | 40.1 | 60.4 | 127.4 |
| app | 0.2 | 1.5 | 3 | 10.7 |

Outside the app (client p − server total p): p50 15.1 ms, p95 19.4 ms. Responses without Server-Timing: 0.

Load generator: CPU 20.6 % avg steady / 65.2 % peak (all vCPUs), k6 RSS 722 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 656.3 / 642.9
- `GET /me/posts`: 624.2 / 606.3
- `GET /posts`: 620.9 / 599.2
- `GET /posts/:id`: 634.7 / 617.0
- `GET /users/:id/posts`: 619.8 / 597.5
- `POST /posts`: 632.7 / 614.7
- `POST /posts/:id/comments`: 657.2 / 642.9
- `POST /posts/:id/like`: 649.4 / 631.8
