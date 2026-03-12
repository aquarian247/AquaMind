# Semantic Migration Validation Report

- Component key: `7311DFA1-6535-4D97-B708-BD4ED79AB8F9`
- Batch: `Stofnfiskur Des 23 - Vár 2024` (id=1344)
- Populations: 240
- Window: 2023-12-08 09:09:36 → 2025-05-09 12:01:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3741 | 3742 | -1.00 |
| Feeding kg | 519729.03 | 519787.03 | -58.00 |
| Mortality events | 3755 | 3341 | 414.00 |
| Mortality count | 368773 | 369464 | -691.00 |
| Mortality biomass kg | 0.00 | 3045.61 | -3045.61 |
| Culling events | 30 | 30 | 0.00 |
| Culling count | 82719 | 82719 | 0.00 |
| Culling biomass kg | 3128353.80 | 3128353.80 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 26 | 26 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 64233 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 451492
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/5 bridge-aware (80.0%), 1/5 entry-window (20.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 95 total, 23 bridge-classified, 53 same-stage superseded-zero, 0 short-lived orphan-zero, 19 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 121.
- Fishgroup classification: 51 temporary bridge fishgroups, 35 real stage-entry fishgroups, 51 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1766417 | 0 | 1766417 | 1766417 | 1.0 | 1.0 | 2023-12-08 | 2023-12-10 | 12 | 12 | 0 | 12 | 33 |
| Fry | 1742830 | 0 | 1749666 | 1765781 | 1.01 | 1.01 | 2024-02-21 | 2024-02-23 | 10 | 10 | 0 | 18 | 32 |
| Parr | 956622 | 0 | 1879113 | 5675802 | 5.93 | 3.02 | 2024-05-07 | 2024-05-09 | 6 | 6 | 2 | 48 | 91 |
| Smolt | 440588 | 0 | 1646896 | 2177193 | 4.94 | 1.32 | 2024-08-26 | 2024-08-28 | 5 | 5 | 3 | 25 | 42 |
| Post-Smolt | 221503 | 0 | 1406000 | 3803333 | 17.17 | 2.71 | 2024-12-13 | 2024-12-15 | 2 | 2 | 2 | 42 | 42 |
| Adult | 44425 | 0 | 44425 | 44425 | 1.0 | 1.0 | 2024-02-22 | 2024-02-24 | 1 | 0 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 0 | 1742830 | 1742830 | 10 | 10 | yes | Bridge-aware (direct edge linkage; linked sources: 10) | ALERT: population increases without mixed-batch composition |
| Fry -> Parr | 1219981 | 956622 | -263359 | 6 | 6 | yes | Bridge-aware (linked sources: 18) | OK |
| Parr -> Smolt | 894902 | 440588 | -454314 | 5 | 5 | yes | Bridge-aware (linked sources: 12) | WARN: stage drop exceeds total known removals by 2822 |
| Smolt -> Post-Smolt | 222886 | 221503 | -1383 | 2 | 2 | yes | Bridge-aware (linked sources: 4) | OK |
| Post-Smolt -> Adult | 221503 | 44425 | -177078 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `236.0024`, `236.0025`, `236.0027`, `236.0028`, `236.0030`, `236.0031`, `236.0032`, `236.0033`, `236.0037`, `236.0038`
- Real stage-entry fishgroup examples: `236.0002`, `236.0003`, `236.0004`, `236.0005`, `236.0006`, `236.0007`, `236.0008`, `236.0009`, `236.0010`, `236.0011`
- Bridge fishgroups excluded from stage-entry windows: `236.0027`, `236.0028`, `236.0072`, `236.0075`, `236.0076`, `236.0127`, `236.0128`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 168 | 168 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 22951 |
| Parr | 37258 |
| Post-Smolt | 1240296 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `22D7AC4D-8EC4-4A99-9C39-BE2A4152E65F` | Post-Smolt | 133921 | 133921 |
| `29626D55-30E4-4937-BDE3-ED763FB78CB7` | Post-Smolt | 107282 | 107282 |
| `A336B3F3-F73F-4679-A36D-E74A749BAED6` | Post-Smolt | 100727 | 100727 |
| `0590D9EE-8EDC-4A4E-B134-5E0C974E4429` | Post-Smolt | 100000 | 100000 |
| `D0969117-5A60-46C7-99C3-8AE84401407C` | Post-Smolt | 95498 | 95498 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 0

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 0 | 0 | - | - | - |
| Reachable outside descendants | 0 | 0 | - | - | - |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | FAIL | Positive stage transition deltas without mixed-batch composition rows: 1 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: FAIL (advisory)