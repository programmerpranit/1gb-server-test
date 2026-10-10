# node-express-v05-prepared — 1000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v05-prepared | node-express | 1000 | PASS | 534.0 | 32038 | 48780 | 12.8 | 80.3 | 104.6 | 186.6 | 306 | 6.9 | 73.9 | 56.1 | 0 | 114 | 113 | 477 | 0 | 89.3 | 0.8 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 6.9 | 73.9 | 155.1 | 257.1 |
| conn | 0 | 56.1 | 135 | 234.3 |
| db | 6.4 | 26.1 | 43.9 | 210.8 |
| app | 0.2 | 0.5 | 1.8 | 8.7 |

Outside the app (client p − server total p): p50 5.9 ms, p95 30.7 ms. Responses without Server-Timing: 0.

CPU per request (steady): 1.67 ms. Host-speed probe (fixed workload, higher = slower vCPU): before - ms, after - ms.

Load generator: CPU 18.9 % avg steady / 60.6 % peak (all vCPUs), k6 RSS 553 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 118.0 / 84.0
- `GET /me/posts`: 99.9 / 69.7
- `GET /posts`: 105.9 / 72.1
- `GET /posts/:id`: 122.4 / 86.4
- `GET /users/:id/posts`: 103.0 / 70.8
- `POST /posts`: 108.4 / 76.3
- `POST /posts/:id/comments`: 104.4 / 76.9
- `POST /posts/:id/like`: 110.9 / 80.3
