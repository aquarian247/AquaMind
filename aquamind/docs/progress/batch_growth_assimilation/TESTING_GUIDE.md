# Phase 8/8.5 Integration Testing Guide

**Last Updated:** December 11, 2025  
**Status:** Ready for Manual Testing  
**Prerequisite:** Production-scale test data (145+ batches)

---

## The Testing Challenge

AquaMind's operational features form a symbiotic loop that's hard to test because:
1. **Time compression**: Real batches take 2+ years; we can't wait
2. **Event density**: Millions of events per batch (feeding, environmental, growth)
3. **Feedback loops**: Plans → Execution → Actuals → Triggers → New Plans

**Solution**: Use the test data generation system to create realistic historical data, then manually trigger the feedback mechanisms.

---

## Current Data State

As of December 11, 2025:
```
Batches: 145 (59 active, 86 completed)
ActualDailyAssignmentState: 978,131 records
PlannedActivities: 1,181 (491 pending, 690 completed)
Data staleness: 16 days (latest: 2025-11-25)
```

---

## Quick Refresh Commands

### Option 1: Just Update Daily States (5-10 minutes)
If you just need fresh ActualDailyAssignmentState records:

```bash
cd /Users/aquarian247/Projects/AquaMind

# This recomputes growth analysis for all batches up to today
python scripts/data_generation/run_growth_analysis_optimized.py --workers 4
```

### Option 2: Refresh Planned Activities (30 seconds)
Re-seed activities from templates for active batches:

```bash
# This creates fresh PlannedActivities based on current templates
python scripts/data_generation/seed_planned_activities.py
```

### Option 3: Full Data Refresh (60-90 minutes)
Complete regeneration with fresh events:

```bash
# 1. Wipe operational data (preserves infrastructure)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 2. Initialize master data
python scripts/data_generation/01_initialize_scenario_master_data.py
python scripts/data_generation/01_initialize_finance_policies.py
python scripts/data_generation/01_initialize_health_parameters.py
python scripts/data_generation/01_initialize_activity_templates.py

# 3. Generate batches (45-60 min)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/schedule_4years_final.yaml --workers 14 --use-partitions

# 4. Compute growth analysis (8-10 min)
python scripts/data_generation/run_growth_analysis_optimized.py --workers 4

# 5. Seed planned activities (30 sec)
python scripts/data_generation/seed_planned_activities.py
```

---

## Manual Testing Flows

### Test 1: Variance Analysis (Completed Activities)

**Goal**: Verify the `variance-from-actual` endpoint returns meaningful data.

**Steps**:
```bash
# 1. Find a completed activity with a batch that has daily states
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.planning.models import PlannedActivity
from apps.batch.models import ActualDailyAssignmentState

for act in PlannedActivity.objects.filter(status='COMPLETED').select_related('batch')[:5]:
    has_states = ActualDailyAssignmentState.objects.filter(
        batch=act.batch, 
        date=act.completed_at.date() if hasattr(act.completed_at, 'date') else act.completed_at
    ).exists()
    print(f'Activity {act.id}: {act.activity_type} for {act.batch.batch_number}')
    print(f'  Completed: {act.completed_at}, Has states: {has_states}')
"
```

**API Test** (use a found activity ID):
```bash
# Replace <ID> with an activity ID from above
curl -X GET "http://localhost:8000/api/v1/planning/planned-activities/<ID>/variance-from-actual/" \
  -H "Authorization: Bearer <token>"
```

**Expected Response**:
```json
{
  "activity_id": 123,
  "planned_date": "2024-06-15",
  "actual_date": "2024-06-17",
  "variance_days": 2,
  "actual_weight_g": 105.3,
  "actual_population": 48500,
  "actual_fcr": 1.15,
  "projected_weight_g": 100.0
}
```

---

### Test 2: Projection Preview (Pending Activities)

**Goal**: Verify hover tooltips show scenario-based rationale.

**Steps**:
```bash
# Find a pending activity with a scenario
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.planning.models import PlannedActivity
from apps.scenario.models import ProjectionDay

for act in PlannedActivity.objects.filter(status='PENDING').select_related('batch', 'scenario')[:5]:
    has_projection = ProjectionDay.objects.filter(
        projection_run__scenario=act.scenario,
        batch=act.batch,
        day_date=act.due_date
    ).exists()
    print(f'Activity {act.id}: {act.activity_type} due {act.due_date}')
    print(f'  Batch: {act.batch.batch_number}, Scenario: {act.scenario_id}, Has projection: {has_projection}')
"
```

**API Test**:
```bash
curl -X GET "http://localhost:8000/api/v1/planning/planned-activities/<ID>/projection-preview/" \
  -H "Authorization: Bearer <token>"
```

