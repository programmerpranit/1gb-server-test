# node-http-v02-bun — 4000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v02-bun | node-http | 4000 | PASS | 2081.6 | 124896 | 191899 | 14.2 | 280.3 | 436.2 | 823.3 | 976 | 1.9 | 420.7 | 367.7 | 0 | 101 | 131 | 489 | 0 | 93.6 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 1.9 | 420.7 | 803.0 | 916.1 |
| conn | 0 | 367.7 | 784.6 | 875 |
| db | 0.8 | 12.8 | 24.7 | 187.4 |
| app | 0 | 19 | 438.7 | 856.1 |

Outside the app (client p − server total p): p50 12.3 ms, p95 15.5 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.45 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 78.8 ms, after 105.0 ms.

Load generator: CPU 53.1 % avg steady / 100.0 % peak (all vCPUs), k6 RSS 2283 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 468.9 / 458.2
- `GET /me/posts`: 427.8 / 414.2
- `GET /posts`: 152.1 / 109.3
- `GET /posts/:id`: 428.7 / 415.2
- `GET /users/:id/posts`: 421.7 / 407.1
- `POST /posts`: 433.4 / 423.8
- `POST /posts/:id/comments`: 425.1 / 408.5
- `POST /posts/:id/like`: 420.3 / 404.1
