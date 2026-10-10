# node-express-v01-baseline-r2 — 50 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline-r2 | node-express | 50 | PASS | 26.4 | 1584 | 2390 | 49.9 | 95.4 | 117.6 | 171.3 | 212 | 0 | 103 | 42 | 399 | 0 | 52.0 | 0.1 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 109.5
- `GET /me/posts`: 105.7
- `GET /posts`: 125.3
- `GET /posts/:id`: 112.1
- `GET /users/:id/posts`: 122.7
- `POST /posts`: 101.9
- `POST /posts/:id/comments`: 125.4
- `POST /posts/:id/like`: 121.9