**Expected Response**:
```json
{
  "activity_id": 456,
  "due_date": "2025-04-20",
  "scenario_id": 12,
  "scenario_name": "Auto-generated scenario",
  "projected_weight_g": 150.5,
  "projected_population": 47000,
  "projected_biomass_kg": 7073.5,
  "day_number": 180,
  "rationale": "Projected from scenario model at day 180"
}
```

---

### Test 3: Activity Completion Signal (The Feedback Loop)

**Goal**: Verify completing an activity triggers growth assimilation recompute.

**Prerequisites**: Celery worker running (or test in Django shell with mock).

**Steps**:
```bash
# Start Celery worker in a separate terminal
cd /Users/aquarian247/Projects/AquaMind
celery -A aquamind worker -l info

# In another terminal - complete an activity and watch for recompute
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.planning.models import PlannedActivity
from apps.batch.models import ActualDailyAssignmentState
from datetime import date

# Find a pending activity of type that triggers recompute
act = PlannedActivity.objects.filter(
    status='PENDING',
    activity_type__in=['TRANSFER', 'VACCINATION', 'SAMPLING']
).first()

if act:
    print(f'Completing activity {act.id}: {act.activity_type}')
    print(f'Batch: {act.batch.batch_number}')
    
    # Check daily states before
    before_count = ActualDailyAssignmentState.objects.filter(batch=act.batch).count()
    latest_before = ActualDailyAssignmentState.objects.filter(batch=act.batch).order_by('-date').first()
    print(f'Before: {before_count} states, latest: {latest_before.date if latest_before else None}')
    
    # Complete the activity
    act.status = 'COMPLETED'
    act.completed_at = date.today()
    act.save()  # This triggers on_planned_activity_completed signal
    
    print('Activity completed! Check Celery logs for recompute task.')
else:
    print('No suitable pending activity found')
"
```

**Expected**: Celery log shows `enqueue_batch_recompute` task queued.

---

### Test 4: Weight Threshold Trigger

**Goal**: Verify that reaching a weight threshold auto-generates PlannedActivity.

**Steps**:
```bash
# 1. Create a test ActivityTemplate with weight threshold
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.planning.models import ActivityTemplate
from apps.batch.models import Batch, ActualDailyAssignmentState
from decimal import Decimal

# Find an active batch with recent daily states showing weight progression
batch = Batch.objects.filter(status='ACTIVE').first()
latest_state = ActualDailyAssignmentState.objects.filter(batch=batch).order_by('-date').first()

if latest_state:
    current_weight = float(latest_state.avg_weight_g)
    print(f'Batch {batch.batch_number}: current weight = {current_weight}g')
    
    # Set threshold just below current weight to trigger
    test_threshold = Decimal(str(current_weight - 5))
    
    # Create or update test template
    template, created = ActivityTemplate.objects.update_or_create(
        name='TEST: Weight Trigger',
        defaults={
            'activity_type': 'SAMPLING',
            'trigger_type': 'WEIGHT_THRESHOLD',
            'weight_threshold_g': test_threshold,
            'description': f'Test template - triggers at {test_threshold}g',
            'is_active': True,
        }
    )
    print(f'Template: {template.name} (threshold: {test_threshold}g)')
    print(f'Run growth analysis to trigger: python scripts/data_generation/run_growth_analysis_optimized.py --batch-id {batch.id}')
"
```

**Verify**:
```bash
# After running growth analysis for the batch
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.planning.models import PlannedActivity

# Check for auto-generated activity
recent = PlannedActivity.objects.filter(
    notes__contains='[TemplateID:'
).order_by('-created_at')[:5]

for act in recent:
    print(f'{act.id}: {act.activity_type} - {act.notes[:60]}...')
"
```

---

### Test 5: FCR Calculation

**Goal**: Verify FCR is calculated in daily states.

```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import ActualDailyAssignmentState

# Find states with FCR calculated
with_fcr = ActualDailyAssignmentState.objects.exclude(observed_fcr__isnull=True)[:10]

print('States with FCR calculated:')
for state in with_fcr:
    print(f'  {state.batch.batch_number} Day {state.day_number}: FCR={state.observed_fcr}, Feed={state.feed_kg}kg')

# Summary
total = ActualDailyAssignmentState.objects.count()
fcr_count = ActualDailyAssignmentState.objects.exclude(observed_fcr__isnull=True).count()
print(f'\nTotal: {total:,} states, {fcr_count:,} with FCR ({100*fcr_count/total:.1f}%)')
"
```

---

## Frontend Testing

### Start Development Servers

```bash
# Terminal 1: Backend
cd /Users/aquarian247/Projects/AquaMind
python manage.py runserver 8000

# Terminal 2: Frontend
cd /Users/aquarian247/Projects/AquaMind-Frontend
npm run dev
```

