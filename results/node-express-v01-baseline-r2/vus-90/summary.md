# node-express-v01-baseline-r2 — 90 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline-r2 | node-express | 90 | PASS | 42.8 | 2569 | 3974 | 234.4 | 550.9 | 658.5 | 979.8 | 1177 | 0 | 103 | 59 | 428 | 0 | 94.1 | 0.3 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 602.5
- `GET /me/posts`: 615.3
- `GET /posts`: 563.4
- `GET /posts/:id`: 599.3
- `GET /users/:id/posts`: 591.1
- `POST /posts`: 570.2
- `POST /posts/:id/comments`: 701.2
- `POST /posts/:id/like`: 645.9
