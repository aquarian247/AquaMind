# Semantic Migration Validation Report

- Component key: `248556CA-6E6C-4936-9242-1AE02776A360`
- Batch: `Stofnfiskur Des 23` (id=533)
- Populations: 168
- Window: 2023-12-08 09:09:36 → 2025-05-09 12:01:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3741 | 3741 | 0.00 |
| Feeding kg | 519729.03 | 519729.03 | 0.00 |
| Mortality events | 3755 | 3339 | 416.00 |
| Mortality count | 368773 | 368773 | 0.00 |
| Mortality biomass kg | 0.00 | 2781.65 | -2781.65 |
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
| Environmental readings | n/a (sqlite) | 0 | n/a |
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
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 26 total, 23 bridge-classified, 3 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 58.
- Fishgroup classification: 51 temporary bridge fishgroups, 35 real stage-entry fishgroups, 51 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1766417 | 0 | 1766417 | 1766417 | 1.0 | 1.0 | 2023-12-08 | 2023-12-10 | 12 | 12 | 0 | 12 | 12 |
| Fry | 1742830 | 0 | 1749666 | 1765781 | 1.01 | 1.01 | 2024-02-21 | 2024-02-23 | 10 | 10 | 0 | 18 | 18 |
| Parr | 956622 | 0 | 1879113 | 5692467 | 5.95 | 3.03 | 2024-05-07 | 2024-05-09 | 6 | 6 | 2 | 48 | 64 |
| Smolt | 440588 | 0 | 1646896 | 2177193 | 4.94 | 1.32 | 2024-08-26 | 2024-08-28 | 5 | 5 | 3 | 25 | 32 |
| Post-Smolt | 221503 | 0 | 1406000 | 3448758 | 15.57 | 2.45 | 2024-12-13 | 2024-12-15 | 2 | 2 | 2 | 39 | 42 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1766417 | 1742830 | -23587 | 10 | 10 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Fry -> Parr | 1219981 | 956622 | -263359 | 6 | 6 | yes | Bridge-aware (linked sources: 7); lineage graph fallback used | OK |
| Parr -> Smolt | 901795 | 440588 | -461207 | 5 | 5 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | WARN: stage drop exceeds total known removals by 9715 |
| Smolt -> Post-Smolt | 222886 | 221503 | -1383 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

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
| Fry | 1765781 |
| Parr | 2031699 |
| Smolt | 1255030 |
| Post-Smolt | 1240296 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `9CC6BBF6-ECE3-433B-A95E-1E13E3B96D0F` | Parr | 228357 | 228357 |
| `38714C5D-FDCB-4625-A4D1-83ACAA5526A2` | Parr | 216610 | 216610 |
| `DDE1C2AB-CA82-43AD-9085-2512D139F6FA` | Parr | 193037 | 193037 |
| `3C403C49-FDFE-424D-B021-625243BFB31E` | Fry | 174283 | 174283 |
| `77892CE6-327A-4748-B1DC-D3331D7A346A` | Fry | 174283 | 174283 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1766417 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 57

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 45 | Hatchery:45 | S03 Norðtoftir:45 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 57 | 0 | Hatchery:57 | S03 Norðtoftir:57 | Unknown:57 |
| Reachable outside descendants | 72 | 0 | Hatchery:72 | S03 Norðtoftir:72 | Unknown:72 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)