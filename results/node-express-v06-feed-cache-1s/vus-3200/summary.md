# node-express-v06-feed-cache-1s — 3200 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 3200 | FAIL | 1604.2 | 96250 | 149284 | 42.4 | 388.4 | 725.1 | 1640.9 | 1775 | 19.2 | 709.8 | 481.8 | 0 | 161 | 131 | 548 | 0 | 98.7 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p99 1641>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 19.2 | 709.8 | 1589.6 | 1723.8 |
| conn | 0 | 481.8 | 1460.3 | 1709.8 |
| db | 2.5 | 18.4 | 36.7 | 192 |
| app | 0.1 | 120.5 | 742.1 | 1648.6 |

Outside the app (client p − server total p): p50 23.2 ms, p95 15.3 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.62 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 92.0 ms, after 82.9 ms.

Load generator: CPU 40.3 % avg steady / 97.0 % peak (all vCPUs), k6 RSS 1729 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 728.6 / 710.4
- `GET /me/posts`: 649.3 / 625
- `GET /posts`: 243.5 / 218.7
- `GET /posts/:id`: 673.3 / 660.7
- `GET /users/:id/posts`: 654.6 / 634.4
- `POST /posts`: 642.7 / 590.7
- `POST /posts/:id/comments`: 645.5 / 622.9
- `POST /posts/:id/like`: 592.9 / 564.4
