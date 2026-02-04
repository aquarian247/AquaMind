# Migration Lessons Learned (2026-01-21)

## Purpose
This document consolidates learnings from multiple migration sessions to clarify what works, what doesn't, and the definitive approach going forward.

---

## Timeline of Migration Approaches

| Date | Approach | Outcome |
|------|----------|---------|
| 2026-01-17 | UUID-based component stitching | ✅ Worked but arbitrary groupings |
| 2026-01-19 | 15-component pilot expansion | ⚠️ Discovered lifecycle/workflow issues |
| 2026-01-20 | Discovered PublicTransfers broken since Jan 2023 | 🔍 Key finding |
| 2026-01-21 (AM) | Proposed "Hybrid SubTransfers + Project Linking" | ❌ Over-linked batches (70M+ fish) |
| 2026-01-21 (PM) | **Project tuple = 1 batch** | ⚠️ Worked in many cases, later disproven |
| 2026-01-22 (EOD) | **Ext_Inputs_v2 input-based stitching** | ✅ Current direction |
| 2026-02-03 | Heuristic FW→Sea test + restricted full-lifecycle selection | ✅ Works for targeted QA, non-canonical |

---

## What IS Correct (Use This)

### 1. Batch Identification: Ext_Inputs_v2 (Input-Based)

**Primary batch key:** `InputName + InputNumber + YearClass` from `Ext_Inputs_v2`.

Key points:
- `Ext_Inputs_v2` tracks **egg deliveries** (biological origin).
- **InputName changes at FW→Sea**, so sea-phase batches (e.g., "Summar 2024") are valid sea-only analytics cohorts.
- Use **SubTransfers** for transfer workflows (within-environment). FW→Sea linkage still requires explicit logic.

Scripts:
```bash
python scripts/migration/tools/input_based_stitching_report.py \
  --output-dir scripts/migration/output/input_stitching

PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024" \
  --use-csv scripts/migration/data/extract/
```

**Legacy (deprecated):**
```bash
# Project-based batch migration (deprecated)
python scripts/migration/legacy/tools/pilot_migrate_project_batch.py \
  --project-key "1/25/1" \
  --skip-environmental  # Optional: skip slow environmental migration
```

### 2. ETL Approach with CSV Mode

**Bulk extract → CSV → migrate** is 7-10x faster than per-query SQL.

```bash
# Step 1: Extract once (~20-30 minutes)
python scripts/migration/tools/bulk_extract_fishtalk.py \
  --output scripts/migration/data/extract/

# Step 2: Migrate with --use-csv flag
python scripts/migration/tools/pilot_migrate_component.py \
  --component-key <uuid> --use-csv scripts/migration/data/extract/
```

### 3. Transfer Workflow Creation

**SubTransfers** is used for creating transfer workflows (physical fish movements), NOT for batch identification.

- Use `--use-subtransfers` flag in transfer migration
- Stage transition workflows derived from `OperationProductionStageChange`
- Lifecycle workflows consolidated to **one per batch stage transition** (not per population)

### 3.1 Population Count Conservation (Assignments)

**Use conservation-based counts for assignments to avoid double-counting.**

Rule of thumb:
- Seed counts from `Ext_Inputs_v2.InputCount`.
- Propagate via `SubTransfers.ShareCountFwd`.
- If conserved count is missing or resolves to **0** but a status snapshot is non‑zero, use the snapshot count.
- If a population is superseded by a **same‑stage** transfer, zero it to avoid double‑counting within that stage.

Reference: `DATA_MAPPING_DOCUMENT.md` → 3.2 (Container Assignment Mapping).

### 3.2 Full-Lifecycle Selection Guardrails (Heuristic Runs)

When running heuristic FW→Sea stitching, **always constrain** the full-lifecycle selection to prevent unrelated FW cohorts from being pulled into the batch:

- Use `--include-fw-batch '<target batch key>'`
- Set `--max-fw-batches 1`
- Set `--max-pre-smolt-batches 0`

This keeps the test batch focused on the target cohort + heuristic sea matches only.

### 4. Environmental Data with SQLite Index

For parallel environmental migration, build SQLite index first:

