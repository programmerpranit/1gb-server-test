# node-express-v06-feed-cache-1s — 2500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 2500 | PASS | 1324.8 | 79488 | 121159 | 12.4 | 112.7 | 192.3 | 435.9 | 496 | 1.4 | 165.6 | 126.6 | 0 | 132 | 116 | 515 | 0 | 91.9 | 0.7 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 1.4 | 165.6 | 406.4 | 481.6 |
| conn | 0 | 126.6 | 391.4 | 457.5 |
| db | 0.9 | 18.3 | 35.9 | 157.1 |
| app | 0.1 | 0.4 | 115.4 | 433.2 |

Outside the app (client p − server total p): p50 11.0 ms, p95 26.7 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.69 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 116.1 ms, after 101.1 ms.

Load generator: CPU 39.1 % avg steady / 95.7 % peak (all vCPUs), k6 RSS 1333 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 310.1 / 270.9
- `GET /me/posts`: 271.1 / 247.8
- `GET /posts`: 53.1 / 1.2
- `GET /posts/:id`: 300.4 / 268.4
- `GET /users/:id/posts`: 279.2 / 252.4
- `POST /posts`: 304.8 / 274.4
- `POST /posts/:id/comments`: 294.1 / 263.7
- `POST /posts/:id/like`: 284.8 / 254.5
