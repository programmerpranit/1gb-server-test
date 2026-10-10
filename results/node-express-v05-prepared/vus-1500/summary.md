# node-express-v05-prepared — 1500 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v05-prepared | node-express | 1500 | FAIL | 687.6 | 41254 | 65030 | 318.0 | 598.9 | 730.9 | 1168.2 | 1271 | 297.1 | 710.6 | 693.0 | 0 | 130 | 114 | 497 | 0 | 99.8 | 0.5 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p99 1168>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 297.1 | 710.6 | 1134.9 | 1256.1 |
| conn | 282.9 | 693.0 | 1117.7 | 1229.4 |
| db | 11.8 | 28.9 | 44.7 | 137.6 |
| app | 0.2 | 0.5 | 1.8 | 15 |

Outside the app (client p − server total p): p50 20.9 ms, p95 20.2 ms. Responses without Server-Timing: 0.

CPU per request (steady): 1.45 ms. Host-speed probe (fixed workload, higher = slower vCPU): before - ms, after - ms.

Load generator: CPU 21.7 % avg steady / 49.8 % peak (all vCPUs), k6 RSS 787 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 684.7 / 661.8
- `GET /me/posts`: 679.3 / 658.3
- `GET /posts`: 690.8 / 666
- `GET /posts/:id`: 681.3 / 653.3
- `GET /users/:id/posts`: 713.1 / 684.5
- `POST /posts`: 680.0 / 653.2
- `POST /posts/:id/comments`: 665.6 / 639.9
- `POST /posts/:id/like`: 701.8 / 678.5