```bash
# Build index once
python scripts/migration/tools/build_environmental_sqlite.py \
  --input-dir scripts/migration/data/extract/ \
  --output-path scripts/migration/data/extract/environmental_readings.sqlite

# Run with parallel workers
python scripts/migration/tools/pilot_migrate_environmental_all.py \
  --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite \
  --workers 16
```

---

## What IS NOT Correct (Avoid These)

### ❌ 1. Project Tuple as Primary Batch Identifier

**Problem:** Project tuples are administrative and can mix multiple year‑classes.
They are **not reliable biological batch identifiers** in all cases.

**Do NOT use as the primary batch key** (unless Ext_Inputs_v2 is unavailable and
you explicitly cohort‑split by year‑class/time gaps).

### ❌ 2. Hybrid SubTransfers Chain Linking

**Problem:** Linking SubTransfers chains via shared project tuples caused **over-aggregation**.

**What happened:**
- SubTransfers creates chains within environments (FW-only, Sea-only)
- Attempted to link FW+Sea chains via project tuples
- Result: Batches with 70+ million fish (should be 1-3M)

**Root cause:** Transitive linking - Chain A shares project with Chain B, B shares with C, so A-B-C all get linked, even if they're different biological batches.

**Do NOT use:**
```bash
# WRONG - causes over-linking
python scripts/migration/legacy/tools/subtransfer_chain_stitching.py --link-by-project
python scripts/migration/tools/pilot_migrate_component.py --batch-id BATCH-00013
```

### ❌ 3. UUID-Based Component Keys (Legacy)

The original stitching used arbitrary UUID component keys from `scripts/migration/legacy/tools/population_stitching_report.py`. These don't correspond to biological batches.

**Use input-based stitching** via `Ext_Inputs_v2` and `pilot_migrate_input_batch.py`.

### ❌ 4. Per-Population Lifecycle Workflows

**Problem:** Creating one lifecycle workflow per population stage change caused "workflow explosion" (hundreds of workflows per batch).

**Fix:** Lifecycle workflows consolidated to one per batch stage transition.

### ❌ 5. PublicTransfers for FW→Sea Links

**Problem:** FishTalk's `PublicTransfers` table stopped recording FW-to-sea transfers since January 2023.

**Fix:** Don't rely on PublicTransfers for batch identity. Use `Ext_Inputs_v2` for batch keys and SubTransfers for within-environment workflows. FW→Sea linkage still requires explicit logic.

---

## Known Data Artifacts

### Long Duration Stage Transitions

**Symptom:** Lifecycle workflows spanning 6+ months (e.g., Egg→Fry workflow from March to October).

**Cause:** Legacy stitching (project tuple or multi‑cohort grouping) aggregates populations that entered a stage at different times. This is a **data artifact**, not a bug.

**Options:**
1. Accept as-is (reflects actual FishTalk data)
2. Cohort splitting (complex, changes batch identity)
3. Windowed workflows (more workflows, reduced extremes)

### Sparse Stage Data

Many FishTalk populations have only one stage recorded in `PopulationProductionStages`. Assignment timing becomes the primary signal for stage transitions.

### UI Stage Order Depends on Assignment Ordering

Lifecycle charts group assignments **in the order they are returned** by the assignments API. If the API orders by assignment date, stages can appear out of sequence. The backend now orders batch-filtered assignments by `lifecycle_stage.order` (fix applied 2026‑02‑03).

### Deprecated Halls Still Affect Historical Batches

If a batch historically used a hall that is now deprecated, that hall **still needs stage mapping**. Without it, the migration falls back to the **last** FishTalk stage and can collapse Egg/Alevin into Fry.

---

## Bug Fixes Applied During Migration

### 🐛 Feeding Percentage Numeric Overflow (Fixed 2026-01-21)

**Symptom:** `django.db.utils.DataError: numeric field overflow` when migrating feeding events.

**Root cause:** The `feeding_percentage` field in `FeedingEvent` is `decimal(8,6)`, which can only store values from -99.999999 to 99.999999. When FishTalk has feeding amounts much larger than biomass (edge cases with incorrect data), the calculated percentage `(amount_kg / biomass_kg) * 100` exceeded this limit.

**Fix applied:** Modified `apps/inventory/utils.py::calculate_feeding_percentage()` to cap the result at 99.99:

