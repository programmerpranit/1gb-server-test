# node-express-v01-baseline — 100 VUs

| Tag | Stack | VUs | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 100 | 44.4 | 2666 | 4207 | 331.8 | 703.6 | 824.4 | 1001.7 | 1138 | 0 | 107 | 63 | 425 | 0 | 96.7 | 0.1 | macbook-home-wifi |

Latency columns are steady-state (hold phase). Error % covers the whole run.

## p95 by endpoint (ms, whole run)

- `DELETE /posts/:id/like`: 908.9
- `GET /me/posts`: 697.6
- `GET /posts`: 730.7
- `GET /posts/:id`: 761.1
- `GET /users/:id/posts`: 698.6
- `POST /posts`: 652.4
- `POST /posts/:id/comments`: 804.7
- `POST /posts/:id/like`: 931.3
