# UAT Testing Session Handoff - January 14, 2026

## Session Summary

This session focused on validating AquaMind's core features using UAT-optimized test data. We discovered and fixed several issues, including **real bugs**, **test data gaps**, and **behaviors that appeared to be bugs but were actually correct**.

---

## Key Accomplishments

### 1. Frontend Bug Fixes (Committed & Pushed)

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Hall utilization showing ~3000% | Frontend dividing population by arbitrary formula instead of biomass/capacity | Backend now returns `utilization_percent`; frontend consumes it directly |
| Container capacity ~4854% | Using `volume_m3` (10) as capacity instead of `max_biomass_kg` (35,000) | Fixed `hall-detail.tsx` to use `max_biomass_kg` for capacity |
| Container density wrong | Calculated as `biomass/capacity*100` instead of `biomass/volume` | Fixed to correctly calculate kg/m³ |
| Lifecycle stages filter empty | `getLifecycleStages()` returned empty array placeholder | Now calls `ApiService.apiV1BatchLifecycleStagesList()` |

**Frontend commits**: `ae1cec4`, `7e01e9e`, `a78dfaf`, `e2fda41`

### 2. Test Data Generation Fixes (Committed & Pushed)

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| No Live Forward Projections | Missing step in test data generation | Added `run_live_projections.py` script; documented as Step 8 |
| Scenario pinning missing | `pinned_projection_run` not set on batches | Script now auto-pins scenarios |
| Planned Activities not visible | Activities scattered across 136 batch-specific scenarios | Created shared "UAT Operations Plan" scenario |
| FAR-UAT-780 "0 containers" | Scenario `duration_days=760` but batch at day 782 (expired) | Changed to 900 days; fixed existing UAT data |

**Backend commits**: `6bdcc33`, `714f2c7`, `089d8a2`, `f48645d`

### 3. Documentation Updates

- `test_data_generation_guide_v6.md`: Added Step 8 for Live Forward Projections
- `run_live_projections.py`: New script for manual projection computation
- `UAT_QUICK_TEST_PLAN.md`: Test plan with specific batch IDs for testing

---

## Current Test Progress

### Test Case 1: Batch List & Details View ✅ PASSED
- Batch list loads correctly
- **Lifecycle stages filter now works** (fixed this session)
- Batch details show correct data

### Test Case 2: Executive Dashboard 🔄 IN PROGRESS
**Last verified state:**
- Capacity Utilization: 16.6% (correct)
- Active Batches: 26 batches (correct)
- Total Biomass: 42,054,799.8 kg (correct)

**Harvest Forecast section:**
| Batch | Status | Expected Display |
|-------|--------|-----------------|
| FAR-UAT-780 | PLANNED | Batch-level (10 containers), ~5.1 kg, due 2026-02-01 |
| FAR-UAT-720 | PLANNED | Batch-level (10 containers), ~3.75 kg, due 2026-04-02 |
| FAR-UAT-650 | NEEDS_PLAN | 2 containers (Ring-02, Ring-07) with NULL harvest dates |

⚠️ **FAR-UAT-650 "Needs Plan" is CORRECT behavior** - see explanation below.

---

## Critical Context for Next Agent

### Understanding "Needs Plan" Behavior

The Harvest Forecast uses a **tiered system**:

1. **PLANNED**: PlannedActivity exists with `due_date` within 90-day horizon
2. **PROJECTED**: Live projection exists, no plan within horizon
3. **NEEDS_PLANNING**: `needs_planning_attention=True` AND no plan within horizon

**FAR-UAT-650 case study:**
- Has a batch-level HARVEST plan for **June 11, 2026** (5+ months away)
- This is **beyond** the 90-day horizon (April 14, 2026)
- Ring-02 and Ring-07 have `projected_harvest_date = NULL` because they grow slightly slower and don't reach the 5kg harvest threshold
- The system correctly shows these as "Needs Plan" because:
  - They have `needs_planning_attention=True`
  - No harvest plan exists within 90 days
  - NULL harvest dates are included in the query

**This is NOT a bug** - it's the system correctly alerting that containers need attention sooner than the planned date.

