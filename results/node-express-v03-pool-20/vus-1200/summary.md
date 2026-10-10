# node-express-v03-pool-20 — 1200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v03-pool-20 | node-express | 1200 | PASS | 574.0 | 34443 | 53684 | 181.7 | 567.0 | 755.7 | 971.9 | 1108 | 146.8 | 706.6 | 655.8 | 0 | 120 | 138 | 513 | 0 | 98.8 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 146.8 | 706.6 | 929.5 | 1060.9 |
| conn | 113.3 | 655.8 | 884.8 | 981.4 |
| db | 21.5 | 85.1 | 134.4 | 253.3 |
| app | 0.2 | 1.6 | 3.3 | 11 |

Outside the app (client p − server total p): p50 34.9 ms, p95 49.1 ms. Responses without Server-Timing: 0.

Load generator: CPU 19.6 % avg steady / 64.6 % peak (all vCPUs), k6 RSS 646 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 836.4 / 801.6
- `GET /me/posts`: 591.2 / 538.0
- `GET /posts`: 621.5 / 581.4
- `GET /posts/:id`: 630.4 / 581.6
- `GET /users/:id/posts`: 624.6 / 587
- `POST /posts`: 677.5 / 614.1
- `POST /posts/:id/comments`: 706.5 / 663.5
- `POST /posts/:id/like`: 679.3 / 645.2
