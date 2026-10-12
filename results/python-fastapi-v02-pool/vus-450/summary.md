# python-fastapi-v02-pool — 450 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v02-pool | python-fastapi | 450 | PASS | 239.8 | 14388 | 21929 | 16.0 | 73.2 | 104.3 | 245.7 | 634 | 12.2 | 82.9 | 61.3 | 0 | 69 | 108 | 459 | 0 | 84.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 12.2 | 82.9 | 214.3 | 581 |
| conn | 6.3 | 61.3 | 196.8 | 563.8 |
| db | 4.8 | 20.8 | 34.8 | 149 |
| app | 0.8 | 2 | 3.4 | 111.1 |

Outside the app (client p − server total p): p50 3.8 ms, p95 21.4 ms. Responses without Server-Timing: 0.

CPU per request (steady): 3.50 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 92.4 ms, after 100.7 ms.

Load generator: CPU 10.4 % avg steady / 19.1 % peak (all vCPUs), k6 RSS 274 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 87.1 / 62.0
- `GET /me/posts`: 78.1 / 63.0
- `GET /posts`: 91.0 / 71.4
- `GET /posts/:id`: 97.0 / 78
- `GET /users/:id/posts`: 85.5 / 67.8
- `POST /posts`: 92.8 / 72.4
- `POST /posts/:id/comments`: 95.6 / 75.9
- `POST /posts/:id/like`: 81.1 / 62.7
