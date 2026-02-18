# Semantic Migration Validation Report

- Component key: `0CB99E1D-8E9F-4CE0-A323-27608DA573D7`
- Batch: `Bakkafrost mai 24` (id=522)
- Populations: 164
- Window: 2024-05-10 08:33:22 → 2025-09-29 07:20:22

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1521 | 1521 | 0.00 |
| Feeding kg | 465946.68 | 465946.68 | 0.00 |
| Mortality events | 2889 | 2619 | 270.00 |
| Mortality count | 223016 | 223016 | 0.00 |
| Mortality biomass kg | 0.00 | 6574.89 | -6574.89 |
| Culling events | 5 | 5 | 0.00 |
| Culling count | 76087 | 76087 | 0.00 |
| Culling biomass kg | 3436839.00 | 3436839.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 44 | 44 | 0.00 |
| Growth samples | 9 | 9 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 299103
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/4 bridge-aware (25.0%), 3/4 entry-window (75.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 39 total, 38 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 63.
- Fishgroup classification: 77 temporary bridge fishgroups, 14 real stage-entry fishgroups, 77 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 299887 | 0 | 299887 | 299887 | 1.0 | 1.0 | 2024-05-10 | 2024-05-12 | 1 | 1 | 0 | 1 | 1 |
| Fry | 663305 | 0 | 663305 | 663305 | 1.0 | 1.0 | 2024-07-27 | 2024-07-29 | 3 | 3 | 0 | 3 | 3 |
| Parr | 838104 | 0 | 2028669 | 9148916 | 10.92 | 4.51 | 2024-10-31 | 2024-11-02 | 7 | 7 | 0 | 89 | 125 |
| Smolt | 306862 | 0 | 1336981 | 2819245 | 9.19 | 2.11 | 2025-03-12 | 2025-03-14 | 1 | 1 | 2 | 16 | 19 |
| Post-Smolt | 174347 | 0 | 552442 | 676919 | 3.88 | 1.23 | 2025-06-06 | 2025-06-08 | 2 | 2 | 2 | 16 | 16 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 299887 | 663305 | 363418 | 3 | 1 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Fry -> Parr | 663305 | 838104 | 174799 | 7 | 7 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Parr -> Smolt | 838104 | 306862 | -531242 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 232139 |
| Smolt -> Post-Smolt | 46186 | 45376 | -810 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `24A.0003`, `24A.0004`, `24A.0005`, `24A.0006`, `24A.0009`, `24A.0013`, `24A.0029`, `24A.0030`, `24A.0031`, `24A.0033`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `24A.0002`, `24A.0010`, `24A.0011`, `24A.0014`, `24A.0016`, `24A.0019`
- Bridge fishgroups excluded from stage-entry windows: `24A.0086`, `24A.0088`, `24A.0143`, `24A.0144`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 164 | 164 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 440346 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `8E425921-6107-4C1D-9013-BD52D6CD57AA` | Fry | 220173 | 220173 |
| `8F665BEF-9BF0-43D6-8ABE-4DE7F5150705` | Fry | 220173 | 220173 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 119 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 43

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 3 | Hatchery:3 | S16 Glyvradalur:3 |
| SourcePopBefore -> SourcePopAfter | 39 | Hatchery:39 | S16 Glyvradalur:39 |
| DestPopBefore -> DestPopAfter | 1 | Hatchery:1 | S16 Glyvradalur:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 43 | 0 | Hatchery:43 | S16 Glyvradalur:43 | Unknown:43 |
| Reachable outside descendants | 72 | 0 | Hatchery:72 | S16 Glyvradalur:72 | Unknown:72 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 2) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)