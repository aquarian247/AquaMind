# FCR Calculation Architecture Analysis

**Date:** October 23, 2025  
**Status:** 🔴 **Issue Identified** - FCR calculation is NOT automatic  

---

## Executive Summary

FCR (Feed Conversion Ratio) calculations are currently **on-demand only**, NOT automatic. This means FCR data only exists when explicitly requested via API endpoints, not when users create feeding events or growth samples in real-time.

---

## Current Architecture (As-Is)

### 1. Feeding Event Creation
**Location:** `apps/inventory/api/serializers/feeding.py:114-131`

```python
@transaction.atomic
def create(self, validated_data):
    # Calculate feeding percentage
    feeding_percentage = (amount_kg / batch_biomass_kg) * 100
    validated_data['feeding_percentage'] = feeding_percentage
    
    # ❌ NO FCR CALCULATION HERE
    feeding_event = FeedingEvent.objects.create(**validated_data)
    return feeding_event
```

**What happens:**
- ✅ Feeding percentage is calculated
- ✅ FeedingEvent is saved to database
- ❌ **No FCR summary is created or updated**

---

### 2. On-Demand FCR Calculation
**Location:** `apps/operational/services/fcr_trends_service.py:153-190`

```python
def _ensure_container_summaries_exist(cls, start_date, end_date, ...):
    """
    Ensure container feeding summaries exist for the requested period.
    Called when FCR trends endpoint is accessed.
    """
    assignments = cls._get_relevant_assignments(batch_id, ...)
    periods = cls._generate_time_periods(start_date, end_date, interval)
    
    # CREATE summaries on-demand
    for assignment in assignments:
        for period_start, period_end in periods:
            FCRCalculationService.create_container_feeding_summary(
                assignment, period_start, period_end
            )
```

**When this runs:**
- ✅ When `/api/v1/operational/fcr-trends/` endpoint is called
- ✅ When frontend requests FCR data
- ❌ **NOT when feeding events are created**

---

## Problems with Current Approach

### 1. **Stale Data** ❌
- User adds feeding event at 10:00 AM
- FCR summary still shows yesterday's data until API endpoint is called

### 2. **Performance Issues** ⚠️
- First API request after many feeding events calculates all summaries
- Can cause **1-5 second delays** for busy batches
- Frontend shows loading spinners while calculations run

### 3. **Inconsistent UX** ❌
- Some batches have FCR data (recently viewed)
- Other batches show "N/A" (never viewed, even with feeding data)
- **Script-based backfills required** (as we just did)

### 4. **No Historical Tracking** ⚠️
- FCR summaries use `update_or_create` (line 1167 in fcr_service.py)
- Historical FCR values are **overwritten** when new data arrives
- Cannot track FCR improvements over time

---

## Recommended Architecture (To-Be)

### Option 1: **Django Signals** (Recommended for MVP) ✅

**Trigger:** When FeedingEvent or GrowthSample is saved

```python
# apps/inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inventory.models import FeedingEvent
from apps.batch.models import GrowthSample
from apps.inventory.services.fcr_service import FCRCalculationService
from datetime import date, timedelta

@receiver(post_save, sender=FeedingEvent)
def update_fcr_on_feeding_event(sender, instance, created, **kwargs):
    """
    When a feeding event is created/updated, recalculate FCR summaries.
    """
    if created:  # Only on new feeding events
        # Get the container assignment
        assignment = instance.batch_assignment
        if assignment:
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

@receiver(post_save, sender=GrowthSample)
def update_fcr_on_growth_sample(sender, instance, created, **kwargs):
    """
    When growth sample is added, recalculate FCR (new biomass affects FCR).
    """
    if created:
        batch = instance.batch
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Recalculate all container summaries for this batch
        assignments = batch.batchcontainerassignment_set.filter(is_active=True)
        for assignment in assignments:
            FCRCalculationService.create_container_feeding_summary(
                assignment, start_date, end_date
            )
        
        # Update batch-level summary
        FCRCalculationService.aggregate_container_fcr_to_batch(
            batch, start_date, end_date
        )
```

**Pros:**
- ✅ Real-time FCR updates
- ✅ No frontend delays
- ✅ Simple to implement
- ✅ Works in Django ORM transactions

**Cons:**
- ⚠️ Adds ~100-300ms to feeding event creation
- ⚠️ May cause issues with bulk imports (can be disabled for bulk operations)

---

### Option 2: **Celery Background Tasks** (Recommended for Scale) 🚀

**Trigger:** Async task queue after FeedingEvent saved

