# Semantic Migration Validation Report

- Component key: `7181368D-569E-4809-A8A3-029C7353EB24`
- Batch: `Benchmark Gen. Juni 2025` (id=480)
- Populations: 100
- Window: 2025-06-12 15:00:17 → 2026-02-16 16:24:54.449518

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 684 | 684 | 0.00 |
| Feeding kg | 3963.70 | 3963.71 | -0.01 |
| Mortality events | 1283 | 1280 | 3.00 |
| Mortality count | 536837 | 536837 | 0.00 |
| Mortality biomass kg | 0.00 | 275.09 | -275.09 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
| Growth samples | 108 | 108 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 536837
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 28 total, 28 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 12.
- Fishgroup classification: 40 temporary bridge fishgroups, 60 real stage-entry fishgroups, 40 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500565 | 0 | 3500565 | 3500565 | 1.0 | 1.0 | 2025-06-12 | 2025-06-14 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3438259 | 0 | 3438259 | 3438259 | 1.0 | 1.0 | 2025-09-03 | 2025-09-05 | 12 | 12 | 0 | 12 | 12 |
| Parr | 2827347 | 2827347 | 3534284 | 4476097 | 1.58 | 1.27 | 2025-11-27 | 2025-11-29 | 9 | 9 | 12 | 21 | 49 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1166857 | 89759 | -1077098 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | WARN: stage drop exceeds total known removals by 540261 |
| Fry -> Parr | 89759 | 89759 | 0 | 9 | 9 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0001`, `252.0052`, `252.0053`, `252.0054`, `252.0055`, `252.0056`, `252.0057`, `252.0058`, `252.0059`, `252.0060`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `252.0005`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`, `252.0011`
- Bridge fishgroups excluded from stage-entry windows: `252.0060`, `252.0061`, `252.0062`, `252.0063`, `252.0064`, `252.0065`, `252.0066`, `252.0067`, `252.0069`, `252.0070`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 100 | 100 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500565 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 51

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 12 | Hatchery:12 | S24 Strond:12 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 51 | 0 | Hatchery:51 | S24 Strond:51 | Unknown:51 |
| Reachable outside descendants | 87 | 0 | Hatchery:87 | S24 Strond:87 | Unknown:87 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 9; latest holder in selected component: 9; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C1 | FDEAE661-F3DB-4CBA-8C4B-1274E452EA86 | `F216F4BD-8229-4CC7-A80E-0786701D5B8B` | `F216F4BD-8229-4CC7-A80E-0786701D5B8B` | yes | 413607 | 4039.7 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| C2 | 4626FC19-F0F1-48BA-B7E3-19F399BE44BC | `AD564ED2-5E61-46CF-9779-5EB9C4A0DE9E` | `AD564ED2-5E61-46CF-9779-5EB9C4A0DE9E` | yes | 425784 | 5028.57 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| C3 | BA4588C4-3B18-4A83-A265-A96CC5D746AB | `120B81E0-EDC6-4047-A3B4-09ACDA4ABAC2` | `120B81E0-EDC6-4047-A3B4-09ACDA4ABAC2` | yes | 235105 | 5221.39 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| C4 | 58C52721-00DA-4DC5-9EE2-F5C404C37EE5 | `FC1A48C4-50B7-478D-A572-6A00DDA4F7D0` | `FC1A48C4-50B7-478D-A572-6A00DDA4F7D0` | yes | 223044 | 5172.5 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| C5 | 5270F2C1-7731-41C6-AC7B-AF6009FF5173 | `7881AA95-76B0-4F39-9EBD-3BB1F91596D1` | `7881AA95-76B0-4F39-9EBD-3BB1F91596D1` | yes | 225893 | 5179.41 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| C8 | 5037616D-686C-4398-B559-E29B78A86AFE | `EB2ACEF3-A708-4A96-ADA1-1A166123DBB4` | `EB2ACEF3-A708-4A96-ADA1-1A166123DBB4` | yes | 228813 | 5876.39 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| D3 | F92CF1C1-AC26-416A-88A8-02D16F25E265 | `A5550EFD-1FD0-46B8-A422-A1A434A3E2AD` | `A5550EFD-1FD0-46B8-A422-A1A434A3E2AD` | yes | 424841 | 6257.39 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| D4 | D751B03C-1EA5-47F0-A98D-EAC6DA9D0494 | `0CEACA85-03C3-4933-B980-04E682544227` | `0CEACA85-03C3-4933-B980-04E682544227` | yes | 422010 | 6969.25 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| D8 | 90E4BD9B-3BDF-4542-AD4C-61A4C75947DC | `C68ADD92-72AE-4254-94DC-AE3AC2977FA3` | `C68ADD92-72AE-4254-94DC-AE3AC2977FA3` | yes | 228250 | 4659.81 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)