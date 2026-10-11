# node-http-v02-bun — 4200 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-http-v02-bun | node-http | 4200 | PASS | 2077.8 | 124666 | 194707 | 46.7 | 589.2 | 752.4 | 850.6 | 1208 | 21.9 | 726.4 | 687.0 | 0 | 108 | 136 | 498 | 0 | 97.0 | 0.3 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 21.9 | 726.4 | 833.7 | 911.4 |
| conn | 0 | 687.0 | 821.8 | 897.9 |
| db | 1.4 | 14.3 | 28.1 | 112.5 |
| app | 0.1 | 317.3 | 683.4 | 847 |

Outside the app (client p − server total p): p50 24.8 ms, p95 26.0 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.47 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 77.8 ms, after 90.5 ms.

Load generator: CPU 51.7 % avg steady / 100.0 % peak (all vCPUs), k6 RSS 2409 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 760.7 / 735.7
- `GET /me/posts`: 759.3 / 737
- `GET /posts`: 469.2 / 436.9
- `GET /posts/:id`: 767.6 / 741.9
- `GET /users/:id/posts`: 750.6 / 726.4
- `POST /posts`: 754.2 / 732.0
- `POST /posts/:id/comments`: 764.5 / 743.6
- `POST /posts/:id/like`: 763.1 / 739.3
