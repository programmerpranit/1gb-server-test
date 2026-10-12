# python-fastapi-v02-pool — 650 VUs — FAIL

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python-fastapi-v02-pool | python-fastapi | 650 | FAIL | 297.8 | 17865 | 28604 | 168.7 | 813.5 | 1152.8 | 2015.9 | 4945 | 154.1 | 1130.5 | 1109.7 | 0 | 76 | 113 | 469 | 0 | 99.2 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %. Failed: p95 1153>=800ms, p99 2016>=1000ms.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 154.1 | 1130.5 | 1992.0 | 4931.5 |
| conn | 139.5 | 1109.7 | 1967.3 | 4915.4 |
| db | 12.9 | 28.9 | 48.8 | 167.3 |
| app | 0.8 | 2.2 | 3.9 | 90.3 |

Outside the app (client p − server total p): p50 14.6 ms, p95 22.3 ms. Responses without Server-Timing: 0.

CPU per request (steady): 3.33 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 85.2 ms, after 85.9 ms.

Load generator: CPU 12.1 % avg steady / 38.3 % peak (all vCPUs), k6 RSS 375 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 866.4 / 846.5
- `GET /me/posts`: 947.9 / 911.0
- `GET /posts`: 965.2 / 935.7
- `GET /posts/:id`: 958.9 / 936.7
- `GET /users/:id/posts`: 955.5 / 931.2
- `POST /posts`: 941.3 / 899.2
- `POST /posts/:id/comments`: 1009.3 / 989.1
- `POST /posts/:id/like`: 908.8 / 891.0
