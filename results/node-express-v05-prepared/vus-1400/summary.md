# node-express-v05-prepared — 1400 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v05-prepared | node-express | 1400 | PASS | 645.1 | 38707 | 61337 | 319.7 | 605.8 | 675.8 | 801.5 | 891 | 298 | 652.6 | 634.9 | 0 | 127 | 114 | 493 | 0 | 99.1 | 0.9 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 298 | 652.6 | 783.1 | 864.1 |
| conn | 281.6 | 634.9 | 767 | 841 |
| db | 12.1 | 30.3 | 49.5 | 164.2 |
| app | 0.2 | 0.5 | 1.9 | 43.8 |

Outside the app (client p − server total p): p50 21.7 ms, p95 23.2 ms. Responses without Server-Timing: 0.

CPU per request (steady): 1.54 ms. Host-speed probe (fixed workload, higher = slower vCPU): before - ms, after - ms.

Load generator: CPU 21.6 % avg steady / 63.2 % peak (all vCPUs), k6 RSS 748 MB peak.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 635.4 / 620.9
- `GET /me/posts`: 621.8 / 599.5
- `GET /posts`: 625.0 / 600.6
- `GET /posts/:id`: 639.8 / 618.0
- `GET /users/:id/posts`: 629.6 / 606.8
- `POST /posts`: 632.1 / 609.7
- `POST /posts/:id/comments`: 650.7 / 628.1
- `POST /posts/:id/like`: 620.0 / 596.8