```python
# Calculate percentage and cap at 99.99 to prevent numeric overflow
percentage = (amount_kg / biomass_kg) * Decimal('100.0')
max_percentage = Decimal('99.99')
if percentage > max_percentage:
    percentage = max_percentage
```

**Impact:** Edge cases with bad source data (e.g., 425kg feed on 0.5kg biomass) are now handled gracefully instead of crashing the migration.

---

## Definitive Migration Pipeline

```bash
# 1. Clear migration DB (preserves users)
python scripts/migration/clear_migration_db.py

# 2. Clear stale ExternalIdMap entries (optional for clean replays)
python -c "
from apps.migration_support.models import ExternalIdMap
ExternalIdMap.objects.all().delete()
"

# 3. Generate input-based stitching report
python scripts/migration/tools/input_based_stitching_report.py \
  --output-dir scripts/migration/output/input_stitching

# 4. Migrate an input batch
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024" \
  --use-csv scripts/migration/data/extract/

# 5. Verify
python scripts/migration/tools/migration_counts_report.py
```

---

## Key Scripts Reference

| Script | Purpose | Use When |
|--------|---------|----------|
| `pilot_migrate_input_batch.py` | End-to-end input batch migration | **Primary migration script** |
| `input_based_stitching_report.py` | Generate input batch candidates | Identifying batches to migrate |
| `bulk_extract_fishtalk.py` | ETL extraction to CSV | Before migration (once) |
| `clear_migration_db.py` | Reset migration DB | Before clean runs |
| `migration_counts_report.py` | Verification counts | After each migration |

---

## Summary

| Aspect | Correct Approach | Wrong Approach |
|--------|------------------|----------------|
| **Batch ID** | Ext_Inputs_v2 (InputName + InputNumber + YearClass) | Project tuple as primary, UUID components |
| **Transfer workflows** | SubTransfers + consolidated lifecycles | Per-population workflows |
| **ETL** | Bulk CSV extraction | Per-query SQL |
| **Environmental** | SQLite index + parallel workers | Loading 5GB CSVs per worker |

**Bottom line:** Ext_Inputs_v2 is the biological batch identifier. Project tuple is administrative.

---

## 🚨 Critical Finding: Project Tuple Cohort Issue (2026-01-21 Evening)

**Status:** Historical context. This section documents why the project‑tuple approach was abandoned in favor of `Ext_Inputs_v2`.

### Problem Discovered

**Project tuples can span multiple biological cohorts.** Batch 326 (`FT-77E16BC3-24Q1-LHS`, project `1/24/58`) contains populations with:

| Population Start | Stage | Issue |
|-----------------|-------|-------|
| Oct 2023 | Parr | Cohort 1 |
| Jun 2024 | Alevin, Fry | Cohort 2 (8 months later!) |
| Aug 2024 | Alevin | Cohort 3 |
| Oct 2024 | Eye-egg | Cohort 4 |

**Symptom:** Container assignments show Egg&Alevin stages appearing AFTER Parr/Smolt stages - biologically impossible.

### Root Cause

FishTalk's project tuple `(ProjectNumber, InputYear, RunningNumber)` is an **administrative grouping** that can span multiple year-classes of fish, NOT a true biological batch identifier.

### Implication

The assumption "one project tuple = one batch" is **incorrect for some project tuples**. Not all 924 project tuples have this issue, but those that span >12 months likely do.

### Potential Solutions

1. **Time-based cohort splitting**: Group populations within a project tuple by their start time (e.g., 90-day windows)
2. **Stage-based filtering**: Only include populations that follow a valid lifecycle progression
3. **SubTransfers chain validation**: Use SubTransfers to verify actual fish movement links between populations
4. **Manual review**: Flag project tuples with >12 month span for manual review

### Quantitative Analysis

| Time Span | Count | % of Total | Risk |
|-----------|-------|------------|------|
| < 6 months | 35,752 | 67% | Low |
| 6-12 months | 6,766 | 13% | Medium |
| 12-24 months | 7,563 | 14% | **High** |
| > 24 months | 3,274 | 6% | **Critical** |

**All 15 batches in the dry-run had >700 day spans** - the `recommended_batches.csv` inadvertently selected problematic batches (those with 5+ stages are more likely to span multiple cohorts).

### Recommended Solution (Fallback): Time-Based Cohort Filtering

