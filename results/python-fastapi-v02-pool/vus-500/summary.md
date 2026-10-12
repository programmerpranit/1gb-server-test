# python-fastapi-v02-pool — 500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v02-pool | python-fastapi | 500 | PASS | 266.1 | 15965 | 24327 | 20.2 | 85.1 | 114.0 | 193.8 | 530 | 15.3 | 95.4 | 77.4 | 0 | 70 | 110 | 462 | 0 | 86.7 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 15.3 | 95.4 | 175.5 | 515.7 |
| conn | 8.3 | 77.4 | 152.9 | 503.4 |
| db | 5.7 | 21 | 34.9 | 92.9 |
| app | 0.8 | 1.9 | 3.3 | 50.5 |

Outside the app (client p − server total p): p50 4.9 ms, p95 18.6 ms. Responses without Server-Timing: 0.

CPU per request (steady): 3.26 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 94.1 ms, after 85.7 ms.

Load generator: CPU 12.1 % avg steady / 27.6 % peak (all vCPUs), k6 RSS 300 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 110.0 / 88.1
- `GET /me/posts`: 94.9 / 77.7
- `GET /posts`: 100.3 / 82.6
- `GET /posts/:id`: 108.3 / 89.7
- `GET /users/:id/posts`: 98.0 / 81.6
- `POST /posts`: 98.9 / 84.3
- `POST /posts/:id/comments`: 112.6 / 97.9
- `POST /posts/:id/like`: 97.1 / 82.2
