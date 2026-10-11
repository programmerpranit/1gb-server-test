# node-express-v06-feed-cache-1s — 2000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 2000 | PASS | 1079.1 | 64746 | 98287 | 3.7 | 26.8 | 48.5 | 95.9 | 154 | 0.8 | 25.5 | 7.9 | 0 | 127 | 115 | 501 | 0 | 78.7 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 0.8 | 25.5 | 66.9 | 112.8 |
| conn | 0 | 7.9 | 48.2 | 87.3 |
| db | 0.6 | 11.4 | 27.2 | 98.9 |
| app | 0.1 | 0.3 | 1.5 | 90.2 |

Outside the app (client p − server total p): p50 2.9 ms, p95 23.0 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.73 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 97.3 ms, after 114.7 ms.

Load generator: CPU 36.8 % avg steady / 95.8 % peak (all vCPUs), k6 RSS 1050 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 62.0 / 35.4
- `GET /me/posts`: 65.1 / 36.5
- `GET /posts`: 28.1 / 0.3
- `GET /posts/:id`: 75.5 / 48
- `GET /users/:id/posts`: 61.0 / 33.6
- `POST /posts`: 59.6 / 33.5
- `POST /posts/:id/comments`: 64.9 / 36.9
- `POST /posts/:id/like`: 62.7 / 35.8
