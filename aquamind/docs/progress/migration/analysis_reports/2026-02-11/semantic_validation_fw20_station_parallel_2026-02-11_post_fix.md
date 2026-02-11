# FW 20-Batch Station Cohort (Parallel) Regression Report (2026-02-11 Post-Fix)

## Scope
- 20 recent station-contained FW/non-adult batches (S03/S08/S16/S21/S24).
- Per-batch isolation: DB wipe, station guard (`--expected-site`), semantic gates, counts.
- Migration execution profile: `--parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200 --skip-environmental`.
- Run start (UTC): `2026-02-11 10:49:08`

## Gate Summary
- PASS: `20/20`
- FAIL: `0/20`
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `0`

## Timing Summary
- Average migrate runtime: `108.8s`
- Average semantic runtime: `84.2s`
- Average counts runtime: `0.3s`

| batch | station | gate | non-bridge zero | zero transfer actions | bridge/entry | incomplete_linkage | direct_linkage | migrate_s | semantic_s | counts_s |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Bakkafrost S-21 jan 25 | S21 Viðareiði | PASS | 0 | 0 | 3/0 | 0 | 0 | 144.9 | 122.6 | 0.3 |
| StofnFiskur S-21 apr 25 | S21 Viðareiði | PASS | 0 | 0 | 1/2 | 1 | 0 | 116.6 | 103.5 | 0.3 |
| Benchmark Gen. Mars 2025 | S24 Strond | PASS | 0 | 0 | 1/3 | 1 | 0 | 191.3 | 164.2 | 0.3 |
| AquaGen Mars 25 | S03 Norðtoftir | PASS | 0 | 0 | 2/1 | 0 | 0 | 89.6 | 67.5 | 0.3 |
| Stofnfiskur sept 24 | S03 Norðtoftir | PASS | 0 | 0 | 4/0 | 0 | 0 | 108.1 | 70.5 | 0.3 |
| Bakkafrost S-21 okt 25 | S21 Viðareiði | PASS | 0 | 0 | 0/1 | 0 | 0 | 38.0 | 38.0 | 0.6 |
| Stofnfiskur mai 2025 | S16 Glyvradalur | PASS | 0 | 0 | 2/0 | 0 | 1 | 80.2 | 64.5 | 0.3 |
| Stofnfiskur feb 2025 | S16 Glyvradalur | PASS | 0 | 0 | 1/2 | 1 | 1 | 115.5 | 94.6 | 0.3 |
| Bakkafrost feb 2025 | S16 Glyvradalur | PASS | 0 | 0 | 2/1 | 0 | 1 | 89.7 | 76.9 | 0.3 |
| Benchmark Gen Septembur 2025 | S24 Strond | PASS | 0 | 0 | 0/1 | 0 | 0 | 63.6 | 61.8 | 0.3 |
| BF mars 2025 | S08 Gjógv | PASS | 0 | 0 | 2/1 | 1 | 0 | 167.0 | 129.6 | 0.3 |
| Benchmark Gen. Desembur 2024 | S24 Strond | PASS | 0 | 0 | 3/1 | 1 | 0 | 165.7 | 125.3 | 0.3 |
| StofnFiskur S-21 juli25 | S21 Viðareiði | PASS | 0 | 0 | 1/1 | 0 | 0 | 70.2 | 54.2 | 0.3 |
| Benchmark Gen. Septembur 2024 | S24 Strond | PASS | 0 | 0 | 4/0 | 0 | 0 | 133.2 | 90.0 | 0.3 |
| StofnFiskur okt. 2024 | S08 Gjógv | PASS | 0 | 0 | 2/2 | 2 | 0 | 159.7 | 86.5 | 0.3 |
| Stofnfiskur Des 24 | S03 Norðtoftir | PASS | 0 | 0 | 3/1 | 0 | 0 | 108.5 | 81.7 | 0.3 |
| Stofnfiskur Okt 25 | S03 Norðtoftir | PASS | 0 | 0 | 0/1 | 0 | 0 | 42.3 | 43.6 | 0.3 |
| BF oktober 2025 | S08 Gjógv | PASS | 0 | 0 | 0/1 | 0 | 0 | 39.1 | 43.0 | 0.3 |
| Stofnfiskur Aug 2024 | S16 Glyvradalur | PASS | 0 | 0 | 4/0 | 0 | 0 | 136.7 | 85.0 | 0.3 |
| Stofnfiskur Nov 2024 | S16 Glyvradalur | PASS | 0 | 0 | 0/4 | 3 | 0 | 116.1 | 81.1 | 0.3 |
