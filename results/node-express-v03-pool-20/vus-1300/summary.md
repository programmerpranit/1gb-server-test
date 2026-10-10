# node-express-v03-pool-20 — 1300 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v03-pool-20 | node-express | 1300 | FAIL | 562.6 | 33755 | 54136 | 414.0 | 936.4 | 1031.1 | 1114.0 | 1237 | 379 | 990.3 | 942.6 | 0 | 126 | 137 | 518 | 0 | 99.2 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1031>=800ms, p99 1114>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 379 | 990.3 | 1067.6 | 1213.4 |
| conn | 347.2 | 942.6 | 1024.4 | 1066.1 |
| db | 22.9 | 89.9 | 148.9 | 277.2 |
| app | 0.2 | 1.7 | 3.4 | 12.6 |

Outside the app (client p − server total p): p50 35.0 ms, p95 40.8 ms. Responses without Server-Timing: 0.

Load generator: CPU 19.3 % avg steady / 49.5 % peak (all vCPUs), k6 RSS 690 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1047.5 / 1014.5
- `GET /me/posts`: 955.2 / 913.4
- `GET /posts`: 957.0 / 917.1
- `GET /posts/:id`: 978.4 / 937.7
- `GET /users/:id/posts`: 962.7 / 920.2
- `POST /posts`: 951.9 / 902.9
- `POST /posts/:id/comments`: 1034.5 / 989.4
- `POST /posts/:id/like`: 1017.3 / 977.5