**Immediate action**: Modify `scripts/migration/legacy/tools/project_based_stitching_report.py` to:
1. Calculate population start time span per project tuple
2. Filter to project tuples with **<180 day span** (reduces problem batches significantly)
3. For longer spans, implement **90-day gap cohort splitting**

**Example**: Project `1/24/58` with 90-day gap threshold splits into:
- Cohort 1: Oct 2023 (1 pop, Parr only)
- Cohort 2: Apr-Nov 2024 (15 pops, Alevin→Ongrowing)
- Cohort 3: Mar-May 2025 (3 pops, Smolt/Ongrowing)
- Cohort 4: Sep-Oct 2025 (17 pops, Ongrowing)

### Status

**Confirmed issue** - Project tuple approach needs cohort filtering/splitting. Next session should implement the fix before continuing migration.

---

## 🎯 Solution Discovery: Year-Class Extraction from Population Names (2026-01-22)

**Status:** Fallback strategy. Use only when `Ext_Inputs_v2` is unavailable or for auxiliary FW→Sea linkage research.

### Key Finding

**FishTalk population names contain year-class information** that can be parsed to correctly identify biological cohorts. This provides a much more reliable batch identification method than time-gap splitting alone.

### Population Name Patterns

FishTalk uses consistent naming conventions that encode year-class (egg fertilization date):

| Pattern | Example | Interpretation |
|---------|---------|----------------|
| `(MONTH YY)` in parentheses | `01 S21/S04 SF/BF SEP 24 (MAI/JUN 23)` | Year-class: May/June 2023 |
| Month + Year | `Stofnfiskur S-21 feb24` | Year-class: February 2024 |
| Quarter notation | `24Q1 LHS` | Year-class: Q1 2024 |
| Year only | `NH 2023` | Year-class: 2023 |

**The parenthesized date `(MAI/JUN 23)` is the egg production date, while `SEP 24` indicates when fish went to sea.**

### Analysis of Project 1/24/58

Year-class extraction achieves **97% success rate** (35/36 populations). The project actually contains **5 different year-classes**:

| Year-Class | Quarter | Populations | Stage (current) | Notes |
|------------|---------|-------------|-----------------|-------|
| May/Jun 2023 | 2023-Q2 | 19 | Ongrowing (Adult) | Main cohort - correct progression |
| Jun 2023 | 2023-Q2 | 8 | Ongrowing (Adult) | Part of 2023-Q2 cohort |
| Jul 2023 | 2023-Q3 | 1 | Ongrowing (Adult) | Single population |
| Dec 2023 | 2023-Q4 | 1 | Ongrowing (Adult) | Single population |
| Feb/Mar 2024 | 2024-Q1 | 13 | Mixed (Alevin, Fry, Smolt, Eye-egg) | Later year-class |

**Root cause confirmed**: Project tuple 1/24/58 combines populations from **eggs fertilized across 5 different quarters** (May 2023 to March 2024).

### Why Time-Gap Splitting Alone Fails

Time-gap splitting produces 4 cohorts but one remains invalid because:
- Administrative grouping mixes fish at different lifecycle points
- An Oct 2023 "24Q1 LHS" Parr is grouped with Jun 2024 "NH FEB 24" Alevin
- These are different generations despite appearing in the same time window

### Validated Cohort Approach

Using year-class from names produces **5 of 6 valid cohorts**:

| Cohort | Populations | Time Span | Valid | Notes |
|--------|-------------|-----------|-------|-------|
| 2023-Q1 | 1 | 0 days | ✓ | NH 2023 |
| 2023-Q2 | 19 | 401 days | ✓ | Main cohort (May/Jun 23) |
| 2023-Q3 | 1 | 0 days | ✓ | Jul 23 |
| 2023-Q4 | 1 | 0 days | ✓ | Dec 23 |
| 2024-Q1 | 13 | 399 days | ✗ | Needs further splitting |
| Unknown | 1 | 0 days | ✓ | AX_NH 24 Q1 |

The 2024-Q1 cohort is invalid because it mixes:
- Administrative "24Q1" labels (Oct 2023 fish that are 24Q1 project assignments)
- Actual Feb/Mar 2024 eggs (Alevin/Eye-egg in late 2024)

### Recommended Implementation (Fallback)

**Fallback strategy: Year-class extraction from population names**

