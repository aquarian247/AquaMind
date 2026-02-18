# Semantic Migration Validation Report

- Component key: `4A1E4829-7D62-4CBA-A8CF-274E1F611B6D`
- Batch: `Bakkafrost feb 2025` (id=521)
- Populations: 72
- Window: 2025-02-25 15:42:13 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 15:42:24.799160, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 137 | 137 | 0.00 |
| Feeding kg | 4133.75 | 4133.75 | -0.00 |
| Mortality events | 563 | 509 | 54.00 |
| Mortality count | 340424 | 340424 | 0.00 |
| Mortality biomass kg | 0.00 | 896.26 | -896.26 |
| Culling events | 1 | 1 | 0.00 |
| Culling count | 66814 | 66814 | 0.00 |
| Culling biomass kg | 668140.00 | 668140.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 9 | 9 | 0.00 |
| Growth samples | 3 | 3 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 407238
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/3 bridge-aware (100.0%), 0/3 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 29 total, 28 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 25.
- Fishgroup classification: 32 temporary bridge fishgroups, 6 real stage-entry fishgroups, 32 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 299995 | 0 | 299995 | 299995 | 1.0 | 1.0 | 2025-02-25 | 2025-02-27 | 1 | 1 | 0 | 1 | 1 |
| Fry | 323754 | 0 | 323754 | 323754 | 1.0 | 1.0 | 2025-05-12 | 2025-05-14 | 2 | 2 | 0 | 2 | 2 |
| Parr | 250941 | 0 | 870101 | 3136655 | 12.5 | 3.6 | 2025-08-06 | 2025-08-08 | 2 | 2 | 0 | 35 | 55 |
| Smolt | 123990 | 622197 | 622197 | 872322 | 7.04 | 1.4 | 2025-12-10 | 2025-12-12 | 1 | 1 | 0 | 5 | 14 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 299995 | 299995 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Parr | 299995 | 299995 | 0 | 2 | 2 | yes | Bridge-aware (direct edge linkage; linked sources: 2) | OK |
| Parr -> Smolt | 83661 | 74821 | -8840 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0005`, `252.0006`, `25A.0001`, `25A.0003`, `25A.0006`, `25A.0007`, `25A.0009`, `25A.0010`, `25A.0011`, `25A.0015`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `25A.0002`, `25A.0004`, `25A.0032`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 72 | 72 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 23

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 23 | Hatchery:23 | S16 Glyvradalur:23 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 23 | 0 | Hatchery:23 | S16 Glyvradalur:23 | Unknown:23 |
| Reachable outside descendants | 29 | 0 | Hatchery:29 | S16 Glyvradalur:29 | Unknown:29 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| D01 | A149E1A7-5A9B-4993-88B0-CEAD2E7C9A28 | `6D17832F-1167-452B-A4AD-7E6260201F48` | `6D17832F-1167-452B-A4AD-7E6260201F48` | yes | 220170 | 17238.3 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| D02 | B35798D6-0CEC-4877-AE42-22701F31DEF4 | `3034F5EE-40D0-4DBF-95EB-2E804066C510` | `3034F5EE-40D0-4DBF-95EB-2E804066C510` | yes | 210440 | 26704.8 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| D03 | 1C86F107-5D9C-405A-BEFE-8357A3C01352 | `61E5C6F5-EA1F-421F-8E36-574BD719F986` | `61E5C6F5-EA1F-421F-8E36-574BD719F986` | yes | 191587 | 15555.3 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)