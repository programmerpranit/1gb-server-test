# node-express-v03-pool-20 — 1500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v03-pool-20 | node-express | 1500 | FAIL | 524.5 | 31468 | 54877 | 909.1 | 1498.5 | 1935.5 | 2450.0 | 2648 | 874.9 | 1892.1 | 1832.1 | 0 | 136 | 155 | 542 | 0 | 100.0 | 0.5 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 909>=500ms, p95 1936>=800ms, p99 2450>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 874.9 | 1892.1 | 2393.7 | 2594.3 |
| conn | 836 | 1832.1 | 2336.7 | 2437.4 |
| db | 24.5 | 99.7 | 162.9 | 295.5 |
| app | 0.2 | 1.8 | 3.7 | 12.8 |

Outside the app (client p − server total p): p50 34.2 ms, p95 43.4 ms. Responses without Server-Timing: 0.

Load generator: CPU 17.8 % avg steady / 53.9 % peak (all vCPUs), k6 RSS 785 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1736.2 / 1694.7
- `GET /me/posts`: 1594.3 / 1560.4
- `GET /posts`: 1516.7 / 1468
- `GET /posts/:id`: 1576.2 / 1536.8
- `GET /users/:id/posts`: 1507.4 / 1466.7
- `POST /posts`: 1512.7 / 1461.9
- `POST /posts/:id/comments`: 1621.2 / 1584.4
- `POST /posts/:id/like`: 1606.1 / 1555.7
