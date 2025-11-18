# ⛔ STOP - Data Model Audit Required Before Test Data Generation

**Date:** November 18, 2025  
**Severity:** CRITICAL  
**Status:** ⚠️ **BLOCKING TEST DATA GENERATION**

---

## 🚨 CRITICAL ISSUE DISCOVERED

**MortalityEvent has FK to Batch (should be Assignment)**

This is a fundamental data model flaw that:
- Loses container-specific mortality location
- Requires proration workarounds in Growth Engine
- Reduces analytics precision
- Violates design consistency

**See:** `ISSUE_MORTALITY_EVENT_FK_DESIGN_FLAW.md` for complete analysis

---

## ⛔ DO NOT PROCEED WITH TEST DATA GENERATION

**Why:** 
- Generating 170 batches with **wrong FK structure** = wasted 5-6 hours
- Would need to regenerate after fix (another 5-6 hours)
- **Fix model FIRST**, then generate clean data

---

## ✅ WHAT WAS COMPLETED THIS SESSION

1. **Growth Engine Fix (Issue #112)** - DONE ✅
   - No more population doubling
   - Tested and verified
   - Ready to commit

2. **Test Data Guide v3** - DONE ✅
   - Infrastructure saturation documented
   - Single source of truth

3. **Data Model Flaw Discovered** - EXCELLENT TIMING 🎯
   - Found BEFORE generating 170 batches
   - Found BEFORE UAT
   - Saves massive rework

---

## 🎯 REQUIRED ACTIONS (Next Session)

### 1. Complete Data Model Audit (2 hours)

**Run these checks:**
```bash
cd /Users/aquarian247/Projects/AquaMind

# Find all FK relationships to batch_batch
echo "
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'batch_batch'
ORDER BY tc.table_name;
" | psql aquamind_db

# Check for proration hacks (indicates FK problems)
grep -r "prorate\|assignment_share\|population_share" apps/*/services/*.py
```

**Audit each model:**
- Does event happen per-container or batch-wide?
- Does code loop per-assignment but store to batch?
- Does service prorate from batch to assignment?

### 2. Fix MortalityEvent (3-4 hours)

**Files to modify:**
- `apps/batch/models/mortality.py` (add assignment FK)
- Create migration (add field, backfill, make non-null)
- `scripts/data_generation/03_event_engine_core.py` (line 573)
- `apps/batch/services/growth_assimilation.py` (lines 787-803)
- ~16 test files
- API serializers (if needed)
- Frontend forms (if needed)

### 3. Fix EnvironmentalReading Population (5 minutes)

**Note:** Model is correct (intentionally denormalized for hypertable performance).

**Simple fix:**
```python
# Line 469 in event engine
EnvironmentalReading(
    ...
    container=a.container,
    batch=self.batch,
    batch_container_assignment=a,  # ← ADD THIS (1-line change)
    ...
)
```

**Why multiple FKs are correct:**
- Hypertable with 40M+ rows (joins are expensive)
- Direct FKs enable indexed queries (batch, container, assignment)
- Denormalization is correct pattern for time-series data

### 4. Fix Any Other Flaws Found (TBD)

Depends on audit results.

### 5. THEN Generate Test Data (5-6 hours)

**Only after all FK flaws fixed:**
```bash
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 6  # Note: 6 workers, not 14 (race condition issue)
```

---

## 💡 WHY THIS IS ACTUALLY GOOD NEWS

**Discovery timing is PERFECT:**
- Found during testing (not production)
- Found before generating 100GB of wrong data
- Found before UAT handoff
- Fix is straightforward (add FK + update code)

**What could have gone wrong:**
- Generate 170 batches with wrong FK (5-6 hours wasted)
- Discover in UAT: "Why can't we see which container had mortality?"
- Realize entire dataset is wrong
- Regenerate everything (another 5-6 hours)
- **Total waste: 10-12 hours + embarrassment**

**By catching it now:**
- Fix model first (3-4 hours)
- Generate correct data once (5-6 hours)
- **Total: 8-10 hours, done right**

---

## 📱 For Next Agent/Session

1. Read `ISSUE_MORTALITY_EVENT_FK_DESIGN_FLAW.md` completely
2. Run data model audit (SQL + grep commands above)
3. Create GitHub issue with findings
4. Fix MortalityEvent FK (migration + code)
5. Fix EnvironmentalReading population (1-line change)
6. Test with single batch
7. THEN proceed with full test data generation

---

**Status: Growth Engine fix is solid. Data model needs fixing before scaling up.**

---
