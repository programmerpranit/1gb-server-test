# node-express-v02-pool — 1200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1200 | PASS | 564.5 | 33867 | 52270 | 225.0 | 608.5 | 729.0 | 844.8 | 934 | 0 | 120 | 108 | 480 | 0 | 95.3 | 0.4 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 771.7
- `GET /me/posts`: 736.5
- `GET /posts`: 727.2
- `GET /posts/:id`: 746.6
- `GET /users/:id/posts`: 732.5
- `POST /posts`: 743.3
- `POST /posts/:id/comments`: 780.6
- `POST /posts/:id/like`: 763.9
