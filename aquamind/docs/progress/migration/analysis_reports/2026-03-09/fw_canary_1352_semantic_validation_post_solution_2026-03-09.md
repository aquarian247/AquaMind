# Semantic Migration Validation Report

- Component key: `EF6EC682-7532-43DF-8D6B-1441ABFF504E`
- Batch: `Stofnfiskur desembur 2023 - Vár 2024` (id=1352)
- Populations: 543
- Window: 2023-12-06 14:25:06 → 2025-05-07 21:51:37

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4188 | 4188 | 0.00 |
| Feeding kg | 899673.99 | 899673.99 | 0.00 |
| Mortality events | 5859 | 5693 | 166.00 |
| Mortality count | 1516993 | 1516993 | 0.00 |
| Mortality biomass kg | 0.00 | 7356.39 | -7356.39 |
| Culling events | 14 | 14 | 0.00 |
| Culling count | 138532 | 138532 | 0.00 |
| Culling biomass kg | 2659837.30 | 2659837.30 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
| Growth samples | 434 | 434 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 110411 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1655525
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/5 bridge-aware (60.0%), 2/5 entry-window (40.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 240 total, 240 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 756.
- Fishgroup classification: 107 temporary bridge fishgroups, 62 real stage-entry fishgroups, 332 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500512 | 0 | 3500512 | 3500512 | 1.0 | 1.0 | 2023-12-06 | 2023-12-08 | 39 | 39 | 0 | 39 | 89 |
| Fry | 3308215 | 0 | 3308215 | 3308215 | 1.0 | 1.0 | 2024-03-07 | 2024-03-09 | 12 | 12 | 0 | 12 | 50 |
| Parr | 2196888 | 0 | 3581391 | 12119202 | 5.52 | 3.38 | 2024-05-28 | 2024-05-30 | 7 | 7 | 10 | 79 | 185 |
| Smolt | 127243 | 0 | 2228305 | 8018495 | 63.02 | 3.6 | 2024-08-16 | 2024-08-18 | 2 | 2 | 0 | 56 | 101 |
| Post-Smolt | 280469 | 0 | 2322977 | 8995034 | 32.07 | 3.87 | 2024-11-20 | 2024-11-22 | 2 | 2 | 0 | 117 | 118 |
| Adult | 29528 | 0 | 29528 | 29528 | 1.0 | 1.0 | 2024-03-08 | 2024-03-10 | 1 | 0 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 3500512 | 3308215 | -192297 | 12 | 12 | yes | Bridge-aware (linked sources: 39); lineage graph fallback used | OK |
| Fry -> Parr | 3308215 | 2196888 | -1111327 | 7 | 7 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 131300 | 127243 | -4057 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 127243 | 280469 | 153226 | 2 | 2 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Post-Smolt -> Adult | 280469 | 29528 | -250941 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0052`, `234.0053`, `234.0054`, `234.0055`, `234.0056`, `234.0057`, `234.0058`, `234.0059`, `234.0060`, `234.0061`
- Real stage-entry fishgroup examples: `234.0001`, `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`
- Bridge fishgroups excluded from stage-entry windows: `234.0066`, `234.0074`, `234.0075`, `234.0076`, `234.0078`, `234.0086`, `234.0087`, `234.0088`, `234.0089`, `234.0098`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 339 | 339 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Post-Smolt | 1972604 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `512EA333-27E1-4383-BC27-3CCCD862477B` | Post-Smolt | 99026 | 99026 |
| `462D370D-F891-45D1-9F4C-12BF7FBB21EF` | Post-Smolt | 93003 | 93003 |
| `EA785F12-00C0-4079-8D9B-F5243D518E7F` | Post-Smolt | 93003 | 93003 |
| `2AD93581-B262-40FA-87D0-8213F847CC03` | Post-Smolt | 86935 | 86935 |
| `315964AC-8F02-4AB3-868A-B53C7FCCE436` | Post-Smolt | 78577 | 78577 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 1

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 1 | Hatchery:1 | S24 Strond:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 1 | 0 | Hatchery:1 | S24 Strond:1 | Unknown:1 |
| Reachable outside descendants | 1 | 0 | Hatchery:1 | S24 Strond:1 | Unknown:1 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)