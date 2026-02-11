# Faroe FW <30 Months Canary (5 batches) - 2026-02-11

## Scope
- Canary set of 5 Faroe FW station-contained batches (<30 months old).
- Per batch protocol: DB wipe + expected-site guard + semantic gates + counts.
- Execution profile: `--parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200 --skip-environmental`.

## Gate Summary
- PASS: `5/5`
- FAIL: `0/5`
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `0`

| batch | station | gate | non-bridge zero | bridge/entry | incomplete_linkage | direct_linkage | migrate_rc | semantic_rc | counts_rc |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Benchmark Gen. Mars 2025 | S24 Strond | PASS | 0 | 1/3 | 1 | 0 | 0 | 0 | 0 |
| Bakkafrost mai 24 | S16 Glyvradalur | PASS | 0 | 1/3 | 3 | 0 | 0 | 0 | 0 |
| StofnFiskur mars 2024 | S08 Gjógv | PASS | 0 | 1/2 | 2 | 0 | 0 | 0 | 0 |
| Stofnfiskur S-21 feb24 | S21 Viðareiði | PASS | 0 | 4/0 | 0 | 0 | 0 | 0 | 0 |
| Stofnfiskur Juni 24 | S03 Norðtoftir | PASS | 0 | 3/1 | 1 | 0 | 0 | 0 | 0 |
