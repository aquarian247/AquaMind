# Migration Handover Document - 2026-01-22

## 🎯 BREAKTHROUGH: Batch Identification Solved

**We found the true biological batch identifier in FishTalk.**

### The Discovery

The `dbo.Ext_Inputs_v2` table tracks **egg inputs/deliveries** from suppliers - this is the biological origin of batches, NOT the project tuple.

### Why This Matters

| Previous Approach | Problem | New Approach |
|-------------------|---------|--------------|
| Project tuple `(ProjectNumber, InputYear, RunningNumber)` | Administrative/financial - mixes multiple year-classes | `Ext_Inputs_v2` tracks actual egg deliveries |
| Batch 326 (project 1/24/58) | Spans 721 days, 5 different year-classes, biologically impossible | Input-based batches have 20-275 day spans |
| PopulationName parsing | Only 43-83% extraction | Direct `InputName` field = 100% |

---

## 📋 Required Reading (In Order)

1. **FISHTALK_SCHEMA_ANALYSIS.md** - Section 7 (NEW): Complete Ext_Inputs_v2 analysis
2. **MIGRATION_LESSONS_LEARNED.md** - "MAJOR DISCOVERY: Ext_Inputs_v2 Table" section at bottom
3. **DATA_MAPPING_DOCUMENT.md** - Section 3.0.0: NEW RECOMMENDED APPROACH

Optional context:
- **MIGRATION_CANONICAL.md** - Overall migration runbook
- **data_model.md** lines 314-321 - Mixed batch concept in AquaMind

---

## 🔑 Key Technical Details

### Ext_Inputs_v2 Table Structure

```sql
-- Query to identify biological batches
SELECT 
    i.InputName,           -- Batch name like "Stofnfiskur S21 okt 25", "BM Jun 24"
    i.InputNumber,         -- Numeric identifier
    i.YearClass,           -- Year class (2025, 2024, etc.)
    COUNT(DISTINCT i.PopulationID) as pop_count,
    MIN(i.StartTime) as earliest,
    MAX(i.StartTime) as latest,
    DATEDIFF(day, MIN(i.StartTime), MAX(i.StartTime)) as span_days,
    SUM(i.InputCount) as total_fish
FROM dbo.Ext_Inputs_v2 i
WHERE i.InputName IS NOT NULL AND i.YearClass IS NOT NULL
GROUP BY i.InputName, i.InputNumber, i.YearClass
ORDER BY total_fish DESC
```

### Batch Key Formula

**`InputName + InputNumber + YearClass`** = One biological batch

### Sample Valid Batches (from actual FishTalk data)

| InputName | InputNumber | YearClass | Populations | Span (days) | Fish |
|-----------|-------------|-----------|-------------|-------------|------|
| 22S1 LHS | 2 | 2021 | 317 | 42 | 6.9M |
| Heyst 2023 | 1 | 2023 | 108 | 275 | 6.3M |
| Vár 2025 | 1 | 2025 | 104 | 204 | 6.3M |
| Stofnfiskur Aug 22 | 3 | 2022 | 40 | 21 | 5.1M |
| Rogn okt 2023 | 3 | 2023 | 567 | 19 | 4.7M |

### Naming Convention Patterns in InputName

| Pattern | Example | Meaning |
|---------|---------|---------|
| Supplier + Strain + Date | "Stofnfiskur S21 okt 25" | Stofnfiskur, S21 strain, Oct 2025 |
| Season + Year | "Heyst 2023", "Vár 2024" | Harvest/Spring (Faroese) |
| Strain Code | "22S1 LHS", "16S0 SF" | Year+Season+Code |
| Norwegian month | "Rogn okt 2023" | Roe October 2023 |

---

## 🧬 Domain Context (from user)

1. **A batch is a biological cohort** - fish from a single egg fertilization event
2. **Geography constraint**: A batch stays in ONE station → ONE sea area (never changes geography)
3. **Lifecycle stages**: Egg&Alevin (~90 days) → Fry (~90 days) → Parr (~90 days) → Smolt (~90 days) → Post-Smolt (~90 days) → Adult (300-450 days)
4. **Total lifecycle**: ~2-2.5 years
5. **Expected batch size**: 1-3 million fish
6. **"Árgangur"** (Faroese for "year-class") shown in FishTalk exports IS the batch identifier - comes from `Ext_Inputs_v2.InputName`

---

## 📁 Key Files

### Documentation
- `/aquamind/docs/progress/migration/FISHTALK_SCHEMA_ANALYSIS.md` - Section 7
- `/aquamind/docs/progress/migration/MIGRATION_LESSONS_LEARNED.md` - Bottom section
- `/aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` - Section 3.0.0

### Scripts (existing)
- `/scripts/migration/bulk_extract_fishtalk.py` - Bulk CSV extraction (needs Ext_Inputs_v2 added)
- `/scripts/migration/project_based_stitching_report.py` - Current stitching (to be replaced)
- `/scripts/migration/pilot_migrate_project_batch.py` - Migration script (needs update)

### Analysis Scripts Created This Session
- `/scripts/migration/tools/analyze_batch_cohorts.py` - Time-gap/stage analysis
- `/scripts/migration/tools/analyze_yearclass_from_names.py` - Name parsing analysis
- `/scripts/migration/tools/validate_yearclass_approach.py` - Dataset-wide validation

### Data Files
- `/scripts/migration/data/extract/populations.csv` - Population data
- `/scripts/migration/output/project_stitching/project_batches.csv` - Project-based analysis
- `/scripts/migration/output/project_stitching/project_population_members.csv` - Population names

---

## ✅ Implementation Tasks

### Phase 1: Extract Ext_Inputs_v2
1. Add `Ext_Inputs_v2` to `bulk_extract_fishtalk.py`
2. Extract to CSV: `ext_inputs.csv`

### Phase 2: Build Input-Based Stitching Report
1. Create `input_based_stitching_report.py` (new script)
2. Group populations by `(InputName, InputNumber, YearClass)`
3. Output: `input_batches.csv` with batch statistics

### Phase 3: Validate
1. Verify each batch has single geography (station + area)
2. Verify stage progression is biologically valid
3. Verify time span < 900 days
4. Verify fish count 1-3M per batch

### Phase 4: Update Migration
1. Modify `pilot_migrate_project_batch.py` to accept Input-based batch keys
2. Or create new `pilot_migrate_input_batch.py`

---

## 🔌 Database Connection

FishTalk SQL Server connection (from `migration_config.json`):
- Server: `192.168.1.3`
- Database: `FishTalk`
- User: `sa`
- Password: In config file

---

## ⚠️ Known Issues

1. **Some Input batches have long spans** (e.g., "FO Gen 2" = 1706 days) - these may be broodstock or special cases
2. **PopulationAttributes.YearClass** is NOT the same as Ext_Inputs_v2.YearClass - it's an EAV table with only year values
3. **PublicTransfers** is broken since Jan 2023 - do not use
4. **SubTransfers** only tracks within-environment moves, not FW→Sea handoffs

---

## 📝 Session Notes

- Session had stability/stalling issues (possible Claude datacenter issue)
- All critical findings documented in the files above
- The `Ext_Inputs_v2` discovery was made by querying FishTalk directly via sqlcmd
- The "Árgangur" column the user saw in FishTalk exports corresponds to `InputName` + `YearClass`

---

**Document Created:** 2026-01-22  
**Status:** Ready for implementation
