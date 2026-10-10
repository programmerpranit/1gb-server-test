# node-express-v01-baseline-r2 — 100 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline-r2 | node-express | 100 | FAIL | 43.7 | 2622 | 4100 | 460.6 | 792.8 | 889.5 | 1025.3 | 1132 | 0 | 106 | 66 | 487 | 0 | 97.9 | 0.3 | macbook-home-wifi |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 890>=800ms, p99 1025>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 792.5
- `GET /me/posts`: 811.6
- `GET /posts`: 838.1
- `GET /posts/:id`: 882.9
- `GET /users/:id/posts`: 806.9
- `POST /posts`: 857.6
- `POST /posts/:id/comments`: 995.7
- `POST /posts/:id/like`: 909.6
