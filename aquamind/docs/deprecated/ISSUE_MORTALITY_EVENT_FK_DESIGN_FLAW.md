# Issue: MortalityEvent FK to Batch (Should be Assignment) - Critical Data Model Flaw

**Priority:** CRITICAL  
**Type:** Data Model Design Flaw  
**Impact:** Analytics accuracy, audit trail precision, data integrity  
**Discovered:** 2025-11-18 during Growth Engine testing  
**Status:** ✅ **RESOLVED** 2025-11-18

---

## ✅ RESOLUTION SUMMARY (2025-11-18)

**Fixed Models:**
- ✅ `batch.MortalityEvent` - Added `assignment` FK (migration 0037)
- ✅ `health.LiceCount` - Added `assignment` FK (migration 0028)
- ✅ `health.MortalityRecord` - Added `assignment` FK (migration 0029)
- ✅ `environmental.EnvironmentalReading` - Event engine now populates `batch_container_assignment` FK

**Code Updates:**
- ✅ Growth Engine: Removed proration workaround (lines 787-803), confidence increased from 0.9 to 1.0
- ✅ Event Engine: Updated to populate `assignment` FK for mortality events (line 662)
- ✅ Event Engine: Updated to populate `batch_container_assignment` FK for environmental readings (line 557)
- ✅ Serializers: Added `assignment` field to MortalityEvent and LiceCount serializers
- ✅ Test Utils: Updated `create_test_mortality_event()` helper

**Verification:**
- ✅ All 1266 backend tests passing (Python)
- ✅ All 905 frontend tests passing (TypeScript/Vitest)
- ✅ TypeScript type checks: 0 errors
- ✅ OpenAPI schema regenerated: 0 errors, 19 warnings
- ✅ Migrations applied cleanly

**Pattern Applied:**
- Kept denormalized `batch` FK for query performance and aggregation endpoints
- Added `assignment` FK for precision and container-specific tracking
- Added model validation to ensure `assignment.batch == batch`
- Historical tables automatically updated by django-simple-history

**Performance Impact:**
- Growth Engine confidence scores increased from 0.9 → 1.0 for actual mortality
- Eliminated ~50 lines of complex proration logic
- Direct assignment queries instead of batch-wide aggregation + distribution

---

## 🚨 PROBLEM SUMMARY

`MortalityEvent` has FK to `Batch` (batch-wide), while `GrowthSample` correctly has FK to `Assignment` (container-specific). This inconsistency requires **proration workarounds** in Growth Engine and **loses critical location granularity**.

### The Inconsistency

| Model | Current FK | Should Be | Granularity |
|-------|------------|-----------|-------------|
| `GrowthSample` | `assignment` | ✅ CORRECT | Container-specific |
| `MortalityEvent` | `batch` | ❌ WRONG | Batch-wide (10+ containers) |

**Reality:** Mortality happens **in a specific container** (location, time, conditions), not batch-wide.

---

## 🔍 ROOT CAUSE EVIDENCE

### 1. Event Engine Creates Mortality Per-Assignment (But Stores to Batch!)

**File:** `scripts/data_generation/03_event_engine_core.py` (lines 561-584)

```python
def mortality_check(self):
    rates = {'Egg&Alevin': 0.0015, 'Fry': 0.0005, ...}
    
    for a in self.assignments:  # ← LOOPS PER ASSIGNMENT/CONTAINER
        rate = rates.get(a.lifecycle_stage.name, 0.0001)
        exp = a.population_count * rate
        act = np.random.poisson(exp)
        
        if act > 0:
            MortalityEvent.objects.create(
                batch=self.batch,  # ← STORES TO BATCH (LOSES CONTAINER INFO!) ❌
                event_date=self.current_date,
                count=act,
                ...
            )
            a.population_count -= act  # ← Updates assignment
            a.save()
```

**Problem:** Mortality is calculated **per-container** but stored **batch-wide**. Which container had the mortality? **LOST!**

### 2. Growth Engine ADMITS THE FLAW (Implements Proration Workaround)

**File:** `apps/batch/services/growth_assimilation.py` (lines 760-803)

