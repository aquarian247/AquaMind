# Event Model FK Pattern Audit Results

**Date**: 2025-11-18  
**Auditor**: Claude (AI Assistant)  
**Purpose**: Identify all event models with incorrect FK granularity before remediation

---

## Executive Summary

**Models Requiring Fixes**: 3  
**Models Verified Correct**: 2  
**Proration Workarounds Found**: 1 (Growth Engine mortality calculation)

---

## Detailed Audit Results

| Model | App | Current FK Pattern | Should Be | Fix Required | Priority | Line Ref |
|-------|-----|-------------------|-----------|--------------|----------|----------|
| `MortalityEvent` | batch | `batch` only | `batch` + `assignment` | **YES** | CRITICAL | models/mortality.py:26 |
| `LiceCount` | health | `batch` only | `batch` + `assignment` | **YES** | HIGH | models/mortality.py:198 |
| `MortalityRecord` | health | `batch` + `container` | `batch` + `container` + `assignment` | **YES** | HIGH | models/mortality.py:36 |
| `Treatment` | health | `batch` + `assignment` + `container` | ✅ CORRECT | NO | N/A | models/treatment.py:35-44 |
| `FeedingEvent` | inventory | `batch` + `batch_assignment` + `container` | ✅ CORRECT | NO | N/A | models/feeding.py:29-42 |
| `EnvironmentalReading` | environmental | `batch` + `container` + `assignment` | ✅ MODEL CORRECT | NO* | MEDIUM | models.py:72-79 |

**Notes**:
- `*` EnvironmentalReading has correct FK structure, but event engine doesn't populate `batch_container_assignment` FK

---

## Audit Criteria Applied

For each model, we verified:

1. **Operational Reality**: Does operator record event at specific container?
2. **Event Engine Pattern**: Is event calculated per-container in data generation?
3. **Service Layer Usage**: Does any service "prorate" this event from batch to container?

---

## Findings by Model

### ❌ CRITICAL: `batch.MortalityEvent`

**Current State**:
```python
batch = models.ForeignKey(Batch, on_delete=models.PROTECT, 
                         related_name='mortality_events')
# NO assignment FK!
```

**Issues Identified**:
1. Event engine creates mortality per-assignment (loop at line 652) but stores to batch
2. Growth Engine prorates batch mortality across assignments (lines 787-803)
3. Confidence reduced to 0.9 due to proration uncertainty
4. Loss of container-specific mortality data

**Evidence**:
- `scripts/data_generation/03_event_engine_core.py` line 652-671: Loops `for a in self.assignments` but creates with `batch=self.batch` only
- `apps/batch/services/growth_assimilation.py` lines 787-803: Proration workaround with comment "MortalityEvent is tracked at batch level, not assignment level"

**Fix Required**: Add `assignment` FK, keep `batch` FK for query performance

---

### ❌ HIGH: `health.LiceCount`

**Current State**:
```python
batch = models.ForeignKey(Batch, on_delete=models.CASCADE, 
                         related_name='lice_counts')
container = models.ForeignKey(Container, on_delete=models.SET_NULL, 
                             null=True, blank=True, 
                             related_name='lice_counts')
# NO assignment FK!
```

**Issues Identified**:
1. Lice sampling is container-specific (operators sample specific tanks)
2. Has `container` FK but no `assignment` FK
3. Can't track which batch-in-container had the lice infestation

**Operational Reality**:
- Lice counts are taken from specific containers
- Multiple batches can be in same container over time
- Need to know WHICH batch assignment had the lice

**Fix Required**: Add `assignment` FK, keep `batch` + `container` for backward compatibility

---

### ❌ HIGH: `health.MortalityRecord`

**Current State**:
```python
batch = models.ForeignKey(Batch, on_delete=models.CASCADE, 
                         related_name='mortality_records')
container = models.ForeignKey(Container, on_delete=models.SET_NULL, 
                             null=True, blank=True, 
                             related_name='mortality_records')
# NO assignment FK!
```

**Issues Identified**:
1. Has complex `save()` method that prorates mortality across assignments (lines 69-189)
2. Similar to `MortalityEvent` but in health app
3. Loss of precision in which assignment had mortality

**Note**: This model has sophisticated save() logic that finds and updates assignments, but stores no direct link to the assignment it updated!

**Fix Required**: Add `assignment` FK for precision

---

### ✅ CORRECT: `health.Treatment`

**Current State**:
```python
batch = models.ForeignKey(Batch, ...)
container = models.ForeignKey(Container, ..., null=True, blank=True)
batch_assignment = models.ForeignKey(BatchContainerAssignment, ..., 
                                    null=True, blank=True)
```

**Analysis**: Has all three FKs - batch (convenience), container (location), assignment (precision). **No changes needed**.

---

### ✅ CORRECT: `inventory.FeedingEvent`

