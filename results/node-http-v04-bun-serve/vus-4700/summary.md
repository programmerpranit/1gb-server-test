# node-http-v04-bun-serve — 4700 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v04-bun-serve | node-http | 4700 | FAIL | 2143.5 | 128609 | 204841 | 162.6 | 1001.0 | 1188.2 | 1546.8 | 1837 | 128.9 | 1157.9 | 1095.5 | 0 | 61 | 133 | 461 | 0 | 99.1 | 0.6 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1188>=800ms, p99 1547>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 128.9 | 1157.9 | 1483.7 | 1635.5 |
| conn | 0 | 1095.5 | 1390.6 | 1623.6 |
| db | 3.1 | 14.4 | 26.2 | 108.3 |
| app | 0.1 | 649.8 | 1139.7 | 1568.2 |

Outside the app (client p − server total p): p50 33.7 ms, p95 30.3 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.46 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 148.4 ms, after 95.2 ms.

Load generator: CPU 50.4 % avg steady / 99.8 % peak (all vCPUs), k6 RSS 2633 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1181.9 / 1170.3
- `GET /me/posts`: 1170.6 / 1149.8
- `GET /posts`: 860.0 / 799.7
- `GET /posts/:id`: 1183.7 / 1157.2
- `GET /users/:id/posts`: 1171.6 / 1147.5
- `POST /posts`: 1179.9 / 1157.3
- `POST /posts/:id/comments`: 1180.9 / 1148.9
- `POST /posts/:id/like`: 1178.3 / 1157.3
