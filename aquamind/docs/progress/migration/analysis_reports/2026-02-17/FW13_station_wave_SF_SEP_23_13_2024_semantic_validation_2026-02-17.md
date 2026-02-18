# Semantic Migration Validation Report

- Component key: `AA69BFC2-4B6C-4455-844B-0296B5B12A1B`
- Batch: `SF SEP 23 13` (id=516)
- Populations: 51
- Window: 2023-09-28 09:00:00 → 2024-03-06 13:03:05

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2330 | 2330 | 0.00 |
| Feeding kg | 856.06 | 856.06 | 0.00 |
| Mortality events | 2525 | 2390 | 135.00 |
| Mortality count | 124383 | 124383 | 0.00 |
| Mortality biomass kg | 0.00 | 41.84 | -41.84 |
| Culling events | 97 | 96 | 1.00 |
| Culling count | 699199 | 699199 | 0.00 |
| Culling biomass kg | 1171666.50 | 1171666.50 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 192 | 192 | 0.00 |
| Growth samples | 168 | 168 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 823582
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 27.
- Fishgroup classification: 0 temporary bridge fishgroups, 25 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 823580 | 0 | 1645935 | 1713135 | 2.08 | 1.04 | 2023-09-28 | 2023-09-30 | 24 | 24 | 0 | 50 | 50 |
| Fry | 30720 | 0 | 30720 | 30720 | 1.0 | 1.0 | 2024-02-21 | 2024-02-23 | 1 | 1 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 30720 | 30720 | 0 | 1 | 1 | yes | Bridge-aware (direct edge linkage; linked sources: 1) | OK |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `2413.0002`, `2413.0003`, `2413.0004`, `2413.0005`, `2413.0006`, `2413.0007`, `2413.0008`, `2413.0009`, `2413.0010`, `2413.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 51 | 51 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 0

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 0 | 0 | - | - | - |
| Reachable outside descendants | 0 | 0 | - | - | - |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)