1. **Parse year-class from names** using these patterns (in priority order):
   - `\(([A-Za-z/]+)\s*(\d{2})\)` - Parenthesized month/year like `(MAI/JUN 23)`
   - `([a-zA-Z]{3,})\s*(\d{2,4})` - Month + year like `feb24`, `Mars 2024`
   - `(\d{2})Q([1-4])` - Quarter notation like `24Q1`
   - `\b(20\d{2})\b` - Year only like `2023`

2. **Group by year + quarter** to form initial cohorts

3. **Validate each cohort**:
   - Check for stage progression violations (earlier stages after later stages)
   - Check time span (<900 days typical lifecycle)

4. **Sub-split invalid cohorts** using time-gap approach (90-day threshold)

5. **Filter project tuples** by cohort count:
   - 1 cohort: Safe to migrate as-is
   - 2+ cohorts: Each cohort becomes a separate AquaMind batch

### Implementation Files

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/migration/analysis/analyze_batch_cohorts.py` | Analyze time-gap and stage-based splitting | Created |
| `scripts/migration/analysis/analyze_yearclass_from_names.py` | Extract year-class from population names | Created |
| `scripts/migration/legacy/tools/project_based_stitching_report.py` | Needs year-class cohort logic | To be updated |

### Month Name Mappings (Faroese/Danish/Norwegian/English)

```python
MONTH_MAP = {
    # English
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    # Scandinavian
    "mai": 5, "des": 12, "okt": 10, "mars": 3,
}
```

### Next Steps (Fallback)

1. **Modify `scripts/migration/legacy/tools/project_based_stitching_report.py`** to:
   - Add year-class extraction from PopulationName
   - Group populations by project tuple + year-class quarter
   - Generate separate batch candidates per cohort

2. **Update `scripts/migration/legacy/tools/pilot_migrate_project_batch.py`** to:
   - Accept cohort-qualified batch keys (e.g., `1/24/58:2023-Q2`)
   - Or auto-split multi-cohort project tuples

3. **Validate on sample batches** before full migration run

### Success Criteria for Correct Batch

| Criterion | Target | Why |
|-----------|--------|-----|
| Single year-class | ✓ | Fish from same egg fertilization quarter |
| Stage progression valid | ✓ | No Egg after Smolt, etc. |
| Time span | <900 days | ~2.5 years lifecycle max |
| Population count | 1-50 typical | Reasonable batch size |
| Fish count | 1-3M | Expected batch size |

### Year-Class Extraction Rate by InputYear

| InputYear | Populations | Extraction Rate | Primary Method |
|-----------|-------------|-----------------|----------------|
| 2024-2025 | 7,341 | 79-83% | Year-class extraction |
| 2022-2023 | 9,934 | 77-79% | Year-class extraction |
| 2020-2021 | 12,835 | 45% | Hybrid (year-class + time-gap) |
| 2018-2019 | 19,380 | 25-30% | Time-gap splitting |
| Pre-2018 | 18,894 | <25% | Time-gap splitting |

**Key finding:** FishTalk's naming convention with year-class indicators `(MONTH YY)` became standard around 2022. For recent data, year-class extraction is highly reliable.

### Recommended Hybrid Approach (Fallback)

```
For each project tuple:
1. Attempt year-class extraction from all population names
2. IF extraction_rate >= 70%:
     Group populations by extracted year-class quarter
     Validate each cohort for stage progression
     Split invalid cohorts by time-gap (90-day threshold)
3. ELSE:
     Use time-gap splitting (90-day threshold)
     Validate each cohort for stage progression
4. Each valid cohort = one AquaMind batch
```

### Analysis Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/migration/analysis/analyze_batch_cohorts.py` | Analyze time-gap and stage-based splitting for a project |
| `scripts/migration/analysis/analyze_yearclass_from_names.py` | Extract and validate year-class from population names |
| `scripts/migration/analysis/validate_yearclass_approach.py` | Validate approach across all project tuples |

### Status

**Validated fallback** - Year-class extraction is reliable for recent data (2022+). Use only when `Ext_Inputs_v2` is unavailable or for auxiliary FW→Sea linkage research.

---

## 📋 Implementation Checklist (2026-01-22, Fallback)

