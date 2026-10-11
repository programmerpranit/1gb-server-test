# node-http-v01-express-v06-port — 3200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v01-express-v06-port | node-http | 3200 | PASS | 1677.6 | 100656 | 154434 | 10.9 | 196.9 | 392.4 | 835.3 | 990 | 1.6 | 361.6 | 262.6 | 0 | 144 | 133 | 523 | 0 | 92.4 | 0.6 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 1.6 | 361.6 | 789.8 | 977.1 |
| conn | 0 | 262.6 | 769.8 | 955.5 |
| db | 0.8 | 14.7 | 29.8 | 174.8 |
| app | 0 | 3.4 | 368.3 | 839.8 |

Outside the app (client p − server total p): p50 9.3 ms, p95 30.9 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.55 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 80.8 ms, after 90.7 ms.

Load generator: CPU 47.5 % avg steady / 99.0 % peak (all vCPUs), k6 RSS 1725 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 432.6 / 403.4
- `GET /me/posts`: 399.9 / 362.8
- `GET /posts`: 82.9 / 49.4
- `GET /posts/:id`: 382.3 / 354.0
- `GET /users/:id/posts`: 373.1 / 344.5
- `POST /posts`: 373.9 / 351.0
- `POST /posts/:id/comments`: 365.4 / 340.6
- `POST /posts/:id/like`: 365.2 / 338.4
