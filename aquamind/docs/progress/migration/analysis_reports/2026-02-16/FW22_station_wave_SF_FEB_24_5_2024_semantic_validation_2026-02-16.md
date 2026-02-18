# Semantic Migration Validation Report

- Component key: `1E81696F-1749-4036-945B-0290B466B32C`
- Batch: `SF FEB 24` (id=484)
- Populations: 77
- Window: 2024-02-15 14:37:52 → 2025-05-14 09:42:05

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 978 | 978 | 0.00 |
| Feeding kg | 87744.83 | 87744.83 | 0.00 |
| Mortality events | 1655 | 1648 | 7.00 |
| Mortality count | 748419 | 748419 | 0.00 |
| Mortality biomass kg | 0.00 | 20178.45 | -20178.45 |
| Culling events | 537 | 537 | 0.00 |
| Culling count | 185470 | 185470 | 0.00 |
| Culling biomass kg | 12915373.77 | 12915373.68 | 0.09 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 47 | 47 | 0.00 |
| Growth samples | 106 | 106 | 0.00 |
| Health journal entries | 91 | 91 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 933889
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/4 bridge-aware (50.0%), 2/4 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 3 total, 3 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 25.
- Fishgroup classification: 9 temporary bridge fishgroups, 48 real stage-entry fishgroups, 9 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1190000 | 0 | 1259955 | 1259955 | 1.06 | 1.0 | 2024-02-15 | 2024-02-17 | 36 | 36 | 0 | 40 | 40 |
| Fry | 741406 | 0 | 741406 | 741406 | 1.0 | 1.0 | 2024-05-21 | 2024-05-23 | 6 | 6 | 0 | 6 | 6 |
| Parr | 1012263 | 0 | 1073465 | 2033709 | 2.01 | 1.89 | 2024-09-05 | 2024-09-07 | 3 | 3 | 0 | 14 | 17 |
| Smolt | 203234 | 0 | 541139 | 541139 | 2.66 | 1.0 | 2024-11-12 | 2024-11-14 | 2 | 2 | 0 | 3 | 3 |
| Post-Smolt | 338898 | 0 | 600785 | 1176843 | 3.47 | 1.96 | 2025-02-11 | 2025-02-13 | 1 | 1 | 0 | 11 | 11 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1190000 | 741406 | -448594 | 6 | 6 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 225951 | 225951 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 6) | OK |
| Parr -> Smolt | 67732 | 67732 | 0 | 2 | 2 | yes | Bridge-aware (direct edge linkage; linked sources: 2) | OK |
| Smolt -> Post-Smolt | 203234 | 338898 | 135664 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `245.0047`, `245.0049`, `245.0051`, `245.0053`, `245.0054`, `245.0055`, `245.0057`, `245.0058`, `245.0059`
- Real stage-entry fishgroup examples: `245.0001`, `245.0002`, `245.0003`, `245.0004`, `245.0006`, `245.0007`, `245.0008`, `245.0010`, `245.0011`, `245.0012`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 77 | 77 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1055139 |
| Smolt | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 38

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 35 | Hatchery:35 | FW22 Applecross:35 |
| SourcePopBefore -> SourcePopAfter | 3 | Hatchery:3 | FW22 Applecross:3 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 38 | 0 | Hatchery:38 | FW22 Applecross:38 | Unknown:38 |
| Reachable outside descendants | 41 | 0 | Hatchery:41 | FW22 Applecross:41 | Unknown:41 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)