# Semantic Migration Validation Report

- Component key: `0CED8E8A-D16C-4616-9CA9-5D028D32D0B8`
- Batch: `StofnFiskur mars 2024` (id=445)
- Populations: 305
- Window: 2024-03-12 14:35:02 → 2025-07-21 18:31:04

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4152 | 4152 | 0.00 |
| Feeding kg | 61455.91 | 61455.91 | -0.00 |
| Mortality events | 4240 | 3750 | 490.00 |
| Mortality count | 39909 | 39909 | 0.00 |
| Mortality biomass kg | 0.00 | 1012.30 | -1012.30 |
| Culling events | 24 | 24 | 0.00 |
| Culling count | 202177 | 202177 | 0.00 |
| Culling biomass kg | 8218018.90 | 8218018.90 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 12 | 12 | 0.00 |
| Growth samples | 125 | 125 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 242086
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 130 total, 86 bridge-classified, 20 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 24 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 153.
- Fishgroup classification: 98 temporary bridge fishgroups, 13 real stage-entry fishgroups, 98 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 388110 | 0 | 388110 | 388110 | 1.0 | 1.0 | 2024-03-12 | 2024-03-14 | 1 | 1 | 0 | 1 | 1 |
| Fry | 376686 | 0 | 750624 | 1523667 | 4.04 | 2.03 | 2024-06-03 | 2024-06-05 | 10 | 10 | 0 | 116 | 147 |
| Smolt | 51157 | 0 | 414479 | 1211791 | 23.69 | 2.92 | 2024-09-10 | 2024-09-12 | 1 | 1 | 0 | 44 | 135 |
| Post-Smolt | 130177 | 27959 | 330417 | 820560 | 6.3 | 2.48 | 2024-08-20 | 2024-08-22 | 1 | 1 | 0 | 14 | 22 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 400000 | 400000 | 0 | 10 | 10 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Smolt | 376686 | 51157 | -325529 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 83443 |
| Smolt -> Post-Smolt | 51157 | 130177 | 79020 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0028`, `241.0030`, `241.0034`, `241.0036`, `241.0040`, `241.0042`, `241.0046`, `241.0048`, `241.0052`, `241.0054`
- Real stage-entry fishgroup examples: `241.0002`, `241.0012`, `241.0013`, `241.0014`, `241.0015`, `241.0016`, `241.0017`, `241.0018`, `241.0019`, `241.0020`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 305 | 305 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 40000 |
| Smolt | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 43

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 30 | Hatchery:30 | S08 Gjógv:30 |
| SourcePopBefore -> SourcePopAfter | 13 | Hatchery:13 | S08 Gjógv:13 |
| DestPopBefore -> DestPopAfter | 2 | Hatchery:2 | S08 Gjógv:2 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 43 | 0 | Hatchery:43 | S08 Gjógv:43 | Unknown:43 |
| Reachable outside descendants | 97 | 0 | Hatchery:97 | S08 Gjógv:97 | Unknown:97 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 1; latest holder in selected component: 0; latest holder outside selected component: 1; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| T2 | 449002D1-9C9A-4198-810A-82463AF2E122 | `3DE85EEE-5F4F-4177-BD0C-58E31FEEB0DC` | `5F75D907-CA8A-4B56-94B7-0A8889F19122` | no | 39828 | 9416.86 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)