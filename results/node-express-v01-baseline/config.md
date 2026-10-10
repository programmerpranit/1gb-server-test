# node-express-v01-baseline

## What changed vs. the previous tag
First tag. Baseline for the node-express stack.

## Full configuration
- App: `apps/node-express` — Express 5.3.0, pg 8.23.1, plain SQL, no ORM
- Runtime: Node v24.21.0, `NODE_ENV=production`, default heap, no flags
- App processes/workers: 1 (systemd `bench-app`, no cluster/pm2)
- DB connections: **no pool** — new `pg.Client` per request, closed before responding
- Writes: explicit `BEGIN/COMMIT` on the request's connection
- Postgres: 16.15, defaults (`shared_buffers=128MB`, `max_connections=100`), localhost TCP, SCRAM auth
- Swap: off
- Reverse proxy: none (Express directly on :3000)
- Load generator: MacBook on home Wi-Fi (`macbook-home-wifi`), k6 v2.3.0, ~40 ms RTT to the droplet

## Results
| VUs | Steady req/s | p50 ms | p95 ms | p99 ms | Error % | CPU % | App MB | PG MB | Used MB |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 44.4 | 332 | 824 | 1002 | 0.00 | 96.7 | 107 | 63 | 425 |
| 250 | 57.4 | 2694 | 3765 | 4298 | 24.08 | 100.0 | 114 | 124 | 530 |

Ladder stopped at 250 VUs (error rate > 1 %). **Capacity: below 100 VUs** — 100 VUs had no errors but steady p95
(824 ms) is above the 500 ms bar.

## Observations
- CPU-bound from 100 VUs: the single vCPU sits at ~97–100 %. Memory is not the limit (peak 530 MB used, 431 MB
  still available, no swap).
- At 250 VUs Postgres uses ~60 % of the CPU and Node ~27 %. Most of Postgres's work is per-request connection setup:
  forking a backend and SCRAM password authentication, before any query runs.
- Errors at 250 VUs are connection exhaustion: requests pile up (250 open client sockets), each holds its own
  Postgres connection, and new connects fail with `remaining connection slots are reserved for roles with the
  SUPERUSER attribute` / `sorry, too many clients already` (the app returns 500).
- Steal time ≈ 0.1–0.3 %, so a noisy neighbour is not a factor.
- Offered load is ~0.5 req/s per VU, so 100 VUs ≈ 50 req/s offered vs. 44 served: the box is already at its
  ceiling at 100 VUs in this configuration.

## Next idea
`node-express-v02-pool`: introduce `pg.Pool` with defaults (max 10). It removes per-request connect/auth cost and
caps Postgres connections well below `max_connections`.
