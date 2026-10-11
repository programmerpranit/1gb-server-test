# node-express-v06-feed-cache-1s — 1000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 1000 | PASS | 543.0 | 32577 | 49477 | 2.0 | 5.4 | 8.4 | 24.0 | 90 | 0.7 | 4.3 | 0.1 | 0 | 113 | 111 | 472 | 0 | 52.8 | 0.5 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 0.7 | 4.3 | 12.1 | 70.6 |
| conn | 0 | 0.1 | 0.1 | 61.8 |
| db | 0.5 | 4.1 | 11.5 | 51.6 |
| app | 0.2 | 0.3 | 0.7 | 26.5 |

Outside the app (client p − server total p): p50 1.3 ms, p95 4.1 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.97 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 89.3 ms, after 87.6 ms.

Load generator: CPU 18.1 % avg steady / 34.2 % peak (all vCPUs), k6 RSS 555 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 11.8 / 6.7
- `GET /me/posts`: 7.7 / 4
- `GET /posts`: 4.9 / 0.3
- `GET /posts/:id`: 10.3 / 6.9
- `GET /users/:id/posts`: 8.7 / 4.6
- `POST /posts`: 10.5 / 6.7
- `POST /posts/:id/comments`: 13.0 / 8.2
- `POST /posts/:id/like`: 12.1 / 8.0
