# node-express-v02-pool — 200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 200 | PASS | 106.3 | 6378 | 9678 | 37.8 | 44.2 | 55.3 | 287.5 | 737 | 0 | 104 | 89 | 443 | 0 | 30.5 | 0.6 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 67.5
- `GET /me/posts`: 47.6
- `GET /posts`: 49.2
- `GET /posts/:id`: 49.7
- `GET /users/:id/posts`: 47.9
- `POST /posts`: 58.6
- `POST /posts/:id/comments`: 55.3
- `POST /posts/:id/like`: 50.7
