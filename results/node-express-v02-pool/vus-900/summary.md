# node-express-v02-pool — 900 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 900 | PASS | 461.0 | 27660 | 42235 | 66.3 | 259.4 | 318.4 | 457.7 | 746 | 0 | 113 | 108 | 472 | 0 | 91.3 | 0.6 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 318.2
- `GET /me/posts`: 299.4
- `GET /posts`: 298.7
- `GET /posts/:id`: 311.4
- `GET /users/:id/posts`: 295.6
- `POST /posts`: 299.7
- `POST /posts/:id/comments`: 317.5
- `POST /posts/:id/like`: 334.6
