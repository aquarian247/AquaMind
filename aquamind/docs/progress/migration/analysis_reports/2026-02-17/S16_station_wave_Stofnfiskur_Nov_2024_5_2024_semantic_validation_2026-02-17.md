# Semantic Migration Validation Report

- Component key: `94B7E42D-16B1-4CD8-A361-1E99D04E8612`
- Batch: `Stofnfiskur Nov 2024` (id=525)
- Populations: 138
- Window: 2024-11-20 14:02:24 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 15:56:44.306392, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1033 | 1033 | 0.00 |
| Feeding kg | 92044.92 | 92044.92 | 0.00 |
| Mortality events | 3022 | 2652 | 370.00 |
| Mortality count | 513904 | 513904 | 0.00 |
| Mortality biomass kg | 0.00 | 2379.46 | -2379.46 |
| Culling events | 4 | 4 | 0.00 |
| Culling count | 141370 | 141370 | 0.00 |
| Culling biomass kg | 2095435.00 | 2095435.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 12 | 12 | 0.00 |
| Growth samples | 10 | 10 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 655274
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/4 bridge-aware (25.0%), 3/4 entry-window (75.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 4 total, 3 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 53.
- Fishgroup classification: 56 temporary bridge fishgroups, 26 real stage-entry fishgroups, 56 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1800784 | 0 | 1800784 | 1800784 | 1.0 | 1.0 | 2024-11-20 | 2024-11-22 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1577400 | 0 | 1577400 | 1577400 | 1.0 | 1.0 | 2025-02-06 | 2025-02-08 | 8 | 8 | 0 | 8 | 8 |
| Parr | 1169897 | 0 | 1922577 | 11315328 | 9.67 | 5.89 | 2025-05-05 | 2025-05-07 | 8 | 8 | 5 | 96 | 98 |
| Smolt | 306993 | 0 | 1279569 | 3597270 | 11.72 | 2.81 | 2025-09-06 | 2025-09-08 | 1 | 1 | 5 | 19 | 21 |
| Post-Smolt | 553222 | 822595 | 822595 | 822595 | 1.49 | 1.0 | 2025-11-24 | 2025-11-26 | 4 | 4 | 0 | 6 | 6 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1800784 | 1577400 | -223384 | 8 | 7 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1577400 | 1169897 | -407503 | 8 | 7 | no | Entry window (incomplete linkage) | OK |
| Parr -> Smolt | 1169897 | 306993 | -862904 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 207630 |
| Smolt -> Post-Smolt | 258072 | 243936 | -14136 | 4 | 4 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `245.0014`, `245.0015`, `245.0017`, `245.0023`, `245.0024`, `245.0027`, `245.0036`, `245.0039`, `245.0040`, `245.0041`
- Real stage-entry fishgroup examples: `245.0001`, `245.0002`, `245.0003`, `245.0004`, `245.0005`, `245.0006`, `245.0007`, `245.0008`, `245.0009`, `245.0010`
- Bridge fishgroups excluded from stage-entry windows: `245.0014`, `245.0015`, `245.0017`, `245.0023`, `245.0024`, `245.0071`, `245.0073`, `245.0076`, `245.0080`, `245.0083`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 138 | 138 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 222572 |
| Parr | 66825 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `837D3C86-17D7-407F-952D-996CAAD15322` | Fry | 222572 | 222572 |
| `8DECE7C7-6748-4CDF-8AE9-5C898C33625C` | Parr | 66825 | 66825 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 87520 |
| Fry | 131097 |
| Parr | 95 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 64

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 11 | Hatchery:11 | S16 Glyvradalur:11 |
| SourcePopBefore -> SourcePopAfter | 48 | Hatchery:48 | S16 Glyvradalur:48 |
| DestPopBefore -> DestPopAfter | 8 | Hatchery:8 | S16 Glyvradalur:8 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 64 | 0 | Hatchery:64 | S16 Glyvradalur:64 | Unknown:64 |
| Reachable outside descendants | 86 | 0 | Hatchery:86 | S16 Glyvradalur:86 | Unknown:86 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E01 | A8588434-EC8A-48D5-A7BB-9CB1AE614928 | `AEA651EB-6D5F-4FB3-8D71-FD1A7629BDB2` | `AEA651EB-6D5F-4FB3-8D71-FD1A7629BDB2` | yes | 147723 | 37759.6 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| E02 | FC172B8F-B999-468E-A079-A0E9380D1E13 | `8E98343E-C4E8-4463-B380-DF7B1619E565` | `8E98343E-C4E8-4463-B380-DF7B1619E565` | yes | 110733 | 54596.7 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| E03 | A8D42A0F-9BDE-4EF9-BFE9-B2A6FED2F91B | `C2D3BF51-6C87-4701-A1FB-7032118D1E0A` | `C2D3BF51-6C87-4701-A1FB-7032118D1E0A` | yes | 149057 | 44080.3 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| E04 | 3783BBEC-FBF4-4894-9C26-18D02559FB87 | `EFB862C2-7DF5-477B-A1CF-57AF5AB8AB72` | `EFB862C2-7DF5-477B-A1CF-57AF5AB8AB72` | yes | 145709 | 68011.7 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| E05 | 4CE72C8A-9115-4EFF-AE82-88CEBF27C4D3 | `283B5243-5993-4A6C-AC66-F0388009891D` | `283B5243-5993-4A6C-AC66-F0388009891D` | yes | 134031 | 27140.2 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| E06 | EBF0F34D-40F7-4D69-8EAC-ECE71F5CB499 | `5F389D57-3572-4B51-8016-2EEB7FF2A676` | `5F389D57-3572-4B51-8016-2EEB7FF2A676` | yes | 135342 | 50920.5 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)