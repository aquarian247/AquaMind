# Semantic Migration Validation Report

- Component key: `36D7DE38-D6C9-4CB7-9FF7-64273124A605`
- Batch: `Stofnfiskur S-21 juni24 - Summar 2024` (id=1349)
- Populations: 381
- Window: 2024-06-12 12:55:24 → 2025-11-25 18:22:47

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3841 | 3842 | -1.00 |
| Feeding kg | 378159.61 | 378166.61 | -7.00 |
| Mortality events | 4380 | 3614 | 766.00 |
| Mortality count | 243947 | 243947 | 0.00 |
| Mortality biomass kg | 0.00 | 3612.60 | -3612.60 |
| Culling events | 195 | 195 | 0.00 |
| Culling count | 223082 | 223082 | 0.00 |
| Culling biomass kg | 3895655.96 | 3895656.02 | -0.06 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 156 | 156 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 105944 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 467029
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/5 bridge-aware (80.0%), 1/5 entry-window (20.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 165 total, 50 bridge-classified, 104 same-stage superseded-zero, 0 short-lived orphan-zero, 11 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 244.
- Fishgroup classification: 137 temporary bridge fishgroups, 28 real stage-entry fishgroups, 137 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1507478 | 0 | 1507478 | 1507478 | 1.0 | 1.0 | 2024-06-12 | 2024-06-14 | 7 | 7 | 0 | 7 | 12 |
| Fry | 1467435 | 0 | 2101047 | 2180175 | 1.49 | 1.04 | 2024-08-30 | 2024-09-01 | 6 | 6 | 3 | 10 | 25 |
| Parr | 997561 | 0 | 1324097 | 7296008 | 7.31 | 5.51 | 2024-12-09 | 2024-12-11 | 6 | 6 | 4 | 140 | 239 |
| Smolt | 78961 | 0 | 969892 | 1607591 | 20.36 | 1.66 | 2025-02-27 | 2025-03-01 | 1 | 1 | 0 | 20 | 61 |
| Post-Smolt | 414931 | 0 | 974188 | 1658230 | 4.0 | 1.7 | 2025-07-08 | 2025-07-10 | 8 | 8 | 5 | 39 | 44 |
| Adult | 37955 | 0 | 37955 | 37955 | 1.0 | 1.0 | 2024-08-31 | 2024-09-02 | 1 | 0 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1507478 | 1341103 | -166375 | 6 | 6 | yes | Bridge-aware (linked sources: 12) | OK |
| Fry -> Parr | 1701165 | 891722 | -809443 | 6 | 6 | yes | Bridge-aware (linked sources: 19) | WARN: stage drop exceeds total known removals by 342414 |
| Parr -> Smolt | 71095 | 35245 | -35850 | 1 | 1 | yes | Bridge-aware (linked sources: 2) | OK |
| Smolt -> Post-Smolt | 188958 | 55769 | -133189 | 8 | 8 | yes | Bridge-aware (linked sources: 18) | OK |
| Post-Smolt -> Adult | 414931 | 37955 | -376976 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0008`, `242.0009`, `242.0010`, `242.0011`, `242.0012`, `242.0013`, `242.0020`, `242.0021`, `242.0022`, `242.0023`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0014`, `242.0015`, `242.0016`, `242.0017`
- Bridge fishgroups excluded from stage-entry windows: `242.0008`, `242.0009`, `242.0010`, `242.0023`, `242.0024`, `242.0030`, `242.0031`, `242.0218`, `242.0219`, `242.0220`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 265 | 265 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Parr | 571663 |
| Post-Smolt | 419275 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `21E7F1C3-F509-41BE-AE39-EFEBE4113B7C` | Parr | 87623 | 87623 |
| `FF9BA8FD-E854-4976-B8EA-4ACA2F73E5B6` | Post-Smolt | 76933 | 76933 |
| `63B53510-054E-4794-A4D9-E787D7C9ACE8` | Post-Smolt | 62140 | 62140 |
| `DCC6D67D-4C49-4ADE-A7FD-C7A382195FEA` | Parr | 61094 | 61094 |
| `27E93685-E1E5-4C35-82F1-42535718E7E1` | Post-Smolt | 59144 | 59144 |

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
- Overall gate result: PASS (advisory)