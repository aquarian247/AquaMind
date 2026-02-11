# Semantic Migration Validation Report

- Component key: `EDF931F2-51CC-4A10-9002-128E7BF8067C`
- Batch: `Stofnfiskur Juni 24` (id=374)
- Populations: 145
- Window: 2024-06-05 13:14:06 → 2025-12-18 11:51:16

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3927 | 3927 | 0.00 |
| Feeding kg | 556670.04 | 556670.04 | 0.00 |
| Mortality events | 3931 | 3700 | 231.00 |
| Mortality count | 233640 | 233640 | 0.00 |
| Mortality biomass kg | 0.00 | 3524.23 | -3524.23 |
| Culling events | 34 | 34 | 0.00 |
| Culling count | 198827 | 198827 | 0.00 |
| Culling biomass kg | 5968603.90 | 5968603.90 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 64 | 64 | 0.00 |
| Growth samples | 12 | 12 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 432467
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 30 total, 26 bridge-classified, 2 same-stage superseded-zero, 2 short-lived orphan-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 57.
- Fishgroup classification: 48 temporary bridge fishgroups, 31 real stage-entry fishgroups, 48 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1708576 | 0 | 1708576 | 1708576 | 1.0 | 1.0 | 2024-06-05 | 2024-06-07 | 12 | 12 | 0 | 12 | 12 |
| Fry | 502720 | 0 | 502720 | 502720 | 1.0 | 1.0 | 2024-08-14 | 2024-08-16 | 12 | 12 | 0 | 12 | 12 |
| Parr | 788597 | 0 | 1477488 | 3593930 | 4.56 | 2.43 | 2024-11-26 | 2024-11-28 | 3 | 3 | 3 | 27 | 49 |
| Smolt | 150721 | 0 | 420066 | 820719 | 5.45 | 1.95 | 2025-04-11 | 2025-04-13 | 2 | 2 | 2 | 23 | 28 |
| Post-Smolt | 109170 | 705228 | 1668421 | 3349378 | 30.68 | 2.01 | 2025-05-15 | 2025-05-17 | 2 | 2 | 0 | 41 | 44 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1760038 | 177185 | -1582853 | 12 | 12 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | WARN: stage drop exceeds total known removals by 1150386 |
| Fry -> Parr | 73827 | 92117 | 18290 | 3 | 3 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | ALERT: population increases without mixed-batch composition |
| Parr -> Smolt | 50246 | 32799 | -17447 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 14528 | 14528 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0025`, `242.0026`, `242.0028`, `242.0029`, `242.0030`, `242.0031`, `242.0032`, `242.0033`, `242.0035`, `242.0036`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0008`, `242.0009`, `242.0010`, `242.0011`
- Bridge fishgroups excluded from stage-entry windows: `242.0030`, `242.0033`, `242.0039`, `242.0063`, `242.0064`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 145 | 145 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1760038 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 59

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 47 | Hatchery:47 | S03 Norðtoftir:47 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 59 | 0 | Hatchery:59 | S03 Norðtoftir:59 | Unknown:59 |
| Reachable outside descendants | 70 | 0 | Hatchery:70 | S03 Norðtoftir:70 | Unknown:70 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 2; latest holder outside selected component: 4; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1801 | 1FA0F0B4-625A-42AA-B8CC-17FF3EA3A8A2 | `50CE6E35-11B5-4E5D-A861-187A553883EC` | `FB0543E1-7C5E-404C-926B-C0D02C508D50` | no | 173781 | 28788.5 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1802 | 8197B471-F78A-47B5-A21E-BFE8050DE65E | `0A4707EC-7595-4379-9482-01452694C719` | `3D809DA5-A0E1-4288-B4D1-FF452F65BBE0` | no | 129743 | 32316.7 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1803 | 1D403F77-D5CE-4B95-A74F-761E26288A30 | `A81ADECE-0FB0-4BD1-B7B8-EAE0157E110E` | `B8A5C85A-FFA4-4A44-9091-948C858D43E5` | no | 186960 | 24019.3 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1804 | E444A0AE-CCBE-4693-97D2-6EA8FD98D096 | `B46EC408-925F-41AB-BB62-745F3E933BF9` | `052082DE-BC21-4AD3-99DB-39D1E37BD48C` | no | 140709 | 27670.7 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1805 | B819646E-DB90-4496-B47D-43ABAB1CC08E | `2BE6BA19-9314-4D11-9840-F01EFBC5CC07` | `2BE6BA19-9314-4D11-9840-F01EFBC5CC07` | yes | 104299 | 69928.1 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1808 | 641B7238-AC50-4FB8-8DE7-4381FF67FECD | `32738DAF-9713-46DA-911F-C756C9170FA6` | `32738DAF-9713-46DA-911F-C756C9170FA6` | yes | 152968 | 72522.9 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | FAIL | Positive stage transition deltas without mixed-batch composition rows: 1 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, and short-lived orphan-zero rows: 0 (threshold: 2) |
- Overall gate result: FAIL (enforced)