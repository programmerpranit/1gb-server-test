# node-http-v02-bun — 4500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v02-bun | node-http | 4500 | FAIL | 2097.4 | 125845 | 199838 | 247.4 | 744.3 | 901.9 | 1044.6 | 1547 | 217.3 | 883.6 | 861.2 | 0 | 113 | 136 | 499 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 902>=800ms, p99 1045>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 217.3 | 883.6 | 1019.6 | 1113 |
| conn | 59.7 | 861.2 | 1009.2 | 1094.6 |
| db | 3.8 | 15.4 | 29.2 | 210.2 |
| app | 0.2 | 463.7 | 789 | 976.3 |

Outside the app (client p − server total p): p50 30.1 ms, p95 18.3 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.48 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 83.1 ms, after 126.6 ms.

Load generator: CPU 50.2 % avg steady / 99.7 % peak (all vCPUs), k6 RSS 2559 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 915.6 / 891.6
- `GET /me/posts`: 923.7 / 902.2
- `GET /posts`: 590.3 / 550.6
- `GET /posts/:id`: 919.2 / 896.0
- `GET /users/:id/posts`: 916.1 / 893.7
- `POST /posts`: 927.3 / 903.0
- `POST /posts/:id/comments`: 936.4 / 909.8
- `POST /posts/:id/like`: 927.3 / 903.2
