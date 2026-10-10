# node-express-v01-baseline — 100 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v01-baseline | node-express | 100 | PASS | 46.7 | 2804 | 4368 | 242.4 | 548.9 | 742.4 | 958.8 | 1141 | 227.1 | 693.7 | 596.6 | 0 | 108 | 70 | 446 | 0 | 97.7 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 227.1 | 693.7 | 882.9 | 1097.2 |
| conn | 180.6 | 596.6 | 749.8 | 867.4 |
| db | 38.3 | 112.1 | 178.3 | 329 |
| app | 0.5 | 6.7 | 10.5 | 19.4 |

Outside the app (client p − server total p): p50 15.3 ms, p95 48.6 ms. Responses without Server-Timing: 0.

Load generator: CPU 2.6 % avg steady / 6.0 % peak (all vCPUs), k6 RSS 96 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 978.8 / 888.4
- `GET /me/posts`: 640.3 / 590.9
- `GET /posts`: 616.1 / 576.3
- `GET /posts/:id`: 688.8 / 636.2
- `GET /users/:id/posts`: 609.2 / 563.9
- `POST /posts`: 555.8 / 502.3
- `POST /posts/:id/comments`: 671.4 / 608.6
- `POST /posts/:id/like`: 636.7 / 595.0
