# Semantic Migration Validation Report

- Component key: `5C2A7C3B-7222-4D47-BB12-0D0E318EAF21`
- Batch: `Stofnfiskur desembur 2023` (id=475)
- Populations: 348
- Window: 2023-12-06 14:25:06 → 2025-05-08 22:01:25

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4280 | 4280 | 0.00 |
| Feeding kg | 942052.78 | 942052.78 | 0.00 |
| Mortality events | 5975 | 5808 | 167.00 |
| Mortality count | 1517759 | 1517759 | 0.00 |
| Mortality biomass kg | 0.00 | 7579.83 | -7579.83 |
| Culling events | 14 | 14 | 0.00 |
| Culling count | 138532 | 138532 | 0.00 |
| Culling biomass kg | 2659837.30 | 2659837.30 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
| Growth samples | 446 | 446 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1656291
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 54 total, 36 bridge-classified, 18 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 92.
- Fishgroup classification: 102 temporary bridge fishgroups, 62 real stage-entry fishgroups, 102 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500512 | 0 | 3500512 | 3500512 | 1.0 | 1.0 | 2023-12-06 | 2023-12-08 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3308215 | 0 | 3308215 | 3308215 | 1.0 | 1.0 | 2024-03-07 | 2024-03-09 | 12 | 12 | 0 | 12 | 12 |
| Parr | 2196888 | 0 | 3581391 | 12119202 | 5.52 | 3.38 | 2024-05-28 | 2024-05-30 | 7 | 7 | 10 | 79 | 114 |
| Smolt | 127243 | 0 | 2228305 | 8016568 | 63.0 | 3.6 | 2024-08-16 | 2024-08-18 | 2 | 2 | 0 | 55 | 56 |
| Post-Smolt | 280469 | 0 | 2353043 | 8101996 | 28.89 | 3.44 | 2024-11-20 | 2024-11-22 | 2 | 2 | 0 | 109 | 127 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 3500512 | 3308215 | -192297 | 12 | 12 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 3308215 | 2196888 | -1111327 | 7 | 7 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 131300 | 127243 | -4057 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 496249 | 280469 | -215780 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0052`, `234.0053`, `234.0054`, `234.0055`, `234.0056`, `234.0057`, `234.0058`, `234.0059`, `234.0060`, `234.0061`
- Real stage-entry fishgroup examples: `234.0001`, `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`
- Bridge fishgroups excluded from stage-entry windows: `234.0066`, `234.0074`, `234.0075`, `234.0076`, `234.0078`, `234.0086`, `234.0087`, `234.0088`, `234.0089`, `234.0098`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 348 | 348 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 3308215 |
| Parr | 1585433 |
| Smolt | 2396891 |
| Post-Smolt | 2042930 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `10BCA575-B2A9-4032-B65F-2AF1A636BBC1` | Fry | 282507 | 282507 |
| `43664DC8-7CEE-4CD7-BD5B-B3E0DCE13EA6` | Fry | 281097 | 281097 |
| `F9F0AE68-2EB2-4293-A7EA-30EB9C7AED9E` | Fry | 281064 | 281064 |
| `A64CCE61-11A6-43E1-9451-018A4CC53E81` | Fry | 280032 | 280032 |
| `E50F7B81-E92F-4C76-93C5-8F6EC4CF5D9E` | Fry | 278754 | 278754 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500512 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 91

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 52 | Hatchery:52 | S24 Strond:52 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 91 | 0 | Hatchery:91 | S24 Strond:91 | Unknown:91 |
| Reachable outside descendants | 204 | 0 | Hatchery:204 | S24 Strond:204 | Unknown:204 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)