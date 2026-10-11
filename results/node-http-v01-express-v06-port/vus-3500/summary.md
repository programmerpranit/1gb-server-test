# node-http-v01-express-v06-port — 3500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v01-express-v06-port | node-http | 3500 | FAIL | 1778.5 | 106711 | 165366 | 29.5 | 335.9 | 470.8 | 1175.4 | 1303 | 7 | 428.4 | 359.6 | 0 | 147 | 133 | 537 | 0 | 95.4 | 0.9 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p99 1175>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 7 | 428.4 | 1150.0 | 1274.5 |
| conn | 0 | 359.6 | 1136.4 | 1247.9 |
| db | 1.4 | 16.2 | 30.5 | 156.1 |
| app | 0.1 | 127.1 | 539.1 | 1173.9 |

Outside the app (client p − server total p): p50 22.5 ms, p95 42.4 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.54 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 82.9 ms, after 98.4 ms.

Load generator: CPU 48.3 % avg steady / 99.5 % peak (all vCPUs), k6 RSS 1923 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 476.3 / 447.4
- `GET /me/posts`: 417.5 / 402.7
- `GET /posts`: 228.5 / 198.2
- `GET /posts/:id`: 420.3 / 405.7
- `GET /users/:id/posts`: 414.6 / 398.6
- `POST /posts`: 414.5 / 400.4
- `POST /posts/:id/comments`: 422.1 / 403.5
- `POST /posts/:id/like`: 414.8 / 400.6