**Current State**:
```python
batch = models.ForeignKey(Batch, ...)
batch_assignment = models.ForeignKey(BatchContainerAssignment, ..., 
                                    null=True, blank=True)
container = models.ForeignKey(Container, ...)
```

**Analysis**: Has all necessary FKs. Event engine properly populates `batch_assignment=a` (line 588). **No changes needed**.

---

### ⚠️ BONUS FIX: `environmental.EnvironmentalReading`

**Current State** (MODEL):
```python
batch = models.ForeignKey(Batch, ..., null=True, blank=True)
container = models.ForeignKey(Container, ..., null=True, blank=True)
sensor = models.ForeignKey(Sensor, ..., null=True, blank=True)
batch_container_assignment = models.ForeignKey(
    BatchContainerAssignment,
    on_delete=models.SET_NULL,
    null=True, blank=True,
    help_text="Direct link to batch-container assignment..."
)
```

**Analysis**: Model structure is CORRECT (intentionally denormalized for TimescaleDB hypertable performance).

**Issue**: Event engine doesn't populate `batch_container_assignment` FK when creating readings.

**Fix**: 1-line change in event engine (around line 469) to add `batch_container_assignment=a`

---

## Proration Workaround Analysis

### Growth Engine: Mortality Proration

**File**: `apps/batch/services/growth_assimilation.py` (lines 787-803)

**Workaround Code**:
```python
# Get batch-level mortality
actual_count = mortality_events.aggregate(Sum('count'))['count__sum']

if actual_count:
    # PRORATION HACK - Assumes mortality distributed by population
    batch_population = self._get_batch_population(date)
    assignment_share = current_population / batch_population
    prorated_mortality = int(round(actual_count * assignment_share))
    return prorated_mortality, 'actual_prorated', 0.9  # ← Lower confidence!
```

**Impact**:
- Reduces confidence from 1.0 to 0.9
- Assumes proportional distribution (may not reflect reality)
- Container with disease outbreak gets same rate as healthy containers

**Fix**: After adding `assignment` FK to `MortalityEvent`, query directly:
```python
mortality_events = MortalityEvent.objects.filter(
    assignment=self.assignment,
    event_date=date
)
actual_count = mortality_events.aggregate(Sum('count'))['count__sum'] or 0
return actual_count, 'actual', 1.0  # Full confidence!
```

---

### FCR Service: Composition Proration

**File**: `apps/inventory/services/fcr_service.py`

**Analysis**: The proration here is for **mixed batch feed composition**, which is LEGITIMATE and should NOT be changed. This is different from the mortality FK issue.

**Grep Results Showing Legitimate Use**:
- `_prorate_feed_by_composition()` method (line 98-103)
- Used for calculating feed amounts when multiple source batches contribute to a mixed batch
- This is correct business logic, not a workaround for poor FK design

---

## Recommendations

### Immediate Actions (Critical Path)

1. ✅ **Fix `MortalityEvent`**: Add `assignment` FK, update event engine, simplify Growth Engine
2. ✅ **Fix `LiceCount`**: Add `assignment` FK (similar pattern)
3. ✅ **Fix `MortalityRecord`**: Add `assignment` FK (similar pattern)
4. ✅ **Bonus: `EnvironmentalReading`**: Populate `batch_container_assignment` in event engine

### Migration Strategy

**Keep denormalized FKs** (user preference):
- Keep `batch` FK for query performance
- Add `assignment` FK for precision
- Add model validation: `assignment.batch == batch`

### Test Impact Estimate

**Backend Tests to Update**: ~16 files
- `apps/batch/tests/models/test_mortality_event_model.py`
- `apps/batch/tests/api/test_analytics.py`
- `apps/batch/tests/api/test_geography_summary.py`
- `scripts/diagnose_data_generation.py`
- `scripts/simulate_full_lifecycle.py`
- Plus all health app mortality tests

**API Changes**: Serializers need `assignment` field added

**Frontend Impact**: TypeScript client regeneration, form updates for mortality/lice entry

---

## Acceptance Criteria for Fixes

For each model fix:
- ✅ Migration creates `assignment` FK field
- ✅ Model has `clean()` validation for FK consistency
- ✅ Serializer includes `assignment` field
- ✅ Event engine populates `assignment` when creating records
- ✅ Service layer removes proration workarounds
- ✅ All tests pass
- ✅ OpenAPI schema updated
- ✅ Frontend client regenerated

---

## Conclusion

**Total Models Requiring Fixes**: 3 (MortalityEvent, LiceCount, MortalityRecord)  
**Bonus Fix**: 1 (EnvironmentalReading event engine population)  
**Estimated Timeline**: 12-15 hours for complete remediation

The audit confirms the issue described in `ISSUE_MORTALITY_EVENT_FK_DESIGN_FLAW.md`. The FK pattern inconsistency affects multiple models and has cascading impacts on service layer code (proration workarounds) and data precision.

**Next Steps**: Proceed to Phase 2 (Database Migrations) per implementation plan.

