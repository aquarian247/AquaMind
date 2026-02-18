# Semantic Migration Validation Report

- Component key: `82214D2A-D43F-4514-B18C-5C9FF264E749`
- Batch: `BF (Fiskaaling) okt. 2023` (id=539)
- Populations: 279
- Window: 2023-10-04 11:38:34 → 2025-03-06 18:23:53

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4997 | 4997 | 0.00 |
| Feeding kg | 53684.47 | 53684.47 | 0.00 |
| Mortality events | 4929 | 3767 | 1162.00 |
| Mortality count | 48239 | 48239 | 0.00 |
| Mortality biomass kg | 0.00 | 393.50 | -393.50 |
| Culling events | 10 | 10 | 0.00 |
| Culling count | 119708 | 119708 | 0.00 |
| Culling biomass kg | 6740110.00 | 6740110.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 10 | 10 | 0.00 |
| Growth samples | 167 | 167 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 167947
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 66 total, 63 bridge-classified, 3 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 108.
- Fishgroup classification: 69 temporary bridge fishgroups, 25 real stage-entry fishgroups, 69 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 607811 | 0 | 607811 | 607811 | 1.0 | 1.0 | 2023-10-04 | 2023-10-06 | 1 | 1 | 0 | 1 | 1 |
| Fry | 582780 | 0 | 1186902 | 2234200 | 3.83 | 1.88 | 2023-12-28 | 2023-12-30 | 20 | 20 | 0 | 164 | 208 |
| Parr | 185952 | 0 | 492406 | 1451041 | 7.8 | 2.95 | 2024-03-19 | 2024-03-21 | 1 | 1 | 1 | 42 | 60 |
| Post-Smolt | 108127 | 0 | 117872 | 122254 | 1.13 | 1.04 | 2024-08-15 | 2024-08-17 | 3 | 3 | 1 | 6 | 10 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 607811 | 582780 | -25031 | 20 | 14 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 141825 | 21077 | -120748 | 1 | 1 | yes | Bridge-aware (linked sources: 7); lineage graph fallback used | OK |
| Parr -> Post-Smolt | 14675 | 12070 | -2605 | 3 | 3 | yes | Bridge-aware (linked sources: 8) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `232.0023`, `232.0027`, `232.0031`, `232.0035`, `232.0039`, `232.0043`, `232.0047`, `232.0051`, `232.0055`, `232.0059`
- Real stage-entry fishgroup examples: `232.0002`, `232.0022`, `232.0024`, `232.0026`, `232.0028`, `232.0030`, `232.0032`, `232.0034`, `232.0036`, `232.0038`
- Bridge fishgroups excluded from stage-entry windows: `232.0063`, `232.0237`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 279 | 279 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 30391 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 55

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 47 | Hatchery:47 | S08 Gjógv:47 |
| SourcePopBefore -> SourcePopAfter | 8 | Hatchery:8 | S08 Gjógv:8 |
| DestPopBefore -> DestPopAfter | 2 | Hatchery:2 | S08 Gjógv:2 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 55 | 0 | Hatchery:55 | S08 Gjógv:55 | Unknown:55 |
| Reachable outside descendants | 134 | 0 | Hatchery:134 | S08 Gjógv:134 | Unknown:134 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)