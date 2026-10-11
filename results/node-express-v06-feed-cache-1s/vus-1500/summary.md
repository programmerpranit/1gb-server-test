# node-express-v06-feed-cache-1s — 1500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 1500 | PASS | 810.1 | 48609 | 73764 | 3.2 | 18.8 | 32.8 | 62.3 | 132 | 0.8 | 13.2 | 0.1 | 0 | 121 | 114 | 497 | 0 | 72.5 | 1.5 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 0.8 | 13.2 | 34.3 | 87.4 |
| conn | 0 | 0.1 | 11.1 | 73.5 |
| db | 0.6 | 10.6 | 26.3 | 83.4 |
| app | 0.1 | 0.4 | 1.2 | 22.1 |

Outside the app (client p − server total p): p50 2.4 ms, p95 19.6 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.90 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 81.0 ms, after 82.8 ms.

Load generator: CPU 30.1 % avg steady / 60.0 % peak (all vCPUs), k6 RSS 815 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 47.2 / 22.2
- `GET /me/posts`: 49.0 / 21.9
- `GET /posts`: 28.7 / 0.4
- `GET /posts/:id`: 66.5 / 39.1
- `GET /users/:id/posts`: 49.8 / 23.3
- `POST /posts`: 53.6 / 27.1
- `POST /posts/:id/comments`: 54.8 / 29.1
- `POST /posts/:id/like`: 54.3 / 26.5
