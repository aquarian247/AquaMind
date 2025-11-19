# CRITICAL BUG: Premature Batch Completion

**Date:** November 19, 2025  
**Severity:** 🚨 **HIGH** - Data integrity issue  
**Status:** ⚠️ **IDENTIFIED** - Fix needed

---

## 🐛 The Bug

**Symptom:**
- 500 batches marked as `status='COMPLETED'`
- But stuck in **Smolt stage** (481) or **Fry stage** (19)
- **Zero harvest events** (no actual harvesting)
- All stopped at exactly **360 days** or **90 days**

**Impact:**
- UI shows batches as "completed" but they're not harvested
- Growth Analysis may be affected
- Harvest reports will be empty
- Data integrity compromised

---

## 🔍 Root Cause Analysis

### The Signal (apps/batch/signals.py:38-117)

```python
@receiver(post_save, sender=BatchContainerAssignment)
def check_batch_completion_on_assignment_change(sender, instance, **kwargs):
    """
    Automatically mark batch as COMPLETED when all assignments are inactive.
    """
    if not instance.is_active:
        batch = instance.batch
        
        # Check if ALL assignments are inactive
        active = batch.batch_assignments.filter(is_active=True).exists()
        
        if not active:
            # All assignments inactive → Mark batch COMPLETED
            batch.status = 'COMPLETED'
            batch.actual_end_date = latest_departure_date
            batch.save()
```

**This signal is CORRECT for production** (real harvests deactivate all assignments).

### The Test Data Problem

**Event Engine with Date-Bounding:**
```python
# generate_batch_schedule.py
duration = min(900, days_since_start)  # ← Date-bounded!

# Batch started 2019-05-05, today is 2025-11-19
# days_since_start = ~2,389 days
# But schedule set duration = 360 days (WHY?)
```

**What Happens:**
1. Batch runs for 360 days (reaches Smolt stage at day 270-360)
2. Event engine **stops** at day 360 (duration limit)
3. Last stage transition deactivated old assignments
4. Current assignments (Smolt) are still active
5. **BUT**: Something deactivates them (end of run?)
6. Signal fires → All assignments inactive → Mark COMPLETED ❌

---

## 🎯 The Real Issue: Schedule Duration Calculation

**In generate_batch_schedule.py line 108:**
```python
days_since_start = (today - batch_start).days
duration = min(total_lifecycle_days, days_since_start)  # ← BUG!
```

**This creates:**
- Batches from 2016-2017: duration = 900 (full lifecycle) ✅
- Batches from 2019-2024: duration = 360-800 (partial) ❌
- Batches from 2025: duration = 50-200 (very young) ✅

**Why this is wrong for test data:**
- **Real operations:** Batches are ongoing, date-bounding makes sense
- **Test data:** We want COMPLETED batches (harvested), not STOPPED batches

---

## 💡 The Solution

### Option 1: Always Run Full 900 Days (Recommended)
```python
# In generate_batch_schedule.py
# Remove date-bounding for test data generation
duration = 900  # Always full lifecycle

# Or: Only generate batches old enough to complete
min_start_date = today - timedelta(days=900 + 50)
if batch_start < min_start_date:
    duration = 900  # Full lifecycle
else:
    # Don't generate this batch (too young)
    continue
```

**Result:**
- All batches either ACTIVE (young) or COMPLETED (harvested)
- No batches stuck in middle stages
- Realistic test data

### Option 2: Fix Signal to Check Lifecycle Stage
```python
# In apps/batch/signals.py
if not active:
    # Only mark COMPLETED if batch reached Adult stage
    if batch.lifecycle_stage.name == 'Adult':
        batch.status = 'COMPLETED'
        batch.actual_end_date = latest_departure
    else:
        # Batch stopped mid-lifecycle, mark as TERMINATED
        batch.status = 'TERMINATED'
        batch.actual_end_date = latest_departure
    
    batch.save()
```

**Result:**
- Batches stopped mid-lifecycle marked as TERMINATED
- Only harvested batches marked as COMPLETED
- Preserves signal logic for production

### Option 3: Don't Deactivate Assignments for Stopped Batches
```python
# In event engine run() method
# At end of run, check if batch reached Adult
if self.batch.lifecycle_stage.name != 'Adult':
    # Batch stopped mid-lifecycle, leave assignments ACTIVE
    # Don't trigger completion signal
    pass
else:
    # Normal harvest flow
    self.harvest_batch()
```

**Result:**
- Stopped batches stay ACTIVE (correct status)
- Only harvested batches marked COMPLETED
- Minimal code changes

---

## 🚨 Current Data State

**What we have:**
- 550 batches total
- 500 marked "COMPLETED" (but not harvested) ❌
- 50 marked "ACTIVE" (correct) ✅
- 0 harvest events ❌
- All batches stuck in early stages

**What we need:**
- ~365 batches COMPLETED (actually harvested from Adult stage)
- ~185 batches ACTIVE (in progress)
- ~365 harvest events
- Realistic stage distribution

---

## 🔧 Recommended Fix

**Immediate:** Regenerate with corrected schedule

```bash
# 1. Fix generate_batch_schedule.py to only generate old batches
# Only include batches that started >900 days ago (can complete full lifecycle)

# 2. Wipe and regenerate
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 3. Generate corrected schedule
python scripts/data_generation/generate_batch_schedule.py \
  --batches 200 --stagger 7 --min-age 900 \
  --output config/batch_schedule_400_corrected.yaml

# 4. Execute
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_400_corrected.yaml --workers 14 --use-partitions
```

---

## 📝 Code Changes Needed

### 1. Add --min-age flag to schedule planner
```python
# generate_batch_schedule.py
parser.add_argument('--min-age', type=int, default=0,
                   help='Minimum batch age in days (skip batches younger than this)')

# In generate_schedule():
if days_since_start < args.min_age:
    continue  # Skip too-young batches
```

### 2. Always use full 900-day duration
```python
# In _plan_single_batch():
duration = 900  # Always full lifecycle for test data
```

### 3. Or: Fix the signal (production impact)
```python
# In apps/batch/signals.py check_batch_completion_on_assignment_change():
# Only mark COMPLETED if in Adult stage
if batch.lifecycle_stage.name == 'Adult':
    batch.status = 'COMPLETED'
else:
    batch.status = 'TERMINATED'  # Stopped mid-lifecycle
```

---

## 🎯 Next Steps

1. **Decide on fix approach** (Option 1 recommended)
2. **Implement fix** in schedule planner
3. **Wipe data** (current 550 batches are corrupted)
4. **Regenerate** with corrected logic
5. **Verify** harvest events exist

---

**This explains why the UI shows "Unknown Stage" and 0 population!**  
The batches are marked COMPLETED but never actually completed their lifecycle.

---

