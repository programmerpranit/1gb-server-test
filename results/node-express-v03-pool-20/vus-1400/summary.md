# node-express-v03-pool-20 — 1400 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v03-pool-20 | node-express | 1400 | FAIL | 604.3 | 36259 | 58260 | 407.5 | 788.5 | 897.3 | 1144.6 | 1279 | 374.6 | 856.8 | 815.9 | 0 | 130 | 139 | 525 | 0 | 100.0 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 897>=800ms, p99 1145>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 374.6 | 856.8 | 1099.9 | 1246.7 |
| conn | 342.2 | 815.9 | 1057.3 | 1109.9 |
| db | 21.1 | 82.8 | 135.5 | 260.3 |
| app | 0.2 | 1.6 | 3.3 | 9.6 |

Outside the app (client p − server total p): p50 32.9 ms, p95 40.5 ms. Responses without Server-Timing: 0.

Load generator: CPU 21.1 % avg steady / 47.6 % peak (all vCPUs), k6 RSS 750 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 961.6 / 919.2
- `GET /me/posts`: 865.2 / 814.0
- `GET /posts`: 875.1 / 831.2
- `GET /posts/:id`: 910.3 / 868.5
- `GET /users/:id/posts`: 876.8 / 837.8
- `POST /posts`: 862.6 / 824.5
- `POST /posts/:id/comments`: 976.7 / 937.9
- `POST /posts/:id/like`: 939.6 / 900.8
