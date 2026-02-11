# FW 20-Batch Station Cohort (Parallel) Regression Report (2026-02-11)

## Scope
- 20 recent station-contained FW/non-adult batches (S03/S08/S16/S21/S24).
- Per-batch isolation: DB wipe, station guard (`--expected-site`), semantic gates, counts.
- Migration execution profile: `--parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200 --skip-environmental`.

## Gate Summary
- PASS: `17/20`
- FAIL: `3/20`
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `2`

## Timing Summary
- Average migrate runtime: `107.9s`
- Average semantic runtime: `78.6s`
- Average counts runtime: `0.4s`

| batch | station | gate | non-bridge zero | zero transfer actions | bridge/entry | incomplete_linkage | migrate_s | semantic_s | counts_s |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Bakkafrost S-21 jan 25 | S21 Viðareiði | PASS | 0 | 0 | 3/0 | 0 | 148.8 | 122.0 | 0.4 |
| StofnFiskur S-21 apr 25 | S21 Viðareiði | PASS | 0 | 0 | 1/2 | 1 | 119.2 | 104.1 | 0.4 |
| Benchmark Gen. Mars 2025 | S24 Strond | PASS | 0 | 0 | 1/3 | 1 | 197.6 | 164.1 | 0.4 |
| AquaGen Mars 25 | S03 Norðtoftir | PASS | 0 | 0 | 2/1 | 0 | 90.4 | 69.6 | 0.4 |
| Stofnfiskur sept 24 | S03 Norðtoftir | PASS | 0 | 0 | 4/0 | 0 | 113.6 | 74.4 | 0.4 |
| Bakkafrost S-21 okt 25 | S21 Viðareiði | PASS | 0 | 0 | 0/1 | 0 | 38.8 | 39.0 | 0.4 |
| Stofnfiskur mai 2025 | S16 Glyvradalur | FAIL | 0 | 0 | 1/1 | 0 | 81.3 | 65.1 | 0.4 |
| Stofnfiskur feb 2025 | S16 Glyvradalur | FAIL | 0 | 0 | 0/3 | 1 | 118.7 | 95.5 | 0.4 |
| Bakkafrost feb 2025 | S16 Glyvradalur | PASS | 0 | 0 | 1/2 | 0 | 92.6 | 78.4 | 0.4 |
| Benchmark Gen Septembur 2025 | S24 Strond | PASS | 0 | 0 | 0/1 | 0 | 65.5 | 62.7 | 0.4 |
| BF mars 2025 | S08 Gjógv | FAIL | 0 | 0 | 0/0 | 0 | 112.5 | 0.0 | 0.3 |
| Benchmark Gen. Desembur 2024 | S24 Strond | PASS | 0 | 0 | 3/1 | 1 | 166.9 | 122.3 | 0.4 |
| StofnFiskur S-21 juli25 | S21 Viðareiði | PASS | 0 | 0 | 1/1 | 0 | 71.2 | 56.1 | 0.4 |
| Benchmark Gen. Septembur 2024 | S24 Strond | PASS | 0 | 0 | 4/0 | 0 | 135.7 | 92.8 | 0.4 |
| StofnFiskur okt. 2024 | S08 Gjógv | PASS | 0 | 0 | 2/2 | 2 | 157.8 | 89.4 | 0.4 |
| Stofnfiskur Des 24 | S03 Norðtoftir | PASS | 0 | 0 | 3/1 | 0 | 109.3 | 80.5 | 0.4 |
| Stofnfiskur Okt 25 | S03 Norðtoftir | PASS | 0 | 0 | 0/1 | 0 | 42.3 | 43.9 | 0.4 |
| BF oktober 2025 | S08 Gjógv | PASS | 0 | 0 | 0/1 | 0 | 39.8 | 43.5 | 0.4 |
| Stofnfiskur Aug 2024 | S16 Glyvradalur | PASS | 0 | 0 | 4/0 | 0 | 137.6 | 89.3 | 0.4 |
| Stofnfiskur Nov 2024 | S16 Glyvradalur | PASS | 0 | 0 | 0/4 | 3 | 118.4 | 79.6 | 0.4 |
