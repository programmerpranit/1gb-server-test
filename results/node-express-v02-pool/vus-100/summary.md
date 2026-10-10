# node-express-v02-pool — 100 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 100 | PASS | 53.3 | 3196 | 4835 | 37.7 | 41.8 | 45.6 | 67.8 | 200 | 0 | 101 | 68 | 410 | 0 | 18.2 | 0.5 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 41.3
- `GET /me/posts`: 43.9
- `GET /posts`: 47.7
- `GET /posts/:id`: 46.0
- `GET /users/:id/posts`: 46.7
- `POST /posts`: 43.5
- `POST /posts/:id/comments`: 48.0
- `POST /posts/:id/like`: 45.8
