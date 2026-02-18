# Semantic Migration Validation Report

- Component key: `2626A8C5-1C77-40B4-89FF-00CDE7CE5D2F`
- Batch: `SF DEC 24` (id=487)
- Populations: 149
- Window: 2024-12-19 11:29:49 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-16 18:23:13.172083, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1382 | 1382 | 0.00 |
| Feeding kg | 140240.61 | 140240.61 | -0.00 |
| Mortality events | 3083 | 3081 | 2.00 |
| Mortality count | 157914 | 157914 | 0.00 |
| Mortality biomass kg | 0.00 | 3231.42 | -3231.42 |
| Culling events | 669 | 669 | 0.00 |
| Culling count | 439194 | 439194 | 0.00 |
| Culling biomass kg | 14403158.55 | 14403158.49 | 0.06 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 41 | 41 | 0.00 |
| Growth samples | 103 | 103 | 0.00 |
| Health journal entries | 6 | 6 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 597108
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 11 total, 10 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 43.
- Fishgroup classification: 35 temporary bridge fishgroups, 77 real stage-entry fishgroups, 35 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2181819 | 0 | 2198182 | 2198182 | 1.01 | 1.0 | 2024-12-19 | 2024-12-21 | 66 | 66 | 0 | 67 | 67 |
| Fry | 325993 | 0 | 325993 | 325993 | 1.0 | 1.0 | 2025-03-21 | 2025-03-23 | 8 | 8 | 0 | 8 | 8 |
| Parr | 870846 | 0 | 2751321 | 8733925 | 10.03 | 3.17 | 2025-06-17 | 2025-06-19 | 2 | 2 | 1 | 49 | 56 |
| Post-Smolt | 367230 | 169768 | 1285409 | 2424876 | 6.6 | 1.89 | 2025-09-03 | 2025-09-05 | 1 | 1 | 1 | 14 | 18 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2181819 | 325993 | -1855826 | 8 | 8 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 1258718 |
| Fry -> Parr | 160906 | 160906 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 4) | OK |
| Parr -> Post-Smolt | 69894 | 69894 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 2) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `248.0076`, `248.0078`, `248.0080`, `248.0082`, `248.0084`, `248.0085`, `248.0086`, `248.0087`, `248.0088`, `248.0090`
- Real stage-entry fishgroup examples: `248.0001`, `248.0002`, `248.0003`, `248.0004`, `248.0005`, `248.0006`, `248.0007`, `248.0008`, `248.0009`, `248.0010`
- Bridge fishgroups excluded from stage-entry windows: `248.0078`, `248.0105`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 149 | 149 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1922643 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 70

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 59 | Hatchery:59 | FW22 Applecross:59 |
| SourcePopBefore -> SourcePopAfter | 11 | Hatchery:11 | FW22 Applecross:11 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 70 | 0 | Hatchery:70 | FW22 Applecross:70 | Unknown:70 |
| Reachable outside descendants | 88 | 0 | Hatchery:88 | FW22 Applecross:88 | Unknown:88 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 2; latest holder in selected component: 2; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| LS1_A2 | 18E93528-1B39-407F-A2B3-21E873149BC6 | `1C3A970A-F2B0-4CE2-B9A9-04BD56B55C0A` | `1C3A970A-F2B0-4CE2-B9A9-04BD56B55C0A` | yes | 348771 | 66654.5 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| LS1_B3 | 0734F126-BE61-4BFE-BFBF-F50E0E58C918 | `9C072382-CDE0-4721-B910-68AEF7113231` | `9C072382-CDE0-4721-B910-68AEF7113231` | yes | 419146 | 98762.2 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)