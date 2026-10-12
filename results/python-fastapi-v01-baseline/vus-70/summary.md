# python-fastapi-v01-baseline — 70 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v01-baseline | python-fastapi | 70 | FAIL | 32.2 | 1930 | 3005 | 213.2 | 734.7 | 1006.0 | 1182.4 | 1401 | 199.3 | 934.5 | 739.2 | 0 | 58 | 52 | 414 | 0 | 92.6 | 0.2 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1006>=800ms, p99 1182>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 199.3 | 934.5 | 1116.6 | 1351 |
| conn | 156.2 | 739.2 | 891.0 | 1012.5 |
| db | 39.3 | 181.2 | 237.9 | 426.8 |
| app | 1.7 | 5.5 | 8.1 | 11.5 |

Outside the app (client p − server total p): p50 13.9 ms, p95 71.5 ms. Responses without Server-Timing: 0.

CPU per request (steady): 28.78 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 86.1 ms, after 111.9 ms.

Load generator: CPU 2.0 % avg steady / 10.1 % peak (all vCPUs), k6 RSS 78 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 636.7 / 583.2
- `GET /me/posts`: 775.4 / 728.9
- `GET /posts`: 805.5 / 754.5
- `GET /posts/:id`: 971.9 / 902.1
- `GET /users/:id/posts`: 854.8 / 788.4
- `POST /posts`: 948.4 / 862.5
- `POST /posts/:id/comments`: 776.5 / 717.8
- `POST /posts/:id/like`: 856.4 / 782.0
