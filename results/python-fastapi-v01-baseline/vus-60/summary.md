# python-fastapi-v01-baseline — 60 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v01-baseline | python-fastapi | 60 | PASS | 29.9 | 1793 | 2752 | 115.2 | 364.8 | 490.0 | 618.8 | 713 | 109.1 | 456.5 | 364.8 | 0 | 53 | 46 | 397 | 0 | 86.9 | 0.1 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 109.1 | 456.5 | 587.7 | 682.6 |
| conn | 82 | 364.8 | 460.1 | 584.4 |
| db | 23.5 | 92.0 | 133.4 | 192.8 |
| app | 1.8 | 5.2 | 8 | 12 |

Outside the app (client p − server total p): p50 6.1 ms, p95 33.5 ms. Responses without Server-Timing: 0.

CPU per request (steady): 29.08 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 90.1 ms, after 83.9 ms.

Load generator: CPU 1.8 % avg steady / 7.8 % peak (all vCPUs), k6 RSS 73 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 414.4 / 393.1
- `GET /me/posts`: 504.3 / 471.6
- `GET /posts`: 405.2 / 380.4
- `GET /posts/:id`: 456.7 / 425.2
- `GET /users/:id/posts`: 369.5 / 350.1
- `POST /posts`: 437.2 / 409.2
- `POST /posts/:id/comments`: 399.6 / 374.2
- `POST /posts/:id/like`: 411.9 / 378.9
