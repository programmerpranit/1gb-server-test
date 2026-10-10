# node-express-v01-baseline-r2 — 75 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline-r2 | node-express | 75 | PASS | 39.1 | 2345 | 3536 | 80.7 | 164.5 | 202.1 | 261.2 | 323 | 0 | 106 | 41 | 409 | 0 | 78.2 | 0.1 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 230.3
- `GET /me/posts`: 187.1
- `GET /posts`: 178.4
- `GET /posts/:id`: 186.2
- `GET /users/:id/posts`: 176.1
- `POST /posts`: 173.1
- `POST /posts/:id/comments`: 160.6
- `POST /posts/:id/like`: 195.5
