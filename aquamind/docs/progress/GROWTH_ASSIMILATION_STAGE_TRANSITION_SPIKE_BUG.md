# Growth Assimilation Stage Transition Spike Bug

**Date:** November 19, 2025  
**Discovered During:** TGC formula fix validation  
**Severity:** 🟡 **MEDIUM** - Visual anomaly in Growth Analysis chart  
**Status:** 📋 **DOCUMENTED** (Not blocking TGC fix)

---

## Problem Description

The Growth Analysis chart shows vertical spikes in the orange line (Actual Daily State) at stage transition points. These spikes occur when the Event Engine creates new BatchContainerAssignments during lifecycle stage transitions.

**Observable Symptom:**
- Orange line shows sharp vertical spikes (+5-30g) followed by immediate drops
- Spikes occur precisely at stage transition days (91, 181, 271, 361, 451)
- Green line (Projected) is smooth - no spikes ✅
- Blue dots (Growth Samples) are smooth - no spikes ✅

---

## Example: Batch FI-2025-002 (ID: 1127)

### Day 90-92 Spike:
```
Day 90: Egg&Alevin in Hall A
  - 10 containers
  - Weight: 0.10g ✅
  - Anchor: None
  - Source: tgc_computed

Day 91: NEW Parr assignments in Hall B (STAGE TRANSITION)
  - 10 NEW containers
  - Weight: 6.02g ❌ (SPIKE! Should be ~0.10g)
  - Anchor: None
  - Source: tgc_computed
  - Population: ~297k (transferred from Hall A)

Day 92: Same Parr assignments
  - Same 10 containers
  - Weight: 0.14g ✅ (Corrected by growth_sample anchor)
  - Anchor: growth_sample (measured)
  - Source: measured
```

### Day 180-182 Spike:
```
Day 180: Parr at 6.05g ✅
Day 181: NEW Smolt assignments at 36.07g ❌ (SPIKE! +30g)
Day 182: Same containers at 36.13g ✅ (normal growth)
```

---

## Root Cause Analysis

### Stage Transition Flow (Event Engine):

1. **Day 90**: Fish in Hall A (Egg&Alevin), weight = 0.10g
2. **Day 91**: `check_stage_transition()` detects duration reached
   - Creates transfer workflow
   - Closes old assignments (Hall A)
   - Creates NEW assignments (Hall B, Parr stage)
   - **Problem:** New assignment initial weight = 6.02g (wrong!)
3. **Day 92**: Growth sample recorded
   - Anchor resets weight to actual measured (0.14g)
   - Spike disappears

### Suspected Code Location

**File:** `apps/batch/services/growth_assimilation.py`

**Lines 455-464** - Initial weight fallback logic:
```python
# Last resort: use lifecycle stage's min weight if available
if hasattr(self.assignment.lifecycle_stage, 'expected_weight_min_g'):
    if self.assignment.lifecycle_stage.expected_weight_min_g:
        initial_weight = float(self.assignment.lifecycle_stage.expected_weight_min_g)
```

**Problem:** When computing daily states for new assignments created during stage transitions, the engine falls back to `expected_weight_min_g` of the NEW stage (Parr min = 6.0g) instead of inheriting the actual weight from the previous assignment.

---

## Impact

### User Experience:
- ⚠️ Growth Analysis chart shows confusing spikes
- ⚠️ Makes it look like weight jumped dramatically during transfers
- ⚠️ Reduces trust in the visualization

### Data Integrity:
- ✅ Actual data is correct (growth samples, assignments)
- ✅ Spike is only in ActualDailyAssignmentState (derived/computed table)
- ✅ Day after spike is corrected by real measurements

### Severity:
- **Medium** - Visual issue, doesn't affect actual data
- **Non-blocking** - Core operations unaffected
- **Self-correcting** - Next growth sample fixes the spike

---

## Workaround (Current)

Growth samples recorded on day 92 (day after transition) provide anchor points that correct the computed values. The spikes only last for one day.

---

## Recommended Fix (Future)

### Option A: Inherit Previous Assignment Weight
When creating daily states for new assignments during stage transitions:

```python
# In _get_initial_state() around line 455-464
if not initial_weight:
    # Check if this assignment is part of a stage transition
    # Look for previous assignment in different container from same batch
    prev_assignment = BatchContainerAssignment.objects.filter(
        batch=self.batch,
        departure_date=self.assignment.assignment_date,  # Transferred on same day
        is_active=False
    ).first()
    
    if prev_assignment:
        # Get the last daily state from previous assignment
        prev_state = ActualDailyAssignmentState.objects.filter(
            assignment=prev_assignment
        ).order_by('-date').first()
        
        if prev_state:
            initial_weight = float(prev_state.avg_weight_g)
```

### Option B: Use Transfer Workflow Data
If transition is tracked via `BatchTransferWorkflow`:
- Use `TransferAction.source_assignment` final weight
- More reliable if transfers are properly logged

### Option C: Disable Fallback to Stage Min Weight
Simply don't use `expected_weight_min_g` as fallback during transitions:
- Require explicit anchor or previous state
- Fail gracefully if neither available

---

## Testing Needed (If Fixed)

1. **Verify spike elimination** - regenerate daily states after fix
2. **Check all stage transitions** - Days 91, 181, 271, 361, 451
3. **Validate Growth Analysis chart** - orange line should be smooth
4. **Ensure no data loss** - growth samples still anchor correctly

---

## Related Files

- `apps/batch/services/growth_assimilation.py` - Core computation engine
- `apps/batch/models/daily_state.py` - ActualDailyAssignmentState model
- `client/src/features/batch-management/components/growth-analysis/GrowthAnalysisChart.tsx` - Visualization

---

## Notes

- This bug was discovered while validating the TGC formula fix
- The TGC formula fix is **complete and correct** - this is a separate issue
- Spikes only affect visualization, not actual operational data
- Could be addressed in future sprint focused on Growth Analysis refinement

---

**Priority:** Low-Medium (visual issue, self-correcting within 1 day)  
**Recommendation:** Document for now, fix in dedicated Growth Analysis refinement sprint

