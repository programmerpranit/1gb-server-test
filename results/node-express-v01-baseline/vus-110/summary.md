# node-express-v01-baseline — 110 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 110 | FAIL | 49.8 | 2986 | 4643 | 362.3 | 704.6 | 852.2 | 991.6 | 1096 | 337.2 | 783.8 | 665.6 | 0 | 104 | 64 | 432 | 0 | 98.4 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 852>=800ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 337.2 | 783.8 | 914.0 | 1051.3 |
| conn | 280.3 | 665.6 | 779.6 | 908.3 |
| db | 47.6 | 133.4 | 205.6 | 289 |
| app | 0.5 | 6.9 | 11.9 | 20.8 |

Outside the app (client p − server total p): p50 25.1 ms, p95 68.4 ms. Responses without Server-Timing: 0.

Load generator: CPU 2.9 % avg steady / 15.0 % peak (all vCPUs), k6 RSS 99 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 847.0 / 755.5
- `GET /me/posts`: 755.7 / 709.8
- `GET /posts`: 812.3 / 748.5
- `GET /posts/:id`: 834.3 / 780.1
- `GET /users/:id/posts`: 721.1 / 664.7
- `POST /posts`: 768.9 / 718.9
- `POST /posts/:id/comments`: 973.8 / 912.1
- `POST /posts/:id/like`: 904.5 / 843.8
