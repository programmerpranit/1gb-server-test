# python-fastapi-v01-baseline — 100 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v01-baseline | python-fastapi | 100 | FAIL | 35.8 | 2146 | 3601 | 954.8 | 1475.6 | 1721.6 | 1969.3 | 2220 | 885.9 | 1606.9 | 1273.2 | 0 | 65 | 71 | 449 | 0 | 100.0 | 0.1 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p50 955>=500ms, p95 1722>=800ms, p99 1969>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 885.9 | 1606.9 | 1850.4 | 2120.2 |
| conn | 713.6 | 1273.2 | 1456.5 | 1590.9 |
| db | 155.6 | 346.2 | 499.9 | 670.3 |
| app | 1.4 | 6 | 9.7 | 39.7 |

Outside the app (client p − server total p): p50 68.9 ms, p95 114.7 ms. Responses without Server-Timing: 0.

CPU per request (steady): 27.95 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 80.1 ms, after 87.6 ms.

Load generator: CPU 2.3 % avg steady / 9.0 % peak (all vCPUs), k6 RSS 93 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 1749.6 / 1590.6
- `GET /me/posts`: 1470.8 / 1376.2
- `GET /posts`: 1522.2 / 1407.7
- `GET /posts/:id`: 1786.9 / 1658.4
- `GET /users/:id/posts`: 1415.6 / 1287.2
- `POST /posts`: 1526.3 / 1398.0
- `POST /posts/:id/comments`: 1477.8 / 1369.9
- `POST /posts/:id/like`: 1450.4 / 1336.6
