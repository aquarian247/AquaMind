# Semantic Migration Validation Report

- Component key: `F8A75447-CFA6-4CCD-A15D-0603783992EA`
- Batch: `SF AUG 24` (id=504)
- Populations: 193
- Window: 2024-08-22 14:52:20 → 2025-11-29 09:06:10

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4327 | 4327 | 0.00 |
| Feeding kg | 50507.26 | 50507.26 | -0.00 |
| Mortality events | 5481 | 5058 | 423.00 |
| Mortality count | 443422 | 443422 | 0.00 |
| Mortality biomass kg | 0.00 | 1792.92 | -1792.92 |
| Culling events | 24 | 24 | 0.00 |
| Culling count | 408778 | 408778 | 0.00 |
| Culling biomass kg | 7301383.29 | 7301383.29 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 814 | 814 | 0.00 |
| Growth samples | 393 | 393 | 0.00 |
| Health journal entries | 17 | 17 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 852200
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 6 total, 6 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 74.
- Fishgroup classification: 23 temporary bridge fishgroups, 59 real stage-entry fishgroups, 25 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1636363 | 0 | 2845672 | 4300655 | 2.63 | 1.51 | 2024-08-22 | 2024-08-24 | 50 | 50 | 0 | 100 | 102 |
| Fry | 754657 | 0 | 1197634 | 3870355 | 5.13 | 3.23 | 2025-05-12 | 2025-05-14 | 6 | 6 | 0 | 65 | 69 |
| Parr | 200904 | 0 | 548869 | 677177 | 3.37 | 1.23 | 2025-09-02 | 2025-09-04 | 2 | 2 | 0 | 21 | 21 |
| Smolt | 40619 | 0 | 40619 | 40619 | 1.0 | 1.0 | 2025-10-27 | 2025-10-29 | 1 | 1 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1636363 | 754657 | -881706 | 6 | 6 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 29506 |
| Fry -> Parr | 280896 | 280896 | 0 | 2 | 2 | yes | Bridge-aware (direct edge linkage; linked sources: 2) | OK |
| Parr -> Smolt | 200904 | 40619 | -160285 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0063`, `243.0088`, `243.0089`, `243.0090`, `243.0094`, `243.0097`, `243.0098`, `243.0099`, `243.0101`, `243.0102`
- Real stage-entry fishgroup examples: `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`, `243.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 193 | 193 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1159603 |
| Fry | 0 |
| Parr | 14900 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 72

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 46 | Hatchery:46 | FW21 Couldoran:45, FW13 Geocrab:1 |
| SourcePopBefore -> SourcePopAfter | 23 | Hatchery:23 | FW21 Couldoran:23 |
| DestPopBefore -> DestPopAfter | 4 | Hatchery:4 | FW21 Couldoran:3, FW13 Geocrab:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 72 | 0 | Hatchery:72 | FW21 Couldoran:70, FW13 Geocrab:2 | Unknown:72 |
| Reachable outside descendants | 95 | 0 | Hatchery:95 | FW21 Couldoran:92, FW13 Geocrab:3 | Unknown:95 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)