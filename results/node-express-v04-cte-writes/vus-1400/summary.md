# node-express-v04-cte-writes — 1400 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v04-cte-writes | node-express | 1400 | PASS | 660.5 | 39631 | 61864 | 192.8 | 671.6 | 787.7 | 990.5 | 1092 | 172.7 | 764.3 | 741.7 | 0 | 126 | 110 | 486 | 0 | 99.7 | 0.1 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 172.7 | 764.3 | 973.2 | 1074.5 |
| conn | 158.9 | 741.7 | 957.3 | 1043.9 |
| db | 11.9 | 29.9 | 45.8 | 134.2 |
| app | 0.2 | 0.4 | 2.1 | 11.7 |

Outside the app (client p − server total p): p50 20.1 ms, p95 23.3 ms. Responses without Server-Timing: 0.

Load generator: CPU 21.3 % avg steady / 49.7 % peak (all vCPUs), k6 RSS 746 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 763.4 / 742.8
- `GET /me/posts`: 721.6 / 681.0
- `GET /posts`: 732.2 / 697.6
- `GET /posts/:id`: 739.3 / 705.7
- `GET /users/:id/posts`: 741.6 / 709.7
- `POST /posts`: 716.1 / 677.6
- `POST /posts/:id/comments`: 756.3 / 727.7
- `POST /posts/:id/like`: 740.2 / 700.5