### Scenario Duration Lesson Learned

The test data generator creates scenarios with `duration_days`. If a batch exceeds this duration:
- `LiveProjectionEngine` returns `"At or past scenario end"`
- No `ContainerForecastSummary` created
- Dashboard shows "0 containers"

**We fixed this** by changing 760 → 900 days, but be aware that batches at day 860+ could still hit this edge case.

### Test Data State

The current UAT database has:
- **51 active batches** (strategically positioned across lifecycle stages)
- **85 completed batches** (historical baseline)
- **~235K+ LiveForwardProjection records**
- **~510 ContainerForecastSummary records** (10 per active sea batch)
- **1,020 PlannedActivity records** (in shared "UAT Operations Plan" scenario)

---

## Remaining Test Cases

From `UAT_QUICK_TEST_PLAN.md`:

| # | Test Case | Status |
|---|-----------|--------|
| 1 | Batch List & Details View | ✅ Done |
| 2 | Executive Dashboard | 🔄 In Progress |
| 3 | Live Forward Projection | ⬜ Not Started |
| 4 | Growth Analysis | ⬜ Not Started |
| 5 | Stage Transition (FW Internal) | ⬜ Not Started |
| 6 | FW→Sea Transfer (Critical) | ⬜ Not Started |
| 7 | Harvest-Ready Batch | ⬜ Not Started |
| 8 | Planned Activities | ⬜ Not Started |
| 9 | Environmental Monitoring | ⬜ Not Started |
| 10 | Multi-Company Isolation | ⬜ Not Started |

---

## Key Files for Reference - MUST READS!!

| File | Purpose |
|------|---------|
| `docs/progress/uat_test_data/UAT_QUICK_TEST_PLAN.md` | Test plan with specific batch IDs |
| `docs/database/test_data_generation/test_data_generation_guide_v6.md` | Test data generation guide |
| `docs/user_guides/live_forward_projection_guide.md` | Live projection feature docs |
| `scripts/data_generation/run_live_projections.py` | Manual projection script |
| `apps/batch/api/viewsets/forecast_viewset.py` | Tiered harvest forecast API |

---

## Debugging Tips

### Check if a batch has valid projections:
```python
from apps.batch.models import Batch, ContainerForecastSummary
batch = Batch.objects.get(batch_number='FAR-UAT-XXX')
print(f"Pinned run: {batch.pinned_projection_run}")
summaries = ContainerForecastSummary.objects.filter(assignment__batch=batch, assignment__is_active=True)
print(f"Summaries: {summaries.count()}")
```

### Check scenario duration vs batch age:
```python
from datetime import date, timedelta
scenario = batch.pinned_projection_run.scenario
scenario_end = scenario.start_date + timedelta(days=scenario.duration_days)
days_remaining = (scenario_end - date.today()).days
print(f"Days remaining in scenario: {days_remaining}")
```

### Manually run live projections for a batch:
```python
from apps.batch.services.live_projection_engine import LiveProjectionEngine
for assignment in batch.batch_assignments.filter(is_active=True):
    engine = LiveProjectionEngine(assignment)
    result = engine.compute_and_store()
    print(f"{assignment.container.name}: {result}")
```

---

## Important Reminders

1. **Not every anomaly is a bug** - The "Needs Plan" display for FAR-UAT-650 is correct behavior
2. **Test data issues ≠ code bugs** - Check data state before assuming code is wrong
3. **Scenario duration matters** - Batches can outlive their scenarios, causing projection failures
4. **Horizon filters** - The 90-day horizon filters out data that exists but is beyond the window
5. **Geography matters** - Faroe Islands = ID 1, Scotland = ID 2

---

## Session Statistics

- **Duration**: ~2 hours
- **Commits**: 8 (5 backend, 3 frontend)
- **Bugs fixed**: 5 (4 frontend, 1 backend)
- **Test data issues resolved**: 3
- **"Non-bugs" investigated**: 1 (FAR-UAT-650 Needs Plan)

---

*Last updated: January 14, 2026*
*Next session: Continue from Test Case 2 → Test Case 3 (Live Forward Projection)*
