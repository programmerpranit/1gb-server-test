# node-express-v06-feed-cache-1s — 3000 VUs — PASS

| Tag | Stack | VUs | Pass | Steady req/s | Steady req/min | Total req | p50 ms | p90 ms | p95 ms | p99 ms | Max ms | Srv p50 ms | Srv p95 ms | Conn p95 ms | Error % | App MB (peak) | PG MB (peak) | Used MB (peak) | Swap MB | CPU % (avg steady) | Steal % | Load from |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node-express-v06-feed-cache-1s | node-express | 3000 | PASS | 1541.0 | 92462 | 141899 | 29.4 | 342.6 | 573.0 | 854.6 | 966 | 7.6 | 551.7 | 451.8 | 0 | 156 | 130 | 541 | 0 | 98.0 | 0.4 | do-blr1-loadgen-4vcpu-8gb |

Criteria: steady p50 < 500 ms, p95 < 800 ms, p99 < 1000 ms, errors < 1 %.

Latency columns are steady-state (hold phase). Error % covers the whole run.

## Server timing (steady phase, ms, from Server-Timing)

| Part | p50 | p95 | p99 | max |
|---|---|---|---|---|
| total | 7.6 | 551.7 | 832.5 | 914.1 |
| conn | 0 | 451.8 | 819.4 | 891.6 |
| db | 1.9 | 19 | 37.0 | 176.9 |
| app | 0.1 | 74.3 | 541.7 | 817 |

Outside the app (client p − server total p): p50 21.8 ms, p95 21.3 ms. Responses without Server-Timing: 0.

CPU per request (steady): 0.64 ms. Host-speed probe (fixed workload, higher = slower vCPU): before 88.3 ms, after 83.5 ms.

Load generator: CPU 40.0 % avg steady / 97.8 % peak (all vCPUs), k6 RSS 1593 MB peak — WARNING: load generator above 70 % CPU, k6 may be the bottleneck.

## p95 by endpoint (ms, whole run: client / server total)

- `DELETE /posts/:id/like`: 625.5 / 607.1
- `GET /me/posts`: 586.8 / 559.1
- `GET /posts`: 228.0 / 204.2
- `GET /posts/:id`: 595.1 / 572.4
- `GET /users/:id/posts`: 587.6 / 567.7
- `POST /posts`: 581.0 / 561.8
- `POST /posts/:id/comments`: 590.3 / 568.1
- `POST /posts/:id/like`: 585.4 / 563.3
