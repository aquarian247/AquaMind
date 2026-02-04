# FishTalk Batch Overview (CSV-derived)

Batch key: `Vár 2024|1|2024`

- Populations: 196
- Containers: 136
- Time span: 2024-02-19 -> 2025-05-23

## Stage Rollup

| Stage | Stage name | Pops | Containers | Start | End | Entry count | Exit count | Avg wt start (g) | Avg wt end (g) | Feed kg | Mortality count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adult | Ongrowing | 94 | 38 | 2024-02-19 | 2025-05-23 | 5303414 | 5216364 | 413.2 | 907.4 | 2927906.2 | 90435 |
| Unknown | Unknown | 102 | 102 | 2024-02-19 | 2024-06-28 | 5860229 | 5860229 | 403.7 | 403.7 | 0.0 | 0 |

## Stage Transition Diagram

```mermaid
flowchart LR
  Adult
```

## Linked Batch Candidates (via PopulationLink)

_No linked batches with Ext_Inputs_v2 rows were found._

Linked population details are in `linked_population_candidates.csv`.

Egg-origin candidate batches (with geography/time flags) are in `egg_origin_candidates.csv`.

## Egg-Origin Candidate Batches (Heuristic)

_No candidates passed geo + FW filters. See rejected list below._

### Rejected Candidates (Reason)

| Batch key | Geo match | FW env % | Days to sea | Stations | Linked pops | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| LHS FEB 23|2|2024 | unknown | 100.0 | 363 | 1 | 98 | geo_unknown |

## Stage Durations (days)

| Stage | Interval count | Min | Median | Max | Avg |
| --- | --- | --- | --- | --- | --- |
| Adult | 94 | 0.0 | 0.0 | 364.5 | 23.6 |
| Unknown | 102 | 0.0 | 0.0 | 0.0 | 0.0 |

Detailed durations per population/container are in `stage_durations.csv`.
Aggregated per-container durations are in `stage_container_durations.csv`.

## Growth Sample Weights (AvgWeight)

min=982g, median=4570g, max=7863g, n=16

## Data Gaps / Notes

- Stage rollup uses population_stages.csv; if stage entries are sparse (e.g., only Ongrowing), the diagram will collapse to one stage.
- Stage changes prefer operation_stage_changes.csv when present; fallback is population_stages.csv.
- PopulationLink edges touching this batch: 98 (linked outside batch: 98; link depth=2).
- Some populations have identical StartTime/EndTime in populations.csv, which yields zero-length intervals; use per-container aggregation to interpret stage occupancy.
- Linked populations without Ext_Inputs_v2 rows can be inspected in linked_population_candidates.csv (PopulationName/InputYear hints).
- Feed totals are derived from feeding_actions.csv (grams -> kg).
- Mortality totals are derived from mortality_actions.csv.
- Treatments, lice, and health journal records are not available in the current CSV extract set.
- Container lists per stage are written to stage_rollup.csv for detailed inspection.

## Next Steps (Egg-Origin Trace)

1) Generate/inspect `linked_population_candidates.csv` (run with --include-linked-populations) for FW hints (PopulationName / InputYear / Fishgroup / container names).
2) If no Ext_Inputs_v2 rows exist for linked populations, parse `ext_populations.csv` PopulationName to infer supplier + year-class, then search Ext_Inputs_v2 for matching InputName/YearClass.
3) Filter candidate FW batches by container ProdStage (from grouped_organisation.csv) to ensure FW vs SEA separation.
4) Use OperationProductionStageChange + population_stages to validate FW stage progression (Egg→Fry→Parr→Smolt) before linking to sea batch.
5) Confirm container timelines align with FW→Sea transfer windows (populations Start/EndTime and SubTransfers edges).
