# node-express-v01-baseline — 250 VUs

| Tag | Stack | VUs | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 250 | 57.4 | 3441 | 5869 | 2694.0 | 3500.0 | 3764.9 | 4298.2 | 4780 | 24.08 | 114 | 124 | 530 | 0 | 100.0 | 0.3 | macbook-home-wifi |

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 4359.8
- `GET /me/posts`: 3338.8
- `GET /posts`: 3383.8
- `GET /posts/:id`: 3558.8
- `GET /users/:id/posts`: 3352.9
- `POST /posts`: 3253.9
- `POST /posts/:id/comments`: 4173.5
- `POST /posts/:id/like`: 4122.1
