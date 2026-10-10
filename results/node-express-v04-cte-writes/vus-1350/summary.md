# node-express-v04-cte-writes — 1350 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v04-cte-writes | node-express | 1350 | FAIL | 569.0 | 34139 | 54435 | 510.8 | 766.3 | 847.1 | 952.8 | 1018 | 488.8 | 819.5 | 802.5 | 0 | 126 | 127 | 506 | 0 | 100.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 511>=500ms, p95 847>=800ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 488.8 | 819.5 | 926.1 | 1000.7 |
| conn | 471.5 | 802.5 | 903.7 | 980 |
| db | 14.4 | 34.4 | 52.7 | 112.4 |
| app | 0.2 | 0.9 | 2.4 | 6.8 |

Outside the app (client p − server total p): p50 22.0 ms, p95 27.6 ms. Responses without Server-Timing: 0.

Load generator: CPU 18.9 % avg steady / 65.1 % peak (all vCPUs), k6 RSS 714 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 819.4 / 784.4
- `GET /me/posts`: 778.0 / 748.6
- `GET /posts`: 794.8 / 766.0
- `GET /posts/:id`: 800.3 / 771.9
- `GET /users/:id/posts`: 795.9 / 765.4
- `POST /posts`: 783.6 / 750.8
- `POST /posts/:id/comments`: 796.9 / 762.9
- `POST /posts/:id/like`: 793.3 / 767.1
