# {{TAG}}

## Summary
<!-- Analysis written after the test: verdict (capacity + req/s), the bottleneck and the evidence for it
     (CPU split app/Postgres, memory, connections, error messages, steal), how it compares with the parent tag,
     and the recommended next experiment. -->

## What changed vs. the previous tag
<!-- ONE variable per tag. e.g. "pg Pool max 10 -> 20" -->

## Full configuration
- App: <!-- apps/<name>, framework + driver versions -->
- Runtime flags: <!-- e.g. NODE_ENV=production, --max-old-space-size -->
- App processes/workers: <!-- e.g. 1 -->
- DB pool size: <!-- -->
- Postgres settings changed from default: <!-- none -->
- Swap: <!-- off -->
- Reverse proxy: <!-- none -->
- Load generator: <!-- where k6 ran: region, size, network -->

## Results
<!-- One row per VU level tested, PASS/FAIL, capacity line. -->

## Observations
<!-- Detailed notes: where did it break? CPU-bound / memory / connection pool / OOM kill / swap thrash -->

## Next idea
<!-- -->
