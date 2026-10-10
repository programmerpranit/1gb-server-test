# node-express-v02-pool — 1500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1500 | FAIL | 598.9 | 35931 | 58626 | 666.7 | 1013.3 | 1142.9 | 1263.4 | 1378 | 0 | 134 | 109 | 497 | 0 | 100.0 | 0.2 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 667>=500ms, p95 1143>=800ms, p99 1263>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 1121.3
- `GET /me/posts`: 1111.7
- `GET /posts`: 1101.6
- `GET /posts/:id`: 1107.1
- `GET /users/:id/posts`: 1100.4
- `POST /posts`: 1101.2
- `POST /posts/:id/comments`: 1133.0
- `POST /posts/:id/like`: 1133.9
