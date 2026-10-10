# node-express-v02-pool — 1250 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v02-pool | node-express | 1250 | PASS | 575.6 | 34538 | 54611 | 308.8 | 495.0 | 634.4 | 839.7 | 1100 | 292.4 | 616.0 | 596.7 | 0 | 122 | 109 | 501 | 0 | 100.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 292.4 | 616.0 | 821.1 | 1064.2 |
| conn | 275.1 | 596.7 | 791.9 | 1032.6 |
| db | 11.9 | 42.4 | 64.2 | 164.9 |
| app | 0.2 | 1.6 | 3.1 | 12.3 |

Outside the app (client p − server total p): p50 16.4 ms, p95 18.4 ms. Responses without Server-Timing: 0.

Load generator: CPU 21.3 % avg steady / 52.7 % peak (all vCPUs), k6 RSS 669 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 613.1 / 596.5
- `GET /me/posts`: 656.5 / 642.8
- `GET /posts`: 643.3 / 626.9
- `GET /posts/:id`: 687.6 / 669.0
- `GET /users/:id/posts`: 655.1 / 632.7
- `POST /posts`: 626.8 / 608.3
- `POST /posts/:id/comments`: 774.0 / 754.3
- `POST /posts/:id/like`: 660.1 / 644.0
