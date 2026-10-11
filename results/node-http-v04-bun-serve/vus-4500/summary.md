# node-http-v04-bun-serve — 4500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v04-bun-serve | node-http | 4500 | PASS | 2324.2 | 139452 | 214994 | 14.8 | 174.4 | 319.2 | 911.5 | 1485 | 1.5 | 270.7 | 193.5 | 0 | 59 | 133 | 464 | 0 | 94.1 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 1.5 | 270.7 | 766.7 | 975.4 |
| conn | 0 | 193.5 | 741.6 | 965 |
| db | 0.8 | 11.3 | 20.8 | 101.7 |
| app | 0 | 0.3 | 243.9 | 918.5 |

Outside the app (client p − server total p): p50 13.3 ms, p95 48.5 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.40 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 82.0 ms, after 95.8 ms.

Load generator: CPU 57.6 % avg steady / 100.0 % peak (all vCPUs), k6 RSS 2599 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 316.4 / 287.1
- `GET /me/posts`: 307.8 / 269.8
- `GET /posts`: 123.4 / 16.2
- `GET /posts/:id`: 306.8 / 269.6
- `GET /users/:id/posts`: 313.4 / 274.9
- `POST /posts`: 318.0 / 279.2
- `POST /posts/:id/comments`: 291.3 / 249.0
- `POST /posts/:id/like`: 301.4 / 261.6