### Phase 1: Update Stitching Report (Fallback Priority)
- [ ] Modify `scripts/migration/legacy/tools/project_based_stitching_report.py`:
  - Add PopulationName extraction from FishTalk
  - Implement year-class parsing with month mappings
  - Generate cohort-qualified batch keys (e.g., `1/24/58:2023-Q2`)
  - Calculate extraction rate per project tuple
  - Flag multi-cohort projects in output

### Phase 2: Update Migration Script
- [ ] Modify `scripts/migration/legacy/tools/pilot_migrate_project_batch.py`:
  - Accept cohort suffix in project key
  - Auto-detect and report multi-cohort projects
  - Validate cohort stage progression before migration

### Phase 3: Validation
- [ ] Test on sample of problematic batches (1/24/58, etc.)
- [ ] Verify stage progression in migrated batches
- [ ] Check fish counts per cohort (should be 1-3M)

### Phase 4: Full Migration
- [ ] Run updated stitching report
- [ ] Migrate single-cohort projects first
- [ ] Handle multi-cohort projects with cohort suffixes
- [ ] Validate migrated data in preview stack

---

## 🚀 MAJOR DISCOVERY: Ext_Inputs_v2 Table (2026-01-22 Evening)

### The Breakthrough

**We found the true batch identifier in FishTalk!**

The `Ext_Inputs_v2` table tracks **egg inputs/deliveries** - the biological origin of batches. This is far superior to project tuples or population name parsing.

### Why Project Tuples Failed

Domain expert clarification:
- **Project tuple is a financial/administrative object**, not biological
- A batch stays in **ONE station → ONE area** (geography changes are impossible)
- The "Árgangur" (year-class) shown in FishTalk exports IS the batch identifier
- This comes from `Ext_Inputs_v2.InputName` + related fields

### Ext_Inputs_v2 Table Structure

```sql
SELECT PopulationID, InputName, InputNumber, YearClass, 
       Supplier, StartTime, InputCount, InputBiomass, Species
FROM dbo.Ext_Inputs_v2
```

| Column | Description |
|--------|-------------|
| PopulationID | **Direct link to Populations** |
| InputName | Batch name like "Stofnfiskur S21 okt 25", "BM Jun 24" |
| InputNumber | Numeric identifier |
| YearClass | Year class (2025, 2024, etc.) |
| Supplier | Egg supplier GUID |
| StartTime | When eggs arrived |
| InputCount | Number of eggs |

### Sample Data - Input-Based Batches

| InputName | InputNumber | YearClass | Pops | Span | Fish |
|-----------|-------------|-----------|------|------|------|
| 22S1 LHS | 2 | 2021 | 317 | 42 days | 6.9M |
| Heyst 2023 | 1 | 2023 | 108 | 275 days | 6.3M |
| Stofnfiskur Aug 22 | 3 | 2022 | 40 | 21 days | 5.1M |
| Rogn okt 2023 | 3 | 2023 | 567 | 19 days | 4.7M |

**These are biologically valid batches!** Time spans are reasonable, fish counts are correct (3-7M).

### Recommended New Approach

```
Batch Identification:
1. Primary: Ext_Inputs_v2 (InputName + InputNumber + YearClass)
2. Links via: PopulationID → Populations → all downstream data
3. Validation: Single geography, valid stage progression
```

### Why This Is Better

| Previous Approach | Problem | Ext_Inputs_v2 |
|-------------------|---------|---------------|
| Project tuple | Administrative, mixes year-classes | Tracks egg origin |
| PopulationName parsing | Only 43-83% extraction | Direct field |
| SubTransfers | Missing FW→Sea link | Not needed |

### Tables That Have YearClass

| Table | Has YearClass | Notes |
|-------|---------------|-------|
| **Ext_Inputs_v2** | ✓ | **PRIMARY SOURCE** |
| InputProjects | ✓ | Project-level |
| PlanPopulation | ✓ | Planning |
| PublicPlanPopulation | ✓ | Planning view |

### Implementation Priority

1. **Extract Ext_Inputs_v2 to CSV** (add to bulk_extract_fishtalk.py)
2. **Build Input-based stitching report** (new script)
3. **Validate geography constraint** (batch should stay in one geography)
4. **Update migration to use Input as batch key**

### Status

**CRITICAL FINDING** - Ext_Inputs_v2 provides the true biological batch identifier. This should replace project-tuple-based stitching for batch identification.
