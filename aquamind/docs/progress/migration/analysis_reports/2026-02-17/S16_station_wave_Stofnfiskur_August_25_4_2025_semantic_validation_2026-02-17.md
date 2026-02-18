# Semantic Migration Validation Report

- Component key: `369F6A08-849B-4AFE-BE6D-066DBCBADA91`
- Batch: `Stofnfiskur August 25` (id=524)
- Populations: 13
- Window: 2025-08-27 15:08:41 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 15:53:26.463098, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 271 | 123 | 148.00 |
| Mortality count | 56039 | 56039 | 0.00 |
| Mortality biomass kg | 0.00 | 0.46 | -0.46 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 56039
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 4.
- Fishgroup classification: 0 temporary bridge fishgroups, 13 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1800700 | 0 | 1800700 | 1800700 | 1.0 | 1.0 | 2025-08-27 | 2025-08-29 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1420973 | 1420973 | 1420973 | 1420973 | 1.0 | 1.0 | 2025-11-18 | 2025-11-20 | 8 | 8 | 0 | 8 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1800700 | 1420973 | -379727 | 8 | 6 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 323688 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `254.0001`, `254.0002`, `254.0003`, `254.0004`, `254.0005`, `254.0006`, `254.0007`, `254.0008`, `254.0009`, `254.0010`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 13 | 13 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 362660 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `2B09C81D-AD8B-4747-AD73-49CF96D67E6A` | Fry | 186595 | 186595 |
| `94270FEB-504B-468C-A04F-21CA3419F9F5` | Fry | 176065 | 176065 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 132926 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 6

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 1 | Hatchery:1 | S16 Glyvradalur:1 |
| SourcePopBefore -> SourcePopAfter | 5 | Hatchery:5 | S16 Glyvradalur:5 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 6 | 0 | Hatchery:6 | S16 Glyvradalur:6 | Unknown:6 |
| Reachable outside descendants | 6 | 0 | Hatchery:6 | S16 Glyvradalur:6 | Unknown:6 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 8; latest holder in selected component: 8; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| B01 | 3E702CD5-C6E4-42A1-9E65-52223ACA8BF7 | `B9D330F6-56F9-47D2-883C-2F23A3EE19C0` | `B9D330F6-56F9-47D2-883C-2F23A3EE19C0` | yes | 196988 | 360.69 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B02 | 25076E68-8B80-418B-BC15-9A94F2483D59 | `95D91E86-4791-4516-A653-9ABED3C2BE71` | `95D91E86-4791-4516-A653-9ABED3C2BE71` | yes | 200898 | 365.44 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B03 | E4D09445-B0F5-4708-A337-245D1FFF9183 | `94270FEB-504B-468C-A04F-21CA3419F9F5` | `94270FEB-504B-468C-A04F-21CA3419F9F5` | yes | 176065 | 338.5 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B04 | 86F8182E-8993-4C8F-993F-8561E9C1A27D | `51617952-2379-4902-B9A2-33B775A0C0C8` | `51617952-2379-4902-B9A2-33B775A0C0C8` | yes | 176105 | 331.34 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B05 | FA4D1CCA-7FEB-42A1-AA18-69581F9D6D70 | `2B09C81D-AD8B-4747-AD73-49CF96D67E6A` | `2B09C81D-AD8B-4747-AD73-49CF96D67E6A` | yes | 186595 | 341.79 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B06 | 038019A0-0CB1-471B-BC46-819E2FD03D3E | `32471BEE-AD6D-4528-BA46-C858C1ACB92C` | `32471BEE-AD6D-4528-BA46-C858C1ACB92C` | yes | 173042 | 329.39 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B07 | D43AB4C4-351A-4F1E-A39F-A52EB7191603 | `C7864C28-4868-4848-ACDC-55EBC00FCB6A` | `C7864C28-4868-4848-ACDC-55EBC00FCB6A` | yes | 151012 | 322.29 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| B08 | E3399BF6-0880-44F2-BCCB-DD5B4868B72C | `913043E1-FFEA-4455-A03B-07CA6775F105` | `913043E1-FFEA-4455-A03B-07CA6775F105` | yes | 160268 | 324.47 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)