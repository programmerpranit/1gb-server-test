# node-express-v02-pool — 150 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 150 | PASS | 79.8 | 4791 | 7253 | 37.9 | 43.9 | 50.6 | 153.7 | 715 | 0 | 102 | 85 | 432 | 0 | 26.2 | 0.9 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 55.2
- `GET /me/posts`: 46.2
- `GET /posts`: 49.7
- `GET /posts/:id`: 52.9
- `GET /users/:id/posts`: 56.0
- `POST /posts`: 47.4
- `POST /posts/:id/comments`: 48.9
- `POST /posts/:id/like`: 63.3
