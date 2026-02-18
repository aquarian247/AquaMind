# Semantic Migration Validation Report

- Component key: `A88689DA-143C-490D-86FA-03661F67C7F6`
- Batch: `SF SEP 25` (id=491)
- Populations: 84
- Window: 2025-09-11 08:42:32 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-16 18:27:31.325610, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 782 | 719 | 63.00 |
| Mortality count | 34810 | 34810 | 0.00 |
| Mortality biomass kg | 0.00 | 4.64 | -4.64 |
| Culling events | 211 | 211 | 0.00 |
| Culling count | 310462 | 310462 | 0.00 |
| Culling biomass kg | 2294.80 | 2294.84 | -0.04 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 1 | 1 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 345272
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 8.
- Fishgroup classification: 0 temporary bridge fishgroups, 84 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2800638 | 0 | 2800638 | 2800638 | 1.0 | 1.0 | 2025-09-11 | 2025-09-13 | 76 | 76 | 0 | 76 | 76 |
| Fry | 1947636 | 1947636 | 1947636 | 1947636 | 1.0 | 1.0 | 2025-12-15 | 2025-12-17 | 8 | 8 | 0 | 8 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2800638 | 1947636 | -853002 | 8 | 8 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 507730 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `254.0001`, `254.0002`, `254.0003`, `254.0004`, `254.0005`, `254.0006`, `254.0007`, `254.0008`, `254.0009`, `254.0010`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 84 | 84 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 2521388 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 68

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 68 | Hatchery:68 | FW22 Applecross:68 |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 68 | 0 | Hatchery:68 | FW22 Applecross:68 | Unknown:68 |
| Reachable outside descendants | 68 | 0 | Hatchery:68 | FW22 Applecross:68 | Unknown:68 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 8; latest holder in selected component: 8; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| F2_01 | AE77BFFB-FED4-4B27-A5B0-F6FFEE42EEFF | `76E5F2BA-61EE-4F47-81DC-0B8981CA549F` | `76E5F2BA-61EE-4F47-81DC-0B8981CA549F` | yes | 269767 | 417.56 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_02 | E42DF7C9-351A-409A-8181-C8209A5D9569 | `C47B45D1-7272-4432-8C15-EBAE78C674B8` | `C47B45D1-7272-4432-8C15-EBAE78C674B8` | yes | 237661 | 364.52 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_03 | A254BF0F-3C0F-4B36-8389-F3713978F82F | `D402F80E-910F-49B8-8079-B7EEFA3B7D51` | `D402F80E-910F-49B8-8079-B7EEFA3B7D51` | yes | 218603 | 303.16 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_04 | 2E1D51DA-1B6E-4EFC-9996-30F43AB241E9 | `B5033E23-86AF-4728-9919-DCA216C7828A` | `B5033E23-86AF-4728-9919-DCA216C7828A` | yes | 222260 | 311.89 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_05 | 236DAF47-07D8-4DD4-8188-1793B5080497 | `2403DFEF-BAA3-480F-870A-01EAAAF811E2` | `2403DFEF-BAA3-480F-870A-01EAAAF811E2` | yes | 229027 | 338.73 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_06 | 8CAB29AA-C1CF-40A9-866E-93204EF2E4B3 | `64D7E594-A8A1-4C1D-961F-715A5B045AE3` | `64D7E594-A8A1-4C1D-961F-715A5B045AE3` | yes | 231057 | 350.55 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_07 | 2D1BBC47-AE93-4D6A-8613-81DF0721F9C0 | `DDB578BF-B789-495A-B4F0-DC9A0936FCE6` | `DDB578BF-B789-495A-B4F0-DC9A0936FCE6` | yes | 254699 | 357.64 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| F2_08 | 0DD60763-3562-490F-B9FF-C83CF1E9319C | `6EB3969C-12CC-44F7-A184-B7E1B58E3BF2` | `6EB3969C-12CC-44F7-A184-B7E1B58E3BF2` | yes | 284562 | 373.59 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)