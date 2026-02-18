# Semantic Migration Validation Report

- Component key: `0D5E2166-55AD-4469-B1E4-30A70B22FB72`
- Batch: `StofnFiskur S-21 juli25` (id=471)
- Populations: 40
- Window: 2025-07-23 13:48:53 → 2026-02-16 15:29:06.200007

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 36 | 36 | 0.00 |
| Feeding kg | 55.98 | 55.98 | 0.00 |
| Mortality events | 200 | 193 | 7.00 |
| Mortality count | 118521 | 118521 | 0.00 |
| Mortality biomass kg | 0.00 | 2.78 | -2.78 |
| Culling events | 8 | 7 | 1.00 |
| Culling count | 11250 | 11250 | 0.00 |
| Culling biomass kg | 15.00 | 15.21 | -0.21 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 129771
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 19 total, 19 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 13.
- Fishgroup classification: 20 temporary bridge fishgroups, 20 real stage-entry fishgroups, 20 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501504 | 0 | 1501504 | 1501504 | 1.0 | 1.0 | 2025-07-23 | 2025-07-25 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1395853 | 0 | 1591428 | 1591428 | 1.14 | 1.0 | 2025-10-22 | 2025-10-24 | 6 | 6 | 1 | 7 | 12 |
| Parr | 886785 | 886785 | 886785 | 886785 | 1.0 | 1.0 | 2026-01-15 | 2026-01-17 | 7 | 7 | 0 | 7 | 21 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501504 | 1501504 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1501504 | 1501504 | 0 | 7 | 7 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `253.0008`, `253.0009`, `253.0010`, `253.0011`, `253.0012`, `253.0013`, `253.0021`, `253.0022`, `253.0023`, `253.0024`
- Real stage-entry fishgroup examples: `253.0001`, `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0014`, `253.0015`, `253.0016`
- Bridge fishgroups excluded from stage-entry windows: `253.0008`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 40 | 40 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 7

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 7 | Hatchery:7 | S21 Viðareiði:7 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 7 | 0 | Hatchery:7 | S21 Viðareiði:7 | Unknown:7 |
| Reachable outside descendants | 20 | 0 | Hatchery:20 | S21 Viðareiði:20 | Unknown:20 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 7; latest holder in selected component: 7; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| A01 | 1C4BC069-2B03-4038-9775-1FB3D8C8F915 | `D7FEEB8B-4466-49D2-8712-F93CFFEE8B22` | `D7FEEB8B-4466-49D2-8712-F93CFFEE8B22` | yes | 128927 | 560.52 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| A05 | 4EDA3C9E-DD86-4EB0-88B7-FC496F829F2D | `9B19197C-0897-4B05-8631-5399F6777F48` | `9B19197C-0897-4B05-8631-5399F6777F48` | yes | 148789 | 648.47 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| B07 | 979D7540-BF0A-4F0A-A706-CE4D18A76C4E | `4DD518AD-8D6E-4F15-A613-8B7379E493D1` | `4DD518AD-8D6E-4F15-A613-8B7379E493D1` | yes | 138550 | 838.66 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| B08 | 87D8F67D-D75C-422D-BF4D-DCEA87940B88 | `DE94111B-48FA-4FB0-ACF4-0A5388E638C0` | `DE94111B-48FA-4FB0-ACF4-0A5388E638C0` | yes | 155243 | 908.0 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| B09 | 1F21A2B3-8C7A-45BD-8B02-9C6B2CF557CF | `4C070A50-B031-4A99-A146-14CC57A2FE02` | `4C070A50-B031-4A99-A146-14CC57A2FE02` | yes | 81343 | 633.68 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| B10 | AA073C42-72C4-48E2-851E-F12650E119B5 | `8AA57646-53D3-43E0-B4EE-37A9E29E5ECA` | `8AA57646-53D3-43E0-B4EE-37A9E29E5ECA` | yes | 109748 | 909.13 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| B11 | 8F8FE5FE-D339-47A0-AC53-D98171366809 | `67E48B30-FF8B-496A-AB00-D5750A71F43A` | `67E48B30-FF8B-496A-AB00-D5750A71F43A` | yes | 124185 | 1049.44 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)