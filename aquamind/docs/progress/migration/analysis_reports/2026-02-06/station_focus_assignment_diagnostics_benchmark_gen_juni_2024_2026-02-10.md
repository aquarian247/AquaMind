# Station-Focus Assignment Diagnostics

- Date: 2026-02-10
- Batch: `Benchmark Gen. Juni 2024` (`component_key=5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`)
- Station guard: `S24 Strond`
- DB: `aquamind_db_migr_dev`

## Purpose
Validate container-assignment realism for the station/pre-adult single-batch hardening pass, focusing on:
- implied average-weight outliers from `biomass_kg / population_count`,
- active assignment eligibility,
- growth sample date span.

## Query basis
Diagnostics were computed from `batch_batchcontainerassignment` + `batch_growthsample` after clean replay.

## Before -> After summary

| Metric | Before hardening | After hardening |
| --- | ---: | ---: |
| Active assignments (`Post-Smolt`) | 14 | 13 |
| Active total population | 419,035 | 1,619,290 |
| Active total biomass (kg) | 479,362.84 | 337,654.90 |
| Active implied avg-weight min (g) | 181.13 | 125.18 |
| Active implied avg-weight max (g) | 20,178.14 | 300.10 |
| High-weight low-count outliers (`implied_weight >= 1000g` and `count <= 5000`) | 11 | 0 |
| Growth sample rows | 607 | 607 |
| Growth sample date range | 2024-09-05 to 2025-10-23 | 2024-09-05 to 2025-10-23 |

## Interpretation
- Hardening removed the extreme active container weight artifacts (8kg–20kg implied range) by enforcing count/biomass consistency and non-zero latest-status active gating.
- The "600+ weeks" chart concern is not supported by migrated growth sample dates; data spans ~13 months.
- Lifecycle stage full-summed population counts remain unchanged by this pass; transition basis remains entry-window fallback (`incomplete_linkage`).
