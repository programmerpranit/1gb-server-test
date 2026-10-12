# python-fastapi-v02-pool — 600 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v02-pool | python-fastapi | 600 | PASS | 306.9 | 18417 | 28367 | 42.6 | 293.9 | 434.6 | 862.6 | 2715 | 32.6 | 415.1 | 398.7 | 0 | 71 | 112 | 463 | 0 | 94.3 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 32.6 | 415.1 | 843.8 | 2683.4 |
| conn | 19.7 | 398.7 | 826.1 | 2672.4 |
| db | 9.2 | 23.7 | 37.7 | 96.5 |
| app | 0.8 | 1.9 | 3.3 | 19.8 |

Outside the app (client p − server total p): p50 10.0 ms, p95 19.6 ms. Responses without Server-Timing: 0.

CPU per request (steady): 3.07 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 122.7 ms, after 91.1 ms.

Load generator: CPU 13.3 % avg steady / 60.0 % peak (all vCPUs), k6 RSS 350 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 514.3 / 499.8
- `GET /me/posts`: 414.0 / 397.3
- `GET /posts`: 374.7 / 352.8
- `GET /posts/:id`: 406.3 / 381.7
- `GET /users/:id/posts`: 376.8 / 355.5
- `POST /posts`: 388.1 / 372.1
- `POST /posts/:id/comments`: 391.1 / 374.6
- `POST /posts/:id/like`: 363.1 / 340.3
