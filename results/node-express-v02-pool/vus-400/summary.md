# node-express-v02-pool — 400 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 400 | PASS | 209.4 | 12565 | 19031 | 40.3 | 163.2 | 284.4 | 446.7 | 644 | 0 | 107 | 100 | 454 | 0 | 50.9 | 0.9 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 347.3
- `GET /me/posts`: 292.1
- `GET /posts`: 268.6
- `GET /posts/:id`: 326.5
- `GET /users/:id/posts`: 294.7
- `POST /posts`: 297.4
- `POST /posts/:id/comments`: 354.4
- `POST /posts/:id/like`: 315.4
