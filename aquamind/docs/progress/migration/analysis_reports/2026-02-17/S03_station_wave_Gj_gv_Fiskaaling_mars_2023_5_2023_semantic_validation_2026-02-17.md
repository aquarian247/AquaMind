# Semantic Migration Validation Report

- Component key: `61F28915-834B-471A-A1B9-64B1A2689588`
- Batch: `Gjógv/Fiskaaling mars 2023` (id=531)
- Populations: 65
- Window: 2023-11-27 10:42:09 → 2024-12-10 14:01:45

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1612 | 1612 | 0.00 |
| Feeding kg | 320026.63 | 320026.62 | 0.00 |
| Mortality events | 1672 | 1433 | 239.00 |
| Mortality count | 14796 | 14796 | 0.00 |
| Mortality biomass kg | 0.00 | 1483.91 | -1483.91 |
| Culling events | 3 | 3 | 0.00 |
| Culling count | 32617 | 32617 | 0.00 |
| Culling biomass kg | 1215308.00 | 1215308.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 33 | 33 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 47413
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 3 total, 2 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 26.
- Fishgroup classification: 17 temporary bridge fishgroups, 5 real stage-entry fishgroups, 17 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Parr | 234990 | 0 | 892631 | 1887428 | 8.03 | 2.11 | 2023-11-27 | 2023-11-29 | 2 | 2 | 0 | 17 | 18 |
| Smolt | 171042 | 0 | 686837 | 1165516 | 6.81 | 1.7 | 2024-03-06 | 2024-03-08 | 2 | 2 | 0 | 17 | 18 |
| Post-Smolt | 90064 | 0 | 1241821 | 2064986 | 22.93 | 1.66 | 2024-05-23 | 2024-05-25 | 1 | 1 | 0 | 28 | 29 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Parr -> Smolt | 135990 | 133755 | -2235 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 71817 | 71817 | 0 | 1 | 1 | yes | Bridge-aware (direct edge linkage; linked sources: 1) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `235.0006`, `235.0007`, `23A.0002`, `23A.0003`, `23B.0012`, `23B.0013`, `23B.0022`, `23B.0023`, `23B.0024`, `23B.0025`
- Real stage-entry fishgroup examples: `235.0003`, `235.0004`, `23B.0007`, `23B.0008`, `23B.0017`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 65 | 65 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 15

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 15 | Hatchery:15 | S03 Norðtoftir:15 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 15 | 0 | Hatchery:15 | S03 Norðtoftir:15 | Unknown:15 |
| Reachable outside descendants | 15 | 0 | Hatchery:15 | S03 Norðtoftir:15 | Unknown:15 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)