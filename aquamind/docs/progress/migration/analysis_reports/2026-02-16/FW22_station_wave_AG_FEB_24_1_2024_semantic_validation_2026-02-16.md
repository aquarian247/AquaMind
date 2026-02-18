# Semantic Migration Validation Report

- Component key: `9A2FCED1-721F-4893-AED7-0C07E24C715F`
- Batch: `AG FEB 24` (id=483)
- Populations: 27
- Window: 2024-02-15 14:37:52 → 2025-04-30 11:20:43

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 450 | 450 | 0.00 |
| Feeding kg | 47600.71 | 47600.71 | 0.00 |
| Mortality events | 706 | 700 | 6.00 |
| Mortality count | 235150 | 235150 | 0.00 |
| Mortality biomass kg | 0.00 | 4997.53 | -4997.53 |
| Culling events | 243 | 243 | 0.00 |
| Culling count | 147875 | 147875 | 0.00 |
| Culling biomass kg | 25181580.63 | 25181580.59 | 0.04 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 20 | 20 | 0.00 |
| Growth samples | 42 | 42 | 0.00 |
| Health journal entries | 80 | 80 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 383025
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 2 total, 2 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 11.
- Fishgroup classification: 2 temporary bridge fishgroups, 17 real stage-entry fishgroups, 2 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 381818 | 0 | 398523 | 398523 | 1.04 | 1.0 | 2024-02-15 | 2024-02-17 | 12 | 12 | 0 | 13 | 13 |
| Fry | 99964 | 0 | 99964 | 99964 | 1.0 | 1.0 | 2024-05-21 | 2024-05-23 | 2 | 2 | 0 | 2 | 2 |
| Parr | 299590 | 0 | 446335 | 558581 | 1.86 | 1.25 | 2024-09-04 | 2024-09-06 | 1 | 1 | 0 | 5 | 6 |
| Smolt | 144317 | 0 | 227839 | 227839 | 1.58 | 1.0 | 2024-11-08 | 2024-11-10 | 1 | 1 | 0 | 2 | 3 |
| Post-Smolt | 118095 | 0 | 201617 | 201617 | 1.71 | 1.0 | 2025-01-29 | 2025-01-31 | 1 | 1 | 0 | 3 | 3 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 381818 | 99964 | -281854 | 2 | 2 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 83522 | 83522 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 2) | OK |
| Parr -> Smolt | 83522 | 54932 | -28590 | 1 | 1 | yes | Bridge-aware (linked sources: 2) | OK |
| Smolt -> Post-Smolt | 83522 | 83522 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0019`, `241.0023`
- Real stage-entry fishgroup examples: `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0008`, `241.0009`, `241.0010`, `241.0011`, `241.0012`, `241.0013`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 27 | 27 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 331705 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 12

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 11 | Hatchery:11 | FW22 Applecross:11 |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | FW22 Applecross:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 12 | 0 | Hatchery:12 | FW22 Applecross:12 | Unknown:12 |
| Reachable outside descendants | 12 | 0 | Hatchery:12 | FW22 Applecross:12 | Unknown:12 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)