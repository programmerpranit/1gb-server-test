# node-http-v02-bun — 3500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v02-bun | node-http | 3500 | PASS | 1854.7 | 111279 | 168427 | 5.8 | 75.1 | 166.1 | 424.6 | 591 | 0.8 | 149.4 | 101.7 | 0 | 102 | 129 | 498 | 0 | 89.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 0.8 | 149.4 | 406.0 | 570.7 |
| conn | 0 | 101.7 | 392.9 | 557.6 |
| db | 0.6 | 12.3 | 23.5 | 98.8 |
| app | 0 | 0.9 | 116.4 | 443.7 |

Outside the app (client p − server total p): p50 5.0 ms, p95 16.7 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.48 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 108.5 ms, after 79.7 ms.

Load generator: CPU 45.8 % avg steady / 99.8 % peak (all vCPUs), k6 RSS 1894 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 394.3 / 378.5
- `GET /me/posts`: 402.1 / 386.9
- `GET /posts`: 92.5 / 70.7
- `GET /posts/:id`: 416.6 / 398.3
- `GET /users/:id/posts`: 398.5 / 383.6
- `POST /posts`: 413.0 / 392.3
- `POST /posts/:id/comments`: 394.3 / 373.4
- `POST /posts/:id/like`: 401.8 / 387.7
