# node-express-v02-pool — 700 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 700 | PASS | 367.0 | 22020 | 33613 | 29.6 | 126.9 | 281.8 | 493.7 | 683 | 0 | 110 | 106 | 464 | 0 | 78.6 | 1.4 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 248.5
- `GET /me/posts`: 175.4
- `GET /posts`: 185.7
- `GET /posts/:id`: 211.7
- `GET /users/:id/posts`: 166.3
- `POST /posts`: 204.6
- `POST /posts/:id/comments`: 266.6
- `POST /posts/:id/like`: 246.3
