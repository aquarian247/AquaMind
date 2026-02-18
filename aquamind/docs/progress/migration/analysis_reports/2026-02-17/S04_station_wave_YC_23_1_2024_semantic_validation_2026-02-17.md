# Semantic Migration Validation Report

- Component key: `391702AA-EBBA-49D0-8718-C4F03176019A`
- Batch: `YC 23` (id=547)
- Populations: 22
- Window: 2024-04-17 16:15:20 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-18 09:21:37.054927, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 436 | 436 | 0.00 |
| Feeding kg | 35808.78 | 35808.78 | -0.00 |
| Mortality events | 233 | 229 | 4.00 |
| Mortality count | 491 | 491 | 0.00 |
| Mortality biomass kg | 0.00 | 1564.36 | -1564.36 |
| Culling events | 8 | 8 | 0.00 |
| Culling count | 3820 | 3820 | 0.00 |
| Culling biomass kg | 15443207.00 | 15443207.00 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 4311
- Stage-entry window used for transition sanity: 2 day(s)
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 2 total, 1 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 9.
- Fishgroup classification: 4 temporary bridge fishgroups, 2 real stage-entry fishgroups, 4 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Fry | 6356 | 2922 | 9422 | 19664 | 3.09 | 2.09 | 2024-04-17 | 2024-04-19 | 2 | 2 | 0 | 20 | 22 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0003`, `241.0010`, `241.0011`, `241.0012`
- Real stage-entry fishgroup examples: `241.0002`, `241.0006`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 22 | 22 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 3

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 3 | Hatchery:3 | S04 Húsar:3 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 3 | 0 | Hatchery:3 | S04 Húsar:3 | Unknown:3 |
| Reachable outside descendants | 5 | 0 | Hatchery:5 | S04 Húsar:5 | Unknown:5 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 807 | D93B55E5-F1A7-4D8B-B299-BEFA5952178B | `82120276-6CDE-46A2-A39B-7FDA62A50A44` | `82120276-6CDE-46A2-A39B-7FDA62A50A44` | yes | 369 | 4693.93 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |
| 808 | 2CE3F757-95B1-4969-8161-66E1231F5414 | `0AC1E07D-19FB-4161-8E70-DB88421714BA` | `0AC1E07D-19FB-4161-8E70-DB88421714BA` | yes | 379 | 5030.7 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |
| 809 | 9692C511-0B7B-4D27-A40B-93BF32AF1536 | `BBA60759-93F2-421C-BBE0-54B8B5521456` | `BBA60759-93F2-421C-BBE0-54B8B5521456` | yes | 371 | 4939.77 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |
| 810 | 8937623C-5C23-474A-9645-574E37EA553B | `DE3B5699-732C-4771-8FFE-AB2D2036D412` | `DE3B5699-732C-4771-8FFE-AB2D2036D412` | yes | 323 | 4570.99 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |
| 811 | 3CC6BBA2-174C-4CD7-BF01-68963FB6DB5F | `87EDDDE0-9B98-41F5-AA50-FB9A2B4C96DE` | `87EDDDE0-9B98-41F5-AA50-FB9A2B4C96DE` | yes | 368 | 4988.67 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |
| 812 | 5C9A3CCF-65CF-4E4C-B7AE-B55845ED3A2E | `647D5D0F-A9CD-47A9-A3E8-E8278FD6789D` | `647D5D0F-A9CD-47A9-A3E8-E8278FD6789D` | yes | 339 | 4389.72 | 2026-01-22 00:00:00 | S04 Húsar | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)