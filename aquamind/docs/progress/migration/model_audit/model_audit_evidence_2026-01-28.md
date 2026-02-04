# Model Audit Evidence (from CSV extracts)

Source: scripts/migration/data/extract/ (CSV snapshot).

## Global evidence (Population scale vs input batches)

- Unique PopulationIDs in populations.csv: **349,311**
- Unique PopulationIDs in ext_inputs.csv: **24,205**
- Coverage: **6.9%** of PopulationIDs have Ext_Inputs_v2 rows
- Unique input batches (InputName + InputNumber + YearClass): **1,786**
- Populations per input batch: **min=1, max=970, avg=13.6**

Interpretation: Population rows are far more granular than biological batches; Ext_Inputs_v2 identifies only a subset tied to egg inputs.

## Single batch deep dive

Batch key used:
- InputName = `V\u00e1r 2024` (source uses an accented 'a')
- InputNumber = `1`
- YearClass = `2024`

Evidence (CSV-derived):

- Populations in Ext_Inputs_v2 for this batch: **98**
- Population rows matched in populations.csv: **98**
- Distinct containers: **38**
- Distinct project tuples (ProjectNumber/InputYear/RunningNumber): **42**
- Population time span (StartTime -> EndTime): **2024-02-19 15:29:44 -> 2025-05-23 00:04:16**

Population stage evidence:
- Population stage entries (population_stages.csv): **94**
- Stage entries per population: **94 populations have exactly 1 stage entry**
- Stage distribution: **Ongrowing = 94**

Snapshot evidence:
- Status snapshot rows (status_values.csv): **2,407**
- Status snapshots per population: **min=2, max=367, avg=24.6**

Linkage evidence:
- SubTransfers rows touching this batch: **68**
- PopulationLink rows touching this batch: **98**

Container concentration (top 5 by population count):
- C5F55EA4-2341-4BA7-AD4D-037A4238D8AE: 7
- 66428F7F-853E-4F10-8EC8-EA34C27D0372: 6
- 46089B82-628E-4861-987C-CC550F0AE5DE: 5
- 122093A7-70D6-4598-BF06-1496397E5099: 4
- 77E6DA6F-E99D-49FF-9500-E9D1BDE4D5D7: 4

Interpretation:
- A single input batch spans many populations and containers.
- Each population often has a single stage entry (Ongrowing), implying population ~= segment/instance, not lifecycle.
- Status values are dense time-series snapshots per population.
- SubTransfers/PopulationLinks demonstrate population-to-population lineage, further supporting population as an instance node in a movement graph.

## Second batch deep dive

Batch key used:
- InputName = `Heyst 2023`
- InputNumber = `1`
- YearClass = `2023`

Evidence (CSV-derived):

- Populations in Ext_Inputs_v2 for this batch: **108**
- Population rows matched in populations.csv: **108**
- Distinct containers: **38**
- Distinct project tuples (ProjectNumber/InputYear/RunningNumber): **48**
- Population time span (StartTime -> EndTime): **2023-08-24 11:58:17 -> 2025-02-17 00:49:42**

Population stage evidence:
- Population stage entries (population_stages.csv): **104**
- Stage entries per population: **104 populations have exactly 1 stage entry, 4 have 0**
- Stage distribution: **Ongrowing = 104**

Snapshot evidence:
- Status snapshot rows (status_values.csv): **2,466**
- Status snapshots per population: **min=2, max=372, avg=22.8**

Linkage evidence:
- SubTransfers rows touching this batch: **77**
- PopulationLink rows touching this batch: **111**

Container concentration (top 5 by population count):
- 303497F7-59DD-4638-9142-484A56E43B91: 8
- CF6DEC22-7323-4FB9-BC15-5A07674FAC41: 8
- EFED3B0D-E1AC-4329-B18A-DDB75E8DA852: 5
- A24D16B4-E012-4C86-86E4-A4DB281E8979: 5
- 38B31A51-1A7B-47D9-BFAA-D6F699A48E5A: 5

Interpretation:
- The batch again spans many populations and containers over a long time range.
- Stage evidence is sparse (0–1 entries per population) and concentrated in Ongrowing, reinforcing populations as segments.
- Status snapshots remain dense per population, consistent with time-series assignment data.
- Transfer and link edges continue to form a population-to-population lineage graph rather than a batch identity.
