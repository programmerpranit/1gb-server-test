# node-express-v02-pool — 500 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 500 | PASS | 263.1 | 15785 | 23975 | 30.1 | 127.2 | 233.1 | 519.7 | 1900 | 0 | 109 | 103 | 458 | 0 | 57.8 | 0.3 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 261.1
- `GET /me/posts`: 198.2
- `GET /posts`: 211.0
- `GET /posts/:id`: 249.5
- `GET /users/:id/posts`: 209.0
- `POST /posts`: 202.6
- `POST /posts/:id/comments`: 320.8
- `POST /posts/:id/like`: 246.2
