# Semantic Migration Validation Report

- Component key: `DCF779B3-E1FE-439E-9AA9-16F72B3B22BB`
- Batch: `Stofnfiskur mai 2024` (id=527)
- Populations: 183
- Window: 2024-05-15 09:23:58 → 2025-09-29 07:20:22

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1807 | 1807 | 0.00 |
| Feeding kg | 472497.55 | 472497.55 | 0.00 |
| Mortality events | 3769 | 3242 | 527.00 |
| Mortality count | 466357 | 466357 | 0.00 |
| Mortality biomass kg | 0.00 | 6699.04 | -6699.04 |
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
- Known removal count (mortality + culling + escapes + harvest): 542444
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/4 bridge-aware (50.0%), 2/4 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 45 total, 44 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 7.
- Fishgroup classification: 85 temporary bridge fishgroups, 23 real stage-entry fishgroups, 85 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501578 | 0 | 1501578 | 1501578 | 1.0 | 1.0 | 2024-05-15 | 2024-05-17 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1432839 | 0 | 1432839 | 1432839 | 1.0 | 1.0 | 2024-07-27 | 2024-07-29 | 7 | 7 | 0 | 7 | 7 |
| Parr | 1071642 | 0 | 2116390 | 10175488 | 9.5 | 4.81 | 2024-10-29 | 2024-10-31 | 8 | 8 | 2 | 94 | 136 |
| Smolt | 306862 | 0 | 1525452 | 3154469 | 10.28 | 2.07 | 2025-03-12 | 2025-03-14 | 1 | 1 | 2 | 16 | 19 |
| Post-Smolt | 232668 | 0 | 1032916 | 1332788 | 5.73 | 1.29 | 2025-06-06 | 2025-06-08 | 2 | 2 | 2 | 16 | 16 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501578 | 1432839 | -68739 | 7 | 5 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1432839 | 992493 | -440346 | 8 | 8 | yes | Bridge-aware (linked sources: 7); lineage graph fallback used | OK |
| Parr -> Smolt | 1071642 | 306862 | -764780 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 222336 |
| Smolt -> Post-Smolt | 165070 | 162174 | -2896 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0011`, `243.0012`, `243.0013`, `243.0014`, `243.0018`, `243.0019`, `243.0020`, `243.0021`, `24A.0003`, `24A.0004`
- Real stage-entry fishgroup examples: `243.0001`, `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`
- Bridge fishgroups excluded from stage-entry windows: `243.0018`, `243.0019`, `24A.0086`, `24A.0088`, `24A.0143`, `24A.0144`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 183 | 183 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 440346 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `6C462EDC-173C-420D-8406-E726EF82DCE9` | Fry | 220173 | 220173 |
| `8E425921-6107-4C1D-9013-BD52D6CD57AA` | Fry | 220173 | 220173 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 199215 |
| Parr | 731 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 53

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 6 | Hatchery:6 | S16 Glyvradalur:6 |
| SourcePopBefore -> SourcePopAfter | 47 | Hatchery:47 | S16 Glyvradalur:47 |
| DestPopBefore -> DestPopAfter | 1 | Hatchery:1 | S16 Glyvradalur:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 53 | 0 | Hatchery:53 | S16 Glyvradalur:53 | Unknown:53 |
| Reachable outside descendants | 88 | 0 | Hatchery:88 | S16 Glyvradalur:88 | Unknown:88 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)