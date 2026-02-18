# Semantic Migration Validation Report

- Component key: `720039AF-2D1A-4020-B540-01F48B877A3D`
- Batch: `SF NOV 23 17` (id=505)
- Populations: 198
- Window: 2023-11-02 11:00:23 → 2025-04-15 11:57:38

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3104 | 3104 | 0.00 |
| Feeding kg | 149691.95 | 149691.95 | -0.00 |
| Mortality events | 4787 | 4642 | 145.00 |
| Mortality count | 516119 | 516119 | 0.00 |
| Mortality biomass kg | 0.00 | 26863.41 | -26863.41 |
| Culling events | 189 | 189 | 0.00 |
| Culling count | 298106 | 298106 | 0.00 |
| Culling biomass kg | 29482017.69 | 29482017.69 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 244 | 244 | 0.00 |
| Growth samples | 385 | 385 | 0.00 |
| Health journal entries | 166 | 166 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 1 | 1 | 0.00 |
| Harvest events | n/a | 1 | n/a |
| Harvest count | 372954 | 372954 | 0.00 |
| Harvest live kg | 3455000.00 | 3455000.00 | 0.00 |
| Harvest gutted kg | 3455000.00 | 3455000.00 | 0.00 |

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1187179
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 13 total, 13 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 83.
- Fishgroup classification: 35 temporary bridge fishgroups, 77 real stage-entry fishgroups, 51 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1176961 | 0 | 1508355 | 1508355 | 1.28 | 1.0 | 2024-01-31 | 2024-02-02 | 23 | 23 | 0 | 28 | 28 |
| Fry | 1830304 | 0 | 3316693 | 8681749 | 4.74 | 2.62 | 2023-11-02 | 2023-11-04 | 54 | 54 | 0 | 119 | 127 |
| Parr | 401809 | 0 | 1073283 | 1706161 | 4.25 | 1.59 | 2024-09-11 | 2024-09-13 | 3 | 3 | 2 | 16 | 16 |
| Smolt | 81628 | 0 | 627525 | 1649990 | 20.21 | 2.63 | 2024-12-12 | 2024-12-14 | 1 | 1 | 4 | 22 | 27 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1176961 | 1830304 | 653343 | 54 | 0 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Fry -> Parr | 160043 | 160043 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Parr -> Smolt | 92524 | 27944 | -64580 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `2317.0083`, `2317.0084`, `2317.0086`, `2317.0088`, `2317.0090`, `2317.0091`, `2317.0092`, `2317.0095`, `2317.0096`, `2317.0097`
- Real stage-entry fishgroup examples: `2317.0002`, `2317.0003`, `2317.0004`, `2317.0005`, `2317.0006`, `2317.0007`, `2317.0008`, `2317.0009`, `2317.0010`, `2317.0011`
- Bridge fishgroups excluded from stage-entry windows: `2317.0002`, `2317.0005`, `2317.0015`, `2317.0018`, `2317.0019`, `2317.0020`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 198 | 198 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 270707 |
| Fry | 1063819 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 103

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 49 | Hatchery:49 | FW21 Couldoran:46, FW22 Applecross:3 |
| SourcePopBefore -> SourcePopAfter | 51 | Hatchery:51 | FW21 Couldoran:46, FW22 Applecross:5 |
| DestPopBefore -> DestPopAfter | 8 | Hatchery:8 | FW21 Couldoran:5, FW22 Applecross:3 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 103 | 0 | Hatchery:103 | FW21 Couldoran:95, FW22 Applecross:8 | Unknown:103 |
| Reachable outside descendants | 124 | 0 | Hatchery:124 | FW21 Couldoran:111, FW22 Applecross:13 | Unknown:124 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)