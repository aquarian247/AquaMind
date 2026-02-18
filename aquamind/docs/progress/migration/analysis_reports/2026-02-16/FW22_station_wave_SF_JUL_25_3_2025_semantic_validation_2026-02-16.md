# Semantic Migration Validation Report

- Component key: `95045310-2FE0-4533-B3CA-0329E953A705`
- Batch: `SF JUL 25` (id=490)
- Populations: 91
- Window: 2025-07-10 10:29:41 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-16 18:26:29.482334, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 80 | 80 | 0.00 |
| Feeding kg | 138.40 | 138.40 | 0.00 |
| Mortality events | 1468 | 1422 | 46.00 |
| Mortality count | 42364 | 42364 | 0.00 |
| Mortality biomass kg | 0.00 | 6.53 | -6.53 |
| Culling events | 375 | 375 | 0.00 |
| Culling count | 342908 | 342908 | 0.00 |
| Culling biomass kg | 12094.10 | 12094.04 | 0.06 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 16 | 16 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 385272
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/2 bridge-aware (50.0%), 1/2 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 13.
- Fishgroup classification: 2 temporary bridge fishgroups, 89 real stage-entry fishgroups, 2 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2700000 | 0 | 2700000 | 2700000 | 1.0 | 1.0 | 2025-07-10 | 2025-07-12 | 78 | 78 | 0 | 78 | 78 |
| Fry | 505335 | 0 | 505335 | 505335 | 1.0 | 1.0 | 2025-10-20 | 2025-10-22 | 8 | 8 | 0 | 8 | 8 |
| Parr | 883348 | 883348 | 1091216 | 1290796 | 1.46 | 1.18 | 2026-01-20 | 2026-01-22 | 3 | 3 | 2 | 5 | 5 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2700000 | 505335 | -2194665 | 8 | 8 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 1809393 |
| Fry -> Parr | 315215 | 315215 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 5) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `253.0087`, `253.0089`
- Real stage-entry fishgroup examples: `253.0001`, `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0008`, `253.0009`, `253.0010`
- Bridge fishgroups excluded from stage-entry windows: `253.0087`, `253.0089`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 91 | 91 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 2440411 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 70

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 70 | Hatchery:70 | FW22 Applecross:70 |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 70 | 0 | Hatchery:70 | FW22 Applecross:70 | Unknown:70 |
| Reachable outside descendants | 70 | 0 | Hatchery:70 | FW22 Applecross:70 | Unknown:70 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| P05 | 080A8695-DA88-4E27-A40A-C175B7BE1C07 | `BB88F7A6-B704-4CE4-BF03-675190C9CF8C` | `BB88F7A6-B704-4CE4-BF03-675190C9CF8C` | yes | 396615 | 2066.75 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| P06 | FAA1E775-2112-435F-AC86-1B21F70C45FC | `4FF37A2D-363D-4494-9E35-F4697EF124D6` | `4FF37A2D-363D-4494-9E35-F4697EF124D6` | yes | 419097 | 2372.98 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| P07 | 23618732-E035-4DF4-9264-DB2DC5E7C4EC | `DCB8EB2A-75B5-4CBC-802B-3611B4216585` | `DCB8EB2A-75B5-4CBC-802B-3611B4216585` | yes | 203932 | 1164.45 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)