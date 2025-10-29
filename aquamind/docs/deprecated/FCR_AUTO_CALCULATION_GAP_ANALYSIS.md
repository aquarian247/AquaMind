# FCR Automatic Calculation - Gap Analysis

**Date:** October 23, 2025  
**Analyst:** AI Assistant  
**Status:** 🔴 **Critical Gap Identified**

---

## Executive Summary

The **FCR Enhancement Project** (GitHub Issue #19) was **95% implemented** but is **missing automatic triggers**. FCR calculations only run:

1. ✅ **On-demand** - When API endpoint `/api/v1/operational/fcr-trends/` is called
2. ✅ **Manual scripts** - When administrators run backfill scripts
3. ❌ **NOT automatic** - When users create feeding events or growth samples

**Impact:** Users experience stale FCR data, requiring manual script runs to see updated metrics.

---

## What Was Implemented ✅

### 1. Data Model (100% Complete)
**Location:** `apps/inventory/models/summary.py`

✅ **ContainerFeedingSummary** model:
- `confidence_level` field (VERY_HIGH, HIGH, MEDIUM, LOW)
- `estimation_method` field (MEASURED, INTERPOLATED, MIXED)
- `fcr` field with weighted calculations
- `total_growth_kg` tracking

✅ **BatchFeedingSummary** model:
- `overall_confidence_level` field
- `estimation_method` field
- `weighted_avg_fcr` across containers
- `container_count` tracking

✅ **BatchContainerAssignment** model:
**Location:** `apps/batch/models/assignment.py:50-53`
```python
last_weighing_date = models.DateField(
    null=True, blank=True,
    help_text="Date of the most recent growth sample (weighing) for this assignment"
)
```

### 2. Calculation Services (100% Complete)

✅ **FCRCalculationService** (`apps/inventory/services/fcr_service.py`):
- `calculate_container_fcr()` - Container-level FCR with confidence
- `create_container_feeding_summary()` - Save container summary
- `aggregate_container_fcr_to_batch()` - Aggregate to batch level
- `_get_container_growth_data()` - Biomass growth calculation (fixed Oct 22)
- `_get_batch_growth_data()` - Batch-level growth tracking

✅ **FCRTrendsService** (`apps/operational/services/fcr_trends_service.py`):
- `get_fcr_trends()` - Generate time-series FCR data
- `_ensure_container_summaries_exist()` - **On-demand calculation trigger**
- Support for DAILY/WEEKLY/MONTHLY intervals
- Support for batch/container/geography aggregation levels

### 3. API Endpoints (100% Complete)

✅ **FCR Trends Endpoint:**
- URL: `/api/v1/operational/fcr-trends/`
- Operation ID: `api_v1_operational_fcr_trends_list`
- Query params: `batch_id`, `assignment_id`, `geography_id`, `interval`, `start_date`, `end_date`
- Returns: Time-series with `actual_fcr`, `confidence`, `predicted_fcr`

✅ **Feeding Summaries Endpoints:**
- Container summaries: `/api/v1/inventory/container-feeding-summaries/`
- Batch summaries: `/api/v1/inventory/batch-feeding-summaries/`

---

## What Was NOT Implemented ❌

### 1. Django Signals for Automatic Calculation

**Missing:** `apps/inventory/signals.py`

**Expected (from implementation plan Phase 3.2):**
```python
# apps/inventory/signals.py - DOES NOT EXIST

@receiver(post_save, sender=FeedingEvent)
def update_fcr_on_feeding_event(sender, instance, created, **kwargs):
    """Auto-update FCR when feeding event created."""
    pass  # NOT IMPLEMENTED

@receiver(post_save, sender=GrowthSample)
def update_fcr_on_growth_sample(sender, instance, created, **kwargs):
    """Auto-update FCR when growth sample created."""
    pass  # NOT IMPLEMENTED
```

**Current state:**
- `apps/inventory/apps.py` has NO `ready()` method (signals not registered)
- `apps/batch/signals.py` exists but only handles batch completion, NOT FCR

### 2. Auto-Update of `last_weighing_date`

**Expected (from implementation plan):**
> "Use Django signals or model save() overrides to auto-update last_weighing_date on GrowthSample creation"

**Current state:**
- ❌ `last_weighing_date` field exists in BatchContainerAssignment
- ❌ NO signal to update it when GrowthSample is created
- ❌ Field remains null unless manually updated

### 3. Automatic Triggers in Serializers

**Location:** `apps/inventory/api/serializers/feeding.py:114-131`

**Current `create()` method:**
```python
@transaction.atomic
def create(self, validated_data):
    # Calculate feeding percentage
    feeding_percentage = (amount_kg / batch_biomass_kg) * 100
    validated_data['feeding_percentage'] = feeding_percentage
    
    # Create the feeding event
    feeding_event = FeedingEvent.objects.create(**validated_data)
    
    # ❌ NO FCR RECALCULATION TRIGGERED
    
    return feeding_event
```

**What's missing:**
- No call to `FCRCalculationService.create_container_feeding_summary()`
- No signal emission
- No async task queuing

---

## Current FCR Calculation Flow

### Scenario 1: User Creates Feeding Event via UI
```
1. User submits feeding event form
2. POST /api/v1/inventory/feeding-events/
3. FeedingEventSerializer.create() saves to DB
4. ❌ NO FCR CALCULATION
5. Frontend shows old FCR data (stale)
```

### Scenario 2: User Views FCR Trends
```
1. User navigates to batch analytics page
2. Frontend calls GET /api/v1/operational/fcr-trends/?batch_id=X
3. FCRTrendsService._ensure_container_summaries_exist() runs
4. ✅ FCR CALCULATED ON-DEMAND (1-5 second delay)
5. Frontend displays updated FCR
```

### Scenario 3: Administrator Runs Backfill Script
```
1. Admin runs: python scripts/generate_all_batch_fcr.py
2. ✅ FCR CALCULATED FOR ALL BATCHES
3. Frontend shows updated data
```

---

## Impact Assessment

### For Users:
- ❌ **Stale Data**: FCR shown is hours/days old
- ❌ **Slow First Load**: 1-5 second delay when viewing FCR for first time
- ❌ **Confusing UX**: "I just added feeding, why isn't FCR updated?"
- ❌ **Inconsistent**: Some batches have FCR (recently viewed), others show N/A

### For Operations:
- ⚠️ **Manual Intervention**: Requires running scripts periodically
- ⚠️ **Missing Real-Time Alerts**: Can't alert on FCR threshold breaches immediately
- ⚠️ **Incomplete Audit Trail**: Historical FCR not preserved (overwritten on recalc)

### For Development:
- ✅ **Performance**: No overhead on feeding event creation (fast writes)
- ❌ **User Trust**: Appears broken when FCR doesn't update
- ⚠️ **Technical Debt**: Requires scheduled jobs or manual scripts

---

## Recommended Fix: Implement Django Signals

### Implementation (Est. 2-3 hours)

**Step 1: Create signals.py**
```python
# apps/inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inventory.models import FeedingEvent
from apps.batch.models import GrowthSample
from apps.inventory.services.fcr_service import FCRCalculationService
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=FeedingEvent)
def recalculate_fcr_on_feeding_event(sender, instance, created, **kwargs):
    """
    When a feeding event is created, recalculate FCR for the batch.
    Uses a 30-day rolling window for continuous updates.
    """
    if not created:
        return  # Only trigger on new events, not updates
    
    try:
        assignment = instance.batch_assignment
        if not assignment or not assignment.is_active:
            logger.debug(f"Skipping FCR calc for inactive assignment")
            return
        
        # Calculate for last 30 days (rolling window)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Update container-level summary
        FCRCalculationService.create_container_feeding_summary(
            assignment, start_date, end_date
        )
        
        # Update batch-level summary
        FCRCalculationService.aggregate_container_fcr_to_batch(
            instance.batch, start_date, end_date
        )
        
        logger.info(
            f"✅ FCR recalculated for batch {instance.batch.batch_number} "
            f"after feeding event"
        )
    except Exception as e:
        logger.error(f"❌ FCR calculation failed: {e}", exc_info=True)


@receiver(post_save, sender=GrowthSample)
def update_fcr_and_weighing_date_on_growth_sample(sender, instance, created, **kwargs):
    """
    When growth sample is added:
    1. Update last_weighing_date on all active assignments
    2. Recalculate FCR (new biomass affects growth calculation)
    """
    if not created:
        return
    
    try:
        batch = instance.batch
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Update last_weighing_date for all active assignments
        active_assignments = batch.batchcontainerassignment_set.filter(is_active=True)
        active_assignments.update(last_weighing_date=instance.date)
        
        # Recalculate all container summaries for this batch
        for assignment in active_assignments:
            FCRCalculationService.create_container_feeding_summary(
                assignment, start_date, end_date
            )
        
        # Update batch-level summary
        FCRCalculationService.aggregate_container_fcr_to_batch(
            batch, start_date, end_date
        )
        
        logger.info(
            f"✅ FCR and weighing dates updated for batch {batch.batch_number} "
            f"after growth sample ({instance.avg_weight_g}g)"
        )
    except Exception as e:
        logger.error(f"❌ Growth sample FCR update failed: {e}", exc_info=True)
```

**Step 2: Register signals in apps.py**
```python
# apps/inventory/apps.py
class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Feed and Inventory Management'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import apps.inventory.signals  # noqa
```

**Step 3: Add bulk import flag**
```python
# apps/inventory/api/serializers/feeding.py
class FeedingEventSerializer(...):
    skip_fcr_calculation = False  # Class variable for bulk operations
    
    def create(self, validated_data):
        # ... existing code ...
        feeding_event = FeedingEvent.objects.create(**validated_data)
        
        # Signal will handle FCR unless bulk flag is set
        if self.skip_fcr_calculation:
            logger.debug("Skipping FCR calculation (bulk mode)")
        
        return feeding_event
```

---

## Testing Plan

### Unit Tests
```python
# apps/inventory/tests/test_signals.py
def test_fcr_updates_on_feeding_event_creation():
    """FCR summary is created when feeding event is saved."""
    batch = create_batch()
    assignment = create_assignment(batch)
    
    # Before: No FCR summary exists
    assert BatchFeedingSummary.objects.filter(batch=batch).count() == 0
    
    # Create feeding event (should trigger signal)
    create_feeding_event(batch, assignment)
    
    # After: FCR summary exists
    assert BatchFeedingSummary.objects.filter(batch=batch).count() == 1
    summary = BatchFeedingSummary.objects.get(batch=batch)
    assert summary.weighted_avg_fcr is not None
```

### Integration Tests
- Bulk import 100 feeding events → FCR updates 100 times (performance test)
- Add growth sample → `last_weighing_date` updates automatically
- Concurrent feeding events → no race conditions

---

## Performance Considerations

### Signal Overhead
- Current on-demand calc: **0ms** during feeding event creation + **1-5s** on first API call
- With signals: **100-300ms** during feeding event creation + **0ms** on API call

**Net effect:** Better UX (instant FCR updates) at cost of slightly slower writes.

### Optimization Strategies
1. **Debouncing:** Only recalculate if >1 hour since last calc (use cache flag)
2. **Selective Updates:** Only recalculate if feeding event is significant (>1% of biomass)
3. **Async Tasks:** Move to Celery for batches with >10 containers (Phase 2)

---

## Decision Matrix

| Approach | Implementation Time | User Experience | Performance | Complexity |
|----------|-------------------|-----------------|-------------|------------|
| **Current (On-Demand)** | ✅ 0h (done) | ❌ Stale data | ✅ Fast writes | ✅ Simple |
| **Django Signals** | ⚠️ 2-3h | ✅ Real-time | ⚠️ Slower writes | ⚠️ Medium |
| **Celery Tasks** | ❌ 2 days | ✅ Near real-time | ✅ Fast writes | ❌ Complex |
| **Scheduled Cron** | ✅ 1h | ❌ Very stale | ✅ Fast writes | ✅ Simple |

**Recommendation:** Implement **Django Signals** (Option 2) for immediate user value.

---

## Implementation Status

### Phase 1: Data Model ✅ (100%)
- [x] confidence_level field added
- [x] estimation_method field added  
- [x] last_weighing_date field added
- [x] Migrations created and applied

### Phase 2: Services ✅ (100%)
- [x] FCRCalculationService implemented
- [x] Container-level FCR calculation
- [x] Batch-level aggregation
- [x] Confidence assessment logic
- [x] Growth data extraction (fixed Oct 22)

### Phase 3: API ✅ (100%)
- [x] FCR trends endpoint created
- [x] Query parameters implemented
- [x] Time-series aggregation (DAILY/WEEKLY/MONTHLY)
- [x] Geography/Batch/Container filtering
- [x] OpenAPI spec updated

### Phase 4: Automatic Triggers ❌ (0%)
- [ ] Django signals for FeedingEvent
- [ ] Django signals for GrowthSample
- [ ] Signal registration in apps.py
- [ ] Auto-update last_weighing_date
- [ ] Bulk operation flag

### Phase 5: Testing ⚠️ (Partial)
- [x] Service unit tests exist
- [x] API endpoint tests exist
- [ ] Signal integration tests
- [ ] Performance tests with signals

---

## Files to Create/Modify

### New Files:
1. `apps/inventory/signals.py` (NEW - ~100 lines)
2. `apps/inventory/tests/test_signals.py` (NEW - ~150 lines)

### Modified Files:
3. `apps/inventory/apps.py` (add ready() method - 5 lines)
4. `apps/inventory/api/serializers/feeding.py` (optional bulk flag - 10 lines)

---

## Why This Matters

### Current User Experience:
```
👤 User: "I just added 500kg of feed to Batch FI-2024-002"
📊 System: [Shows FCR from yesterday... still 1.80]
👤 User: "Why isn't FCR updated? Is it broken?"
🔧 Admin: [Runs script manually]
📊 System: [Now shows 1.82]
👤 User: "Why did it take 10 minutes?"
```

### With Automatic Triggers:
```
👤 User: "I just added 500kg of feed to Batch FI-2024-002"
📊 System: [Automatically recalculates... FCR now 1.82]
👤 User: "Perfect! FCR went up slightly, as expected"
```

---

## References

- **Implementation Plan:** `docs/progress/fcr_enhancement/fcr_implementation_plan.md`
- **PRD:** `docs/progress/fcr_enhancement/fcr_prd.md`
- **Service Code:** `apps/inventory/services/fcr_service.py`
- **Trends Service:** `apps/operational/services/fcr_trends_service.py`
- **Backend Fix (Oct 22):** Biomass growth calculation implemented
- **Frontend Integration (Oct 23):** Honest fallbacks for null FCR values

---

## Next Action

**Implement Django signals to enable automatic FCR calculation** when users interact with the system through normal data entry workflows.

