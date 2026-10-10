# node-express-v05-prepared — 1300 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v05-prepared | node-express | 1300 | PASS | 633.1 | 37984 | 59537 | 199.9 | 367.6 | 445.2 | 812.9 | 914 | 176.7 | 422.1 | 405.4 | 0 | 119 | 113 | 483 | 0 | 99.3 | 0.7 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 176.7 | 422.1 | 779.8 | 891.9 |
| conn | 161.2 | 405.4 | 760.2 | 862 |
| db | 12.4 | 29.9 | 45.9 | 145.2 |
| app | 0.2 | 0.6 | 1.8 | 11.2 |

Outside the app (client p − server total p): p50 23.2 ms, p95 23.1 ms. Responses without Server-Timing: 0.

CPU per request (steady): 1.57 ms. Host-speed probe (fixed workload, higher = slower vCPU): before - ms, after - ms.

Load generator: CPU 21.4 % avg steady / 64.7 % peak (all vCPUs), k6 RSS 700 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 395.5 / 370.4
- `GET /me/posts`: 384.0 / 360.4
- `GET /posts`: 390.3 / 366.9
- `GET /posts/:id`: 407.9 / 384.5
- `GET /users/:id/posts`: 388.6 / 366.5
- `POST /posts`: 412.3 / 385.6
- `POST /posts/:id/comments`: 389.2 / 367.5
- `POST /posts/:id/like`: 398.9 / 373.6
