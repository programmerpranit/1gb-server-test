# python-fastapi-v02-pool — 400 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v02-pool | python-fastapi | 400 | PASS | 211.9 | 12712 | 19417 | 17.8 | 127.9 | 199.2 | 384.4 | 1322 | 13.5 | 176.2 | 154.0 | 0 | 65 | 108 | 455 | 0 | 83.8 | 2.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 13.5 | 176.2 | 356.7 | 1305.9 |
| conn | 6.8 | 154.0 | 335.4 | 1286.3 |
| db | 5.5 | 27.1 | 45.6 | 120.7 |
| app | 0.9 | 2.4 | 4.1 | 62.2 |

Outside the app (client p − server total p): p50 4.3 ms, p95 23.0 ms. Responses without Server-Timing: 0.

CPU per request (steady): 3.96 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 95.3 ms, after 103.9 ms.

Load generator: CPU 11.9 % avg steady / 42.6 % peak (all vCPUs), k6 RSS 248 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 167.0 / 155.5
- `GET /me/posts`: 152.7 / 132.6
- `GET /posts`: 158.6 / 136.0
- `GET /posts/:id`: 159.2 / 131.8
- `GET /users/:id/posts`: 153.5 / 129.1
- `POST /posts`: 170.2 / 137.0
- `POST /posts/:id/comments`: 148.4 / 122.3
- `POST /posts/:id/like`: 148.2 / 130.1
