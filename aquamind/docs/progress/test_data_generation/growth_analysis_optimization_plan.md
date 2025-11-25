# Growth Analysis Performance Optimization Plan

**Date:** 2025-11-21  
**Status:** Planning Phase  
**Context:** Post v6.1 test data generation success (144/144 batches generated)

---

## 🎯 Problem Statement

**Growth analysis recomputation times out after 300 seconds per batch** (expected: 30-60 seconds).

**Impact:**
- Batch generation: ✅ No impact (100% stable, 144/144 success)
- Operational data: ✅ Complete and usable (18.6M events)
- Growth Analysis UI: ❌ Orange "Actual Daily State" line empty

**Symptoms:**
- Subprocess workers timeout during `recompute_batch_assignments()` call
- All 144 batches timeout (not a data-specific issue)
- CPU load shows tight loops (14 workers pegged at 100%)
- Suggests query inefficiency or N+1 problem

---

## ✅ What's Working (DO NOT TOUCH)

### Batch Generation Pipeline
- ✅ `generate_batch_schedule.py` - 100% stable
- ✅ `execute_batch_schedule.py` - 100% stable  
- ✅ `03_event_engine_core.py` - 100% stable
- ✅ All race conditions eliminated
- ✅ Order-based stage lookups implemented
- ✅ Infrastructure-aware scheduling

### Subprocess-Based Parallelization Framework
- ✅ `growth_analysis_worker_subprocess()` in `04_batch_orchestrator_parallel.py`
- ✅ ProcessPoolExecutor implementation
- ✅ JSON serialization/deserialization
- ✅ Timeout handling (300s)
- ✅ Error reporting

**The parallelization framework is correct** - the issue is in the `recompute_batch_assignments()` function itself.

---

## 🔍 Root Cause Analysis

**Likely Issues (Priority Order):**

### 1. N+1 Query Problem in Daily State Calculation

**Location:** `apps/batch/services/growth_assimilation.py`

**Hypothesis:** For each batch with 800+ days of history:
- Queries assignment events for EACH day individually
- Each day queries: feeding, mortality, transfers, growth samples
- Result: 800 days × 10 containers × 5 event types = **40,000+ database queries per batch**

**Evidence:**
- 800-day batch × 40k queries @ 0.01s each = 400+ seconds (matches timeout!)
- CPU pegged (tight query loop)
- Works on small test batches but not production data

### 2. Missing Database Indexes

**Likely Missing Indexes:**
- `batch_batchcontainerassignment (batch_id, assignment_date, is_active)`
- `environmental_environmentalreading (batch_id, reading_time)`
- `inventory_feedingevent (batch_id, feeding_date)`
- `batch_mortalityevent (batch_id, event_date)`

**Impact:** Sequential scans on large tables (18.6M environmental rows)

### 3. Inefficient Date Range Queries

**Pattern:**
```python
# Slow: Individual day queries
for day in range(800):
    events = Event.objects.filter(batch=batch, date=day)
```

**Should be:**
```python
# Fast: Single bulk query
events = Event.objects.filter(batch=batch).order_by('date')
# Process in memory
```

---

## 💡 Proposed Solutions (Choose One or Combine)

### Solution 1: Bulk Query with In-Memory Processing (Recommended)

**Approach:** Fetch all events for a batch once, process in memory.

**Changes Needed:**
1. Query all feeding events for batch: `FeedingEvent.objects.filter(batch=batch).order_by('feeding_date')`
2. Query all mortality events: `MortalityEvent.objects.filter(batch=batch).order_by('event_date')`
3. Query all transfers: `TransferAction.objects.filter(workflow__batch=batch).order_by('actual_execution_date')`
4. Build daily states in memory from event arrays
5. Bulk create `ActualDailyAssignmentState` records

**Pros:**
- Eliminates N+1 queries
- Minimal code changes
- No database schema changes

**Cons:**
- Requires rewriting day-by-day loop logic
- Memory overhead for large batches (manageable)

**Estimated Speedup:** 100x (400s → 4s per batch)

---

### Solution 2: Add Database Indexes

**Approach:** Add composite indexes for common query patterns.