### Test Scenarios

1. **Production Planner Timeline**
   - Navigate to Production Planner
   - Verify activities show on timeline
   - Hover over pending activities → verify projection preview tooltip
   - Click "Mark Complete" → verify status updates

2. **Variance Report Page**
   - Navigate to Variance Reports
   - Verify FCR metrics card shows data
   - Check color coding (green/amber/red based on FCR thresholds)
   - Click on completed activities → verify variance data

3. **Batch Growth Analysis**
   - Navigate to a batch's Growth Analysis tab
   - Verify "Actual" line shows data
   - Verify "Projected" line from scenario

---

## Verification Queries

### Data Health Check
```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch, ActualDailyAssignmentState
from apps.planning.models import PlannedActivity, ActivityTemplate
from datetime import date

print('=' * 60)
print('PHASE 8/8.5 DATA HEALTH CHECK')
print('=' * 60)

# 1. Batches with scenarios
batches_total = Batch.objects.count()
batches_with_scenarios = Batch.objects.filter(scenarios__isnull=False).distinct().count()
print(f'\n1. Scenarios: {batches_with_scenarios}/{batches_total} batches have scenarios')

# 2. Daily states coverage
states_total = ActualDailyAssignmentState.objects.count()
latest = ActualDailyAssignmentState.objects.order_by('-date').first()
staleness = (date.today() - latest.date).days if latest else 'N/A'
print(f'2. Daily States: {states_total:,} records (staleness: {staleness} days)')

# 3. Planned activities
pa_total = PlannedActivity.objects.count()
pa_completed = PlannedActivity.objects.filter(status='COMPLETED').count()
pa_pending = PlannedActivity.objects.filter(status='PENDING').count()
print(f'3. PlannedActivities: {pa_total} total ({pa_completed} completed, {pa_pending} pending)')

# 4. Activity templates
templates = ActivityTemplate.objects.filter(is_active=True).count()
weight_templates = ActivityTemplate.objects.filter(is_active=True, trigger_type='WEIGHT_THRESHOLD').count()
stage_templates = ActivityTemplate.objects.filter(is_active=True, trigger_type='STAGE_TRANSITION').count()
print(f'4. Templates: {templates} active ({weight_templates} weight, {stage_templates} stage)')

# 5. FCR coverage
fcr_count = ActualDailyAssignmentState.objects.exclude(observed_fcr__isnull=True).count()
fcr_pct = 100 * fcr_count / states_total if states_total else 0
print(f'5. FCR Coverage: {fcr_count:,} states ({fcr_pct:.1f}%)')

# 6. Auto-triggered activities (Phase 8 trigger system)
auto_triggered = PlannedActivity.objects.filter(notes__contains='[TemplateID:').count()
print(f'6. Auto-triggered Activities: {auto_triggered}')

print('\n' + '=' * 60)
overall = 'READY' if (batches_with_scenarios > 100 and states_total > 500000 and pa_total > 500) else 'NEEDS DATA'
print(f'Overall Status: {overall} for testing')
print('=' * 60)
"
```

---

## Common Issues

### Issue: "No scenario available for batch"
**Cause**: Batch doesn't have a linked scenario.
**Fix**: Run `seed_planned_activities.py` which creates scenarios via templates.

### Issue: Daily states are stale
**Cause**: Growth analysis hasn't been run recently.
**Fix**: Run `run_growth_analysis_optimized.py --workers 4`

### Issue: No weight/stage triggers firing
**Cause**: No ActivityTemplates with WEIGHT_THRESHOLD or STAGE_TRANSITION.
**Fix**: Run `01_initialize_activity_templates.py` to seed templates.

### Issue: Variance API returns empty data
**Cause**: No ActualDailyAssignmentState for the completion date.
**Fix**: Ensure daily states cover the activity completion date.

---

## Key Insight: Testing the Feedback Loop

The hardest part to test is the *feedback loop*:
1. Actuals trigger new plans (weight threshold → activity)
2. Plans execute and anchor new actuals (completion → recompute)

**Realistic Testing Strategy**:

```
[Test Data Generation] → [Mature Batches + History]
         ↓
[Run Growth Analysis] → [Fresh Daily States]
         ↓
[Create/Check Templates] → [Trigger Rules Ready]
         ↓
[Manually Complete Activity] → [Observe Signal → Recompute]
         ↓
[Check for Auto-Generated Activities] → [Verify Triggers Fired]
         ↓
[Check Variance API] → [Verify Data Joins Work]
```

The test data generation system solves the "months to mature" problem by creating historical batches with full lifecycle. You then test the Phase 8/8.5 logic by:
1. Running growth analysis to update states
2. Manually triggering completions
3. Verifying the signals and triggers fire correctly

---

**End of Testing Guide**

