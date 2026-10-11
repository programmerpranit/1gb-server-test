# node-http-v03-bun-sql — 4500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v03-bun-sql | node-http | 4500 | FAIL | 1954.7 | 117280 | 189837 | 416.9 | 956.9 | 1087.9 | 1546.8 | 1785 | 397.7 | 1060 | 998.8 | 0 | 109 | 132 | 500 | 0 | 99.8 | 0.7 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1088>=800ms, p99 1547>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 397.7 | 1060 | 1502.1 | 1772 |
| conn | 95.5 | 998.8 | 1463.6 | 1747.3 |
| db | 4 | 17 | 31.8 | 197.3 |
| app | 0.1 | 742.8 | 1084.2 | 1657.8 |

Outside the app (client p − server total p): p50 19.2 ms, p95 27.9 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.51 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 108.2 ms, after 91.5 ms.

Load generator: CPU 48.1 % avg steady / 100.0 % peak (all vCPUs), k6 RSS 2490 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1098.6 / 1065.0
- `GET /me/posts`: 1067.2 / 1031.7
- `GET /posts`: 836.0 / 808.6
- `GET /posts/:id`: 1072.3 / 1037.3
- `GET /users/:id/posts`: 1068.9 / 1033
- `POST /posts`: 1063.6 / 1030.0
- `POST /posts/:id/comments`: 1079.1 / 1053.0
- `POST /posts/:id/like`: 1065.5 / 1027.7