```python
# apps/inventory/tasks.py
from celery import shared_task
from apps.inventory.services.fcr_service import FCRCalculationService
from datetime import date, timedelta

@shared_task(bind=True, max_retries=3)
def recalculate_batch_fcr(self, batch_id):
    """
    Background task to recalculate FCR for a batch.
    """
    try:
        batch = Batch.objects.get(id=batch_id)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Recalculate container summaries
        assignments = batch.batchcontainerassignment_set.filter(is_active=True)
        for assignment in assignments:
            FCRCalculationService.create_container_feeding_summary(
                assignment, start_date, end_date
            )
        
        # Aggregate to batch level
        FCRCalculationService.aggregate_container_fcr_to_batch(
            batch, start_date, end_date
        )
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# In signals.py
@receiver(post_save, sender=FeedingEvent)
def queue_fcr_recalculation(sender, instance, created, **kwargs):
    if created:
        # Queue task (non-blocking)
        recalculate_batch_fcr.delay(instance.batch.id)
```

**Pros:**
- ✅ No performance impact on user requests
- ✅ Handles high-volume feeding events
- ✅ Retry logic for failures
- ✅ Can be prioritized/rate-limited

**Cons:**
- ⚠️ Requires Celery + Redis/RabbitMQ infrastructure
- ⚠️ Slight delay (5-30 seconds) before FCR updates
- ⚠️ More complex deployment

---

### Option 3: **Scheduled Batch Job** (Current Workaround) ⏰

**Trigger:** Cron job runs every hour/day

```bash
# Crontab
0 * * * * /path/to/venv/bin/python /path/to/manage.py calculate_fcr_all_batches
```

**Pros:**
- ✅ Simple to implement
- ✅ No performance impact
- ✅ Predictable resource usage

**Cons:**
- ❌ Stale data (up to 1 hour old)
- ❌ User confusion ("why isn't my FCR updating?")
- ❌ Still requires on-demand calculation for immediate needs

---

## Recommended Implementation Plan

### Phase 1: Django Signals (Immediate - 2 hours) ✅
1. Create `apps/inventory/signals.py`
2. Add signal receivers for FeedingEvent and GrowthSample
3. Register signals in `apps/inventory/apps.py:ready()`
4. Test with development data

**Why:** Solves the immediate problem with minimal infrastructure changes.

### Phase 2: Optimize Signal Logic (1 week) ⚡
1. Add debouncing (don't recalculate on every event)
2. Use database triggers for batch updates
3. Add caching layer for frequently accessed FCR data

**Why:** Improves performance for high-volume operations.

### Phase 3: Celery Migration (1-2 sprints) 🚀
1. Set up Celery infrastructure (Redis + workers)
2. Migrate signal logic to async tasks
3. Add task monitoring dashboard
4. Implement priority queue (new events = high priority)

**Why:** Scales to production workload (1000s of feeding events/day).

---

## Testing Checklist

- [ ] Create feeding event → FCR updates within 1 second (signals)
- [ ] Create feeding event → FCR updates within 30 seconds (Celery)
- [ ] Bulk import 1000 feeding events → FCR calculates without timeout
- [ ] Growth sample added → FCR recalculates with new biomass
- [ ] Multiple concurrent feeding events → no race conditions
- [ ] Failed FCR calculation → retries automatically (Celery)

---

## Files to Modify

### For Signal Implementation:
1. ✅ Create `apps/inventory/signals.py` (new file)
2. ✅ Modify `apps/inventory/apps.py` (register signals)
3. ✅ Add `apps/inventory/management/commands/recalculate_fcr.py` (manual trigger)
4. ⚠️ Update `apps/inventory/api/serializers/feeding.py` (add signal flag for bulk operations)

### For Celery Implementation:
5. ✅ Create `apps/inventory/tasks.py` (Celery tasks)
6. ✅ Modify `aquamind/settings.py` (Celery config)
7. ✅ Create `docker-compose.celery.yml` (Redis + Celery workers)
8. ✅ Update deployment docs

---

## Decision Required

**Question for Product Owner:**

> Should FCR calculations be:
> 1. **Real-time** (signals) - FCR updates immediately when feeding event is saved
> 2. **Near real-time** (Celery) - FCR updates within 30 seconds
> 3. **Periodic** (cron) - FCR updates every hour

**Current state:** Manual scripts + on-demand API calculation (not acceptable for production)

**Recommendation:** Start with **signals (Option 1)**, migrate to **Celery (Option 2)** when scaling.

---

## References

- FCR Calculation Service: `apps/inventory/services/fcr_service.py`
- FCR Trends Service: `apps/operational/services/fcr_trends_service.py`
- Feeding Event Serializer: `apps/inventory/api/serializers/feeding.py`
- Backend FCR Fix (Oct 22): `docs/progress/2025-10-22-frontend-backend-integration-debugging-session.md`

