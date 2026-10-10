# node-express-v02-pool — 1250 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1250 | PASS | 627.3 | 37636 | 56981 | 77.3 | 366.0 | 447.3 | 680.3 | 818 | 0 | 118 | 109 | 479 | 0 | 92.5 | 0.1 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 491.8
- `GET /me/posts`: 467.1
- `GET /posts`: 465.6
- `GET /posts/:id`: 469.8
- `GET /users/:id/posts`: 470.9
- `POST /posts`: 475.6
- `POST /posts/:id/comments`: 500.0
- `POST /posts/:id/like`: 497.4