**Migration Needed:**
```python
# New migration in apps/batch/migrations/
class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='batchcontainerassignment',
            index=models.Index(
                fields=['batch', 'assignment_date', 'is_active'],
                name='bca_batch_date_active_idx'
            )
        ),
        migrations.AddIndex(
            model_name='feedingevent',
            index=models.Index(
                fields=['batch', 'feeding_date'],
                name='feeding_batch_date_idx'
            )
        ),
        # ... similar for mortality, environmental
    ]
```

**Pros:**
- Improves ALL batch queries (not just growth analysis)
- No algorithm changes needed
- Works with existing code

**Cons:**
- Requires migration
- Index maintenance overhead
- May not fully solve if N+1 pattern remains

**Estimated Speedup:** 10-20x (400s → 20-40s per batch)

---

### Solution 3: Cached/Incremental Growth Analysis

**Approach:** Only recompute NEW days, not entire history.

**Logic:**
1. Check last computed day: `ActualDailyAssignmentState.objects.filter(batch=batch).aggregate(Max('day_number'))`
2. Only process days since last computation
3. Append new states to existing

**Pros:**
- Massive speedup for active batches (only compute new days)
- Efficient for ongoing operations
- Good for production use

**Cons:**
- More complex logic (state management)
- Requires handling of assignment changes (what if data corrected?)
- May not help for initial full recompute

**Estimated Speedup:** 50-100x for incremental, minimal for initial

---

### Solution 4: Simplified Daily State Algorithm

**Approach:** Question if we need EVERY detail for EVERY day.

**Considerations:**
- Do we need exact daily population/biomass?
- Or can we sample (e.g., every 7 days)?
- Or calculate from stage averages?

**Trade-off:**
- Faster computation
- Less granular data
- May impact UI chart quality

**Not Recommended** unless business accepts reduced granularity.

---

## 🎯 Recommended Approach

**Phase 1: Profile & Diagnose (30 minutes)**
1. Add timing logs to `recompute_batch_assignments()` to identify bottleneck
2. Log query counts with Django Debug Toolbar or connection.queries
3. Confirm N+1 hypothesis vs other issues

**Phase 2: Quick Win - Add Indexes (1 hour)**
1. Create migration with composite indexes
2. Run on dev database
3. Test growth analysis on 1-2 batches
4. If 10x speedup achieved, good enough for now

**Phase 3: If Still Slow - Refactor to Bulk Queries (2-3 hours)**
1. Rewrite growth_assimilation.py to use bulk queries
2. Process events in memory instead of per-day queries
3. Bulk create daily states
4. Target: <5s per batch

---

## 📋 Success Criteria

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Time per batch | 300s+ (timeout) | <60s | ❌ |
| Query count | ~40,000+ | <1,000 | ❌ |
| CPU pattern | Tight loop | Bursty I/O | ❌ |
| Success rate | 0% (all timeout) | 100% | ❌ |

**Target:** 144 batches × 60s = 2.4 hours for full recompute (vs current: infinite/timeout)

---

## 🚫 Out of Scope

- Batch generation scripts (already stable)
- Schedule generation logic (already optimal)
- Event engine (already correct)
- Subprocess parallelization framework (already working)

**Focus:** Only the `apps/batch/services/growth_assimilation.py` module and related database indexes.

---

## 📁 Files to Investigate

**Primary:**
- `apps/batch/services/growth_assimilation.py` - Core recompute logic

**Secondary:**
- `apps/batch/models/daily_state.py` - ActualDailyAssignmentState model
- Check for missing indexes in migration files

**Testing:**
- Run single-batch recompute with query logging
- Profile with Django Debug Toolbar
- Compare against batches with <100 days (should be fast)

---

## 🎯 Next Agent Instructions

1. **Read** `test_data_generation_guide_v6.md` for context
2. **Profile** `recompute_batch_assignments()` with timing logs
3. **Implement** Solution 2 (indexes) as quick win
4. **If still slow** → Implement Solution 1 (bulk queries)
5. **Test** on generated 144-batch dataset (no need to regenerate)
6. **Validate** can complete all 144 batches in <2 hours

**The test data is already generated and correct - only optimization needed!**

