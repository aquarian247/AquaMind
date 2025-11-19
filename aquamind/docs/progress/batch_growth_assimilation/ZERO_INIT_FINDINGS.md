# Zero-Initialization Findings - Critical Discovery

**Date**: November 18, 2025  
**Issue**: #112 - Population Doubling  
**Status**: ⚠️ **ZERO-INIT NOT VIABLE FOR TEST DATA**

---

## 🔍 Discovery

**Zero-initialization approach** (`population_count=0` on destinations) fixes the population doubling bug for **Growth Analysis**, but **breaks event engine's daily processing**.

---

## ❌ Why Zero-Init Fails for Test Data

### The Problem:

```python
# Day 90 transition creates new assignments:
new_assignment = BatchContainerAssignment.objects.create(
    population_count=0,              # ← Zero-initialized
    biomass_kg=0.00                  # ← Calculated from population_count
)

# TransferAction records the fish:
TransferAction.objects.create(
    transferred_count=305,973        # ← Fish are here!
)

# BUT: Event engine's daily processing (line 488):
def feed_events(self, hour):
    for a in self.assignments:
        biomass = float(a.biomass_kg)  # ← Reads metadata, not transfers!
        if biomass <= 0: continue       # ← SKIPS FEEDING!
```

**Result**:
- ❌ No feeding events (biomass=0)
- ❌ No growth (no feed → no TGC growth)
- ❌ Population stays 0 (not updated from transfers)
- ❌ No scenarios created (population=0 check fails)

---

## ✅ What Works

### Growth Analysis Engine (Production Code):

```python
# apps/batch/services/growth_assimilation.py line 467-550
initial_population = self.assignment.population_count  # Start with metadata

# Each day:
placements = sum(transfer.transferred_count for transfer in transfers_in)
new_population = prev_population + placements - mortality
```

**This correctly adds transfers to initial population!**

---

## 🎯 The Core Conflict

### Two Different Consumers:

| Consumer | Uses | Requirement |
|----------|------|-------------|
| **Event Engine** (test data gen) | `assignment.population_count` | Must be >0 for daily processing |
| **Growth Analysis** (production) | `assignment.population_count` + `transfer.transferred_count` | Both shouldn't have same count |

### The Dilemma:

- **If population_count=0**: Growth analysis works ✅, Event engine breaks ❌
- **If population_count>0**: Event engine works ✅, Growth analysis doubles ❌

---

## 💡 Solution: Fix Growth Engine, Not Test Data

### Current Growth Engine (Line 467):
```python
# Start with assignment metadata
initial_population = self.assignment.population_count
```

### Proposed Fix:
```python
# For NEW assignments (first day), check if it's a transfer destination
first_day = self.batch.start_date or self.assignment.assignment_date

if current_date == first_day or current_date == self.assignment.assignment_date:
    # Check if this assignment has transfers IN on first day
    transfers_in = TransferAction.objects.filter(
        dest_assignment=self.assignment,
        actual_execution_date=current_date
    )
    
    if transfers_in.exists():
        # This is a transfer destination - start from 0, add transfers
        initial_population = 0
    else:
        # This is initial placement (creation workflow) - use metadata
        initial_population = self.assignment.population_count
else:
    # Not first day - use metadata
    initial_population = self.assignment.population_count
```

**This distinguishes**:
- **Initial placements** (creation workflow): Use metadata
- **Transfer destinations** (transfer workflow): Start from 0, add transfers

---

## 🔧 Alternative: Keep Test Data As-Is

### Simpler Approach:

**For Test Data Generation**: Keep pre-populating assignments (current behavior)  
**For Growth Engine**: Check if assignment has incoming transfers on first day
- If YES: Subtract transfer count from initial (avoid double-count)
- If NO: Use metadata as-is

```python
# Line 467 in growth_assimilation.py:
initial_population = self.assignment.population_count

# Check for transfers on first day
first_day_transfers = TransferAction.objects.filter(
    dest_assignment=self.assignment,
    actual_execution_date=self.assignment.assignment_date
).aggregate(Sum('transferred_count'))['transferred_count__sum'] or 0

# If there are first-day transfers, this might be double-counted
# Subtract them from initial to avoid inflation
if first_day_transfers > 0:
    initial_population = max(0, initial_population - first_day_transfers)
```

---

## 📋 Recommendation

**Short Term** (This Session):
1. ✅ Revert zero-initialization in test data generation
2. ✅ Keep assignments pre-populated (old behavior)
3. ✅ Document that Growth Engine needs fix

**Next Session** (Growth Engine Fix):
1. Modify `growth_assimilation.py` to detect transfer destinations
2. Avoid double-counting transfers on first day
3. Test with both test data and production workflows

---

## 🎯 Action Required

**Revert These Lines**:
- Line 845: `population_count=0` → `population_count=fish_per_container`
- Line 913: `population_count=0` → `population_count=container_fish`

**Keep These Lines**:
- Line 1049: `transferred = source_pop` ✅ (correct)
- Celery signal skip ✅ (correct)
- "From batch" scenarios ✅ (correct)

---

**Status**: ⚠️ **Zero-init approach postponed**  
**Next**: Revert to pre-populated assignments, fix Growth Engine later  
**Priority**: Get test data working NOW, optimize later

---

*End of Zero-Init Findings*