```python
def _get_mortality(self, date: date, current_population: int, current_stage):
    """
    Note: MortalityEvent is tracked at batch level, not assignment level.
    For assignment-level calculations, we prorate batch mortality based on
    this assignment's share of batch population.  # ← WORKAROUND FOR FLAW!
    """
    # Get batch-level mortality
    actual_count = mortality_events.aggregate(Sum('count'))['count__sum']
    
    if actual_count:
        # PRORATION HACK - Assumes mortality distributed by population
        batch_population = self._get_batch_population(date)
        assignment_share = current_population / batch_population
        prorated_mortality = int(round(actual_count * assignment_share))
        return prorated_mortality, 'actual_prorated', 0.9  # ← Lower confidence!
```

**The Workaround:**
1. Get batch-total mortality (all containers combined)
2. Calculate this assignment's population share
3. Prorate mortality proportionally
4. **Confidence reduced to 0.9** (because it's guessing!)

**Why This Is Bad:**
- Assumes mortality is proportional to population (not always true!)
- Container with disease outbreak gets same rate as healthy containers
- Loss of precision in Growth Analysis calculations

### 3. GrowthSample Shows Correct Pattern

**File:** `apps/batch/models/growth.py` (line 22)

```python
class GrowthSample(models.Model):
    assignment = models.ForeignKey(
        BatchContainerAssignment,  # ← CORRECT: Container-specific
        on_delete=models.CASCADE,
        related_name='growth_samples'
    )
    sample_date = models.DateField()
    sample_size = models.PositiveIntegerField()
    avg_weight_g = models.DecimalField(...)
    # ... other fields
```

**Why This Is Correct:**
- Growth samples are taken from **specific container**
- Operator records: "Container C-05 on 2024-01-15: 50 fish, avg 25g"
- Precise location tracking
- No proration needed

---

## 💥 IMPACT ASSESSMENT

### Direct Impact

**1. Growth Engine Accuracy**
- Mortality must be **prorated** (estimated, not actual)
- Confidence score reduced (0.9 instead of 1.0)
- Daily state calculations less precise

**2. Analytics Precision**
- Can't analyze: "Which container had highest mortality?"
- Can't correlate: Mortality vs container conditions
- Can't identify: Problem containers vs healthy ones

**3. Audit Trail**
- Regulatory requirement: Track where mortality occurred
- Current model: "Batch XYZ lost 100 fish" (where? Unknown!)
- Should be: "Container C-05 lost 100 fish" (precise location)

**4. Operational Insights**
- Can't identify: Containers with recurring mortality
- Can't correlate: Mortality with environmental conditions per container
- Can't optimize: Container-specific interventions

### Cascading Issues

**Historical Records:**
- `batch_historicalmortalityevent` mirrors the flaw
- Historical audit trail also lacks container granularity

**Frontend/API:**
- Mortality reporting UI likely expects batch-level data
- API serializers assume batch FK
- Changes cascade through entire stack

**Tests:**
- ~16 test files create MortalityEvent with batch FK
- All need updating after migration

---

## 📋 WHAT NEEDS TO BE FIXED

### Critical (Must Fix):
1. **MortalityEvent** - Add `assignment` FK (currently missing)
2. **Event Engine line 573** - Populate assignment FK when creating mortality
3. **Growth Engine lines 787-803** - Remove proration workaround, query directly

### Important (Should Fix):
4. **EnvironmentalReading creation (line 469)** - Populate `batch_container_assignment=a` (1-line fix)
   - Note: Model is correct (denormalized for hypertable performance)
   - All 4 FKs (sensor, container, batch, assignment) are intentional
   - Only issue: Event engine doesn't populate assignment FK
5. **Update all 16+ test files** - Use assignment FK in mortality creates

### Investigation Required:
6. **Health models audit** - Check LiceCount, Treatment, SamplingEvent FK patterns
7. **Verify TransferAction** - Ensure source/dest assignment FKs are always populated

---

## 🔧 PROPOSED FIX

### Phase 1: Database Migration

**Change:**
```python
# OLD
class MortalityEvent(models.Model):
    batch = models.ForeignKey(Batch, ...)  # ❌

# NEW
class MortalityEvent(models.Model):
    assignment = models.ForeignKey(BatchContainerAssignment, ...)  # ✅
    # Keep batch as convenience (denormalized, for queries)
    batch = models.ForeignKey(Batch, ...)  # Optional: for backward compat
```

**Migration Strategy:**
```python
# migrations/XXXX_mortality_to_assignment.py

def forwards(apps, schema_editor):
    MortalityEvent = apps.get_model('batch', 'MortalityEvent')
    
    for event in MortalityEvent.objects.all():
        # Find active assignment at event date
        assignment = BatchContainerAssignment.objects.filter(
            batch=event.batch,
            assignment_date__lte=event.event_date,
            departure_date__gte=event.event_date  # or is NULL
        ).first()
        
        if assignment:
            event.assignment = assignment
            event.save()
        else:
            # Orphaned event - delete or log
            pass
```

### Phase 2: Code Updates

**Files to Update:**
1. `apps/batch/models/mortality.py` (model change)
2. `scripts/data_generation/03_event_engine_core.py` (line 573)
3. `apps/batch/services/growth_assimilation.py` (line 787-803, remove proration)
4. `apps/batch/api/serializers/*.py` (mortality serializers)
5. Frontend: `MortalityEventForm.tsx`, `BatchHealthView.tsx`
6. ~16 test files

**Event Engine Fix:**
```python
# OLD (line 573)
MortalityEvent.objects.create(
    batch=self.batch,
    ...
)

# NEW
MortalityEvent.objects.create(
    assignment=a,  # ← Container-specific!
    batch=self.batch,  # Optional: keep for convenience
    ...
)
```

**Growth Engine Simplification:**
```python
# OLD (lines 787-803) - Complex proration
actual_count = mortality_events.aggregate(Sum('count'))['count__sum']
batch_population = self._get_batch_population(date)
assignment_share = current_population / batch_population
prorated_mortality = int(round(actual_count * assignment_share))

# NEW - Direct query
mortality_events = MortalityEvent.objects.filter(
    assignment=self.assignment,  # ← Direct! No proration!
    event_date=date
)
actual_count = mortality_events.aggregate(Sum('count'))['count__sum'] or 0
return actual_count, 'actual', 1.0  # Full confidence!
```

---

## 🔍 COMPREHENSIVE DATA MODEL AUDIT

**Requirement:** Check ALL batch-related events for similar FK inconsistencies.

### Models to Audit - VERIFIED RESULTS

#### ✅ CORRECT (Has assignment FK and uses it)
- ✅ `GrowthSample` → `assignment` FK (CORRECT MODEL)
- ✅ `FeedingEvent` → Has BOTH `batch` + `batch_assignment` FKs, **BOTH populated** ✅
- ✅ `TransferAction` → `source_assignment` + `dest_assignment` FKs

#### ✅ CORRECT BUT INCOMPLETE
- ⚠️ `EnvironmentalReading` → **Intentionally denormalized** (sensor + container + batch + assignment FKs)
  - **Reason:** Hypertable performance (40M+ rows, joins are expensive)
  - Has all needed FKs including `batch_container_assignment` ✅
  - **Issue:** Event engine doesn't populate `batch_container_assignment` FK
  - Line 469: `EnvironmentalReading(..., container=a.container, batch=self.batch)` 
  - **Fix:** Add `batch_container_assignment=a` (1-line change)

#### ❌ MISSING ASSIGNMENT FK ENTIRELY
- ❌ `MortalityEvent` → Only `batch` FK, **NO assignment FK** (CRITICAL FLAW)

#### ⚠️ NOT YET AUDITED
- ⚠️ Health events (treatments, lice counts) → Check granularity

#### 🔍 Audit Checklist

**For EACH event model, verify:**

1. **Where does event occur?**
   - Container-specific? → Should FK to `assignment`
   - Batch-wide? → OK to FK to `batch`

2. **How is it recorded in real operations?**
   - Operator at container records event? → `assignment` FK
   - Batch-level aggregate? → `batch` FK

3. **How is it used in calculations?**
   - Per-container calculations? → Needs `assignment` FK
   - Batch totals only? → `batch` FK acceptable

### Specific Models to Check

```python
# Priority 1: Event models
apps/batch/models/mortality.py          # MortalityEvent ← KNOWN ISSUE
apps/inventory/models/feeding.py        # FeedingEvent ← CHECK!
apps/environmental/models/reading.py    # EnvironmentalReading ← VERIFY
apps/batch/models/transfer.py          # TransferAction ← Probably correct
apps/batch/models/growth.py            # GrowthSample ← CORRECT (reference)

# Priority 2: Health models
apps/health/models/lice.py             # LiceCount ← CHECK!
apps/health/models/treatment.py        # Treatment ← CHECK!
apps/health/models/journal.py          # HealthJournalEntry ← CHECK!
apps/health/models/sampling.py         # SamplingEvent ← CHECK!

# Priority 3: Finance models
apps/finance/models/facts.py           # HarvestFact ← Probably batch OK
```

### Audit Query Template

For each model, run:
```python
# Check if event loops per-assignment but stores to batch
grep -A 10 "for.*assignment" scripts/data_generation/03_event_engine_core.py | grep "\.objects\.create"

# Check if calculations prorate from batch to assignment
grep -B 5 -A 10 "prorate\|assignment_share\|batch.*population" apps/*/services/*.py
```

---

## 🎯 RECOMMENDED ACTION PLAN

### Immediate (Before Continuing Test Data)

**1. Audit ALL Event Models (30 minutes)**
```bash
# Run comprehensive grep for FK patterns
grep -r "batch = models.ForeignKey" apps/*/models/*.py
grep -r "assignment = models.ForeignKey" apps/*/models/*.py

# Check for proration workarounds (indicates FK mismatch)
grep -r "prorate\|assignment_share\|population_share" apps/*/services/*.py
```

**2. Create Issues for Each Flaw Found**
- MortalityEvent (confirmed)
- FeedingEvent (likely)
- Others (TBD after audit)

**3. Assess Migration Complexity**
- How many events in production?
- Can we migrate existing data?
- What breaks during migration?

### Next Session (Fix Before Test Data)

**Priority Order:**
1. **Data Model Audit** (identify all flaws)
2. **Create Migrations** (fix FKs)
3. **Update Event Engine** (use assignment FK)
4. **Update Growth Engine** (remove proration hacks)
5. **Update Tests** (16+ files)
6. **Update Frontend/API** (if needed)
7. **THEN generate test data** (with correct model)

---

## 🔬 TECHNICAL DEEP DIVE

### Why Has Anything Worked At All?

**The Proration Workaround Masks The Issue:**

```python
# Growth Engine (line 794-800)
batch_population = self._get_batch_population(date)  # Sum all assignments
assignment_share = current_population / batch_population  # e.g., 0.1 (10%)
prorated_mortality = int(round(actual_count * assignment_share))  # Distribute
```

**Example:**
- Batch has 3M fish across 10 containers (300K each)
- Container-05 records: 50 fish mortality
- Event stores: `batch=XYZ, count=50` (loses container info)
- Growth Engine retrieves: "Batch XYZ lost 50 fish today"
- Prorates to Container-05: 50 × (300K/3M) = 5 fish
- **BUT ORIGINAL WAS 50 FISH IN THAT CONTAINER!**

**The Data Loss:**
```
ACTUAL: Container-05 lost 50 fish
STORED: Batch XYZ lost 50 fish (which container? Unknown!)
RETRIEVED: All containers share 50 fish → 5 fish each (WRONG!)
```

**Why Calculations Are Still "Close Enough":**
- With random mortality distribution, proration **averages out**
- Errors cancel over time (overestimate some days, underestimate others)
- But individual daily calculations are **imprecise**

### The Comment That Gave It Away

```python
# Line 769-772
"""
Note: MortalityEvent is tracked at batch level, not assignment level.
For assignment-level calculations, we prorate batch mortality based on
this assignment's share of batch population.
"""
```

**Translation:** "We know this is wrong, here's the workaround."

---

## 📊 COMPREHENSIVE DATA MODEL AUDIT REQUIRED

### Audit Criteria

For EVERY event model, verify:

**1. Spatial Granularity**
- ✅ Container-specific events → `assignment` FK
- ✅ Batch-wide aggregates → `batch` FK
- ❌ Mismatch → DATA FLAW

**2. Operational Reality**
- How do operators record this event?
- Do they specify container? → Needs `assignment` FK
- Batch-level only? → `batch` FK acceptable

**3. Calculation Requirements**
- Are per-container calculations needed?
- Does Growth Engine need to prorate? → FK MISMATCH
- Direct query possible? → FK CORRECT

### Models Requiring Audit

#### Batch App
```python
✅ GrowthSample → assignment FK (CORRECT, reference standard)
❌ MortalityEvent → batch FK (CONFIRMED FLAW)
⚠️  TransferAction → source_assignment + dest_assignment FKs (VERIFY correct)
⚠️  CreationAction → assignment FK? (CHECK)
```

#### Inventory App
```python
✅ FeedingEvent → Has BOTH batch + batch_assignment FKs (CORRECT, denormalized)
   # Event engine populates both (line 501)
   # batch FK for convenience queries
   # batch_assignment FK for precision
   
⚠️  FeedPurchase → ??? (CHECK - likely batch-level OK)
⚠️  FeedContainerStock → ??? (CHECK - feed container inventory)
```

#### Environmental App
```python
✅ EnvironmentalReading → INTENTIONALLY DENORMALIZED (ALL FKs CORRECT)
   # Has: sensor + container + batch + batch_container_assignment FKs
   # Reason: Hypertable performance (40M+ rows, joins expensive)
   # Indexes on (container, param, time) and (batch, param, time)
   # Trade storage for query speed (correct for time-series)
   # ONLY ISSUE: batch_container_assignment not populated by event engine!
   # Fix: Add `batch_container_assignment=a` at line 469 (1-line change)
```

#### Health App
```python
⚠️  LiceCount → batch FK or assignment FK? (CHECK)
   # Lice sampling is container-specific
   # Should probably be assignment FK
   
⚠️  Treatment → batch FK or assignment FK? (CHECK)
   # Treatments applied to specific containers
   # Should probably be assignment FK
   
⚠️  SamplingEvent → ??? (CHECK)
⚠️  HealthJournalEntry → batch FK (PROBABLY OK, it's narrative)
```

#### Finance App
```python
✅ HarvestFact → batch FK (CORRECT, harvest is batch-wide)
✅ IntercompanyTransaction → batch FK (PROBABLY CORRECT)
```

### Audit SQL Query

```sql
-- Find all FK relationships to batch_batch
SELECT 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'batch_batch'
ORDER BY tc.table_name;

-- Expected results to review:
-- batch_mortalityevent.batch_id → batch_batch.id (WRONG!)
-- inventory_feedingevent.batch_id → batch_batch.id (LIKELY WRONG!)
-- environmental_reading.batch_id → batch_batch.id (VERIFY!)
```

---

## 🎯 EXPECTED FINDINGS

### High Confidence Flaws (Likely Wrong):

**1. FeedingEvent → batch FK**
```python
# Event engine likely does:
for assignment in self.assignments:
    FeedingEvent.objects.create(
        batch=self.batch,  # ← WRONG! Should be assignment
        ...
    )
```

**Evidence needed:**
- Check event engine (line ~650-700 range)
- Check if Growth Engine prorates feed too
- Operators feed **specific tanks**, not batches

**2. EnvironmentalReading → batch FK (if exists)**
```python
# Sensors are container-specific
# Readings MUST be container-specific
# If FK is to batch → MAJOR FLAW
```

**3. LiceCount → batch FK (if exists)**
```python
# Lice sampling is container-specific
# Must track which container
# If FK is to batch → FLAW
```

### Lower Risk (Probably OK):

**1. HealthJournalEntry → batch FK**
- Narrative entries, batch-level acceptable

**2. HarvestFact → batch FK**
- Harvest is batch-wide operation

**3. IntercompanyTransaction → batch FK**
- Financial transactions are batch-level

---

## 📋 MIGRATION STRATEGY

### Step 1: Audit & Document (2 hours)
1. Run SQL FK audit query
2. Check each model's operational reality
3. Check event engine for loop patterns
4. Check services for proration workarounds
5. Document findings in table

### Step 2: Prioritize Fixes (30 minutes)
**Critical (Fix immediately):**
- MortalityEvent (confirmed)
- FeedingEvent (if wrong)
- EnvironmentalReading (if wrong)

**Important (Fix soon):**
- Health models (if wrong)

**Low priority:**
- Models where batch FK is actually correct

### Step 3: Create Migrations (1 hour per model)
```python
# For each model:
1. Add assignment FK (nullable initially)
2. Backfill: Find assignment at event_date
3. Make assignment FK non-nullable
4. Optionally: Keep batch FK (denormalized for queries)
```

### Step 4: Update Code (2-4 hours)
1. Event engine: Use assignment FK in creates
2. Growth Engine: Remove proration workarounds
3. API serializers: Update to handle assignment
4. Tests: Update ~16+ test files

### Step 5: Frontend Updates (if needed)
1. Check if frontend displays container info
2. Update forms to show assignment context
3. Update queries to join through assignment

---

## ⚠️ BLOCKING ISSUES

**DO NOT PROCEED WITH TEST DATA GENERATION until this is fixed!**

**Why:**
- Current test data will have **wrong FK structure**
- Would need to regenerate after fix (another 5-6 hours)
- Better to fix model FIRST, then generate correct data

**Timeline:**
1. **Model audit:** 2 hours
2. **Migrations:** 3-4 hours (if 3-4 models wrong)
3. **Code updates:** 4-6 hours
4. **Testing:** 2 hours
5. **THEN test data generation:** 5-6 hours

**Total:** ~20 hours of work before clean test data

---

## 🎓 LESSONS LEARNED

### 1. Consistency Matters
- GrowthSample got it right (assignment FK)
- MortalityEvent got it wrong (batch FK)
- **Always use same pattern for same granularity**

### 2. Comments Reveal Design Flaws
- "Note: We prorate because..." = **RED FLAG**
- Proration = Workaround for incorrect FK

### 3. Test Data Generation Exposes Issues
- Growth Engine testing revealed the proration hack
- Might have gone unnoticed in production (errors hidden by averaging)

### 4. Audit Early and Often
- Review data model before generating millions of records
- Fix structure first, data second
- **Prevention < Correction**

---

## 📞 DISCUSSION POINTS

### Question 1: Keep Batch FK (Denormalized)?

**Option A:** Remove batch FK entirely
```python
assignment = models.ForeignKey(Assignment, ...)
# batch accessible via: assignment.batch
```

**Option B:** Keep both FKs (denormalized)
```python
assignment = models.ForeignKey(Assignment, ...)
batch = models.ForeignKey(Batch, ...)  # For convenience queries
```

**Recommendation:** Option B (denormalized) for query performance.

### Question 2: What About Historical Data?

**If production has mortality events:**
- Can we backfill assignment FK?
- Or mark as "legacy" with NULL assignment?
- Or delete and regenerate?

### Question 3: Priority Order?

**Most critical to fix first:**
1. MortalityEvent (confirmed wrong)
2. FeedingEvent (likely wrong, check first)
3. EnvironmentalReading (critical if wrong)
4. Health models (moderate impact)

---

## 🚀 ACCEPTANCE CRITERIA

**For This Issue to be CLOSED:**

✅ All event models audited (FK documented)  
✅ MortalityEvent migrated to assignment FK  
✅ Event engine updated (create with assignment)  
✅ Growth Engine simplified (proration removed)  
✅ All tests passing  
✅ Migration tested on real data (if exists)  
✅ Frontend/API updated (if needed)  
✅ Similar flaws fixed (FeedingEvent, etc.)  
✅ Documentation updated (ERD, API docs)

---

## 🏁 BOTTOM LINE

**This is NOT a minor issue. It's a fundamental data model flaw that:**
- Loses operational granularity (which container?)
- Requires workaround hacks (proration)
- Reduces analytics precision (confidence scores)
- Violates design consistency (GrowthSample vs MortalityEvent)

**DO NOT generate 170-batch test data until this is fixed!**

**Estimated fix time:** 1-2 days (audit + migrate + test)  
**Estimated test data regen:** 5-6 hours (after fix)  
**Total:** ~2 days to clean, correct data

---

**This is embarrassing, yes. But finding it NOW (before production scale) is actually EXCELLENT timing. Much better than discovering after 100GB of wrong data!**

---

## 📎 References

- Growth Engine: `apps/batch/services/growth_assimilation.py` (lines 760-803)
- Event Engine: `scripts/data_generation/03_event_engine_core.py` (lines 561-584)
- MortalityEvent Model: `apps/batch/models/mortality.py` (line 26)
- GrowthSample Model: `apps/batch/models/growth.py` (line 22, correct pattern)

---

**Assignee:** TBD  
**Labels:** `critical`, `data-model`, `migration`, `technical-debt`  
**Milestone:** Before UAT  
**Estimated:** 16-20 hours

---

