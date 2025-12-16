# AquaMind Operational Core Integration Guide

**Version**: 2.1  
**Last Updated**: December 16, 2025  
**Owner**: Engineering  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/user_guides/`  

---

## Overview

This guide documents the interplay between AquaMind's four core operational features: **Production Planner** (scenario-based planning), **Batch Growth Assimilation** (daily "actuals" computation), **Transfer Workflows** (multi-step execution), and **Live Forward Projection** (operational forecasting). These form a symbiotic "plan → execute → track → learn → forecast" feedback loop, enabling proactive management of 50-60+ concurrent batches while grounding decisions in real data.

The design separates concerns for flexibility—plans for what-ifs, workflows for high-risk executions (e.g., transfers), assimilation for truth-telling actuals, and live projections for data-driven forecasts—without redundancy. This aligns with Bakkafrost's multi-subsidiary ops (e.g., Freshwater → Farming handoffs) and regulatory needs (audit trails via `django-simple-history`). 

For superusers: Think of it as a feedback engine. Plans sketch the future; workflows make it happen; assimilation measures reality and auto-adjusts; live projections answer "given where we are today, when will we really be ready?" No manual reconciliation—signals and Celery tasks keep it live.

**Key Benefits**:
- **Agility**: What-if scenarios without workflow overhead.
- **Accuracy**: Daily states anchor sparse samples (e.g., 10-15 growth measurements over 900 days).
- **Compliance**: Full audit from plan spawn to actual completion.
- **Scalability**: Handles 10k+ records via hypertables and targeted recomputes.

---

## The Three Pillars: Why Separation Matters

These aren't isolated silos—they're layered for a "plan → track → execute → learn" loop, tailored to aquaculture's unpredictability (e.g., weather spikes, disease curves).

| Component | Purpose | Key Models/Tables | Data Flow Role |
|-----------|---------|-------------------|---------------|
| **Production Planner** | High-level, scenario-driven scheduling for what-if ops across 50-60 batches. | `planning_plannedactivity` (activity_type, due_date, status); `planning_activitytemplate` (triggers: DAY_OFFSET, WEIGHT_THRESHOLD, STAGE_TRANSITION). | Generates activities/templates; variance reports on planned vs. actual; spawns workflows. |
| **Batch Growth Assimilation** | Daily "reality check" via TGC-modeled growth, anchoring sparse samples to compute weights/pop/biomass. | `batch_actualdailyassignmentstate` (hypertable: avg_weight_g, population, fcr, provenance JSONB); recompute engine (Celery tasks). | Anchors from workflows/plans; evaluates triggers for new activities; feeds variance with ground-truth data. |
| **Transfer Workflows** | Granular, multi-step execution for complex moves (e.g., multi-day sea transfers with mortality tracking). | `batch_batchtransferworkflow` + `TransferAction` (steps: prep, move, post-check); auto-finance txns. | Executes TRANSFER plans; updates core tables (`batch_batchcontainerassignment` for stage/pop changes); syncs completion back to plans. |

**Why Not Combine Them?** The separation is strategic, not redundant:

| Aspect | Separation (Current Design) | Monolithic Alternative | Why Separation Wins |
|--------|----------------------------|------------------------|---------------------|
| **Flexibility** | Plans for quick what-ifs; workflows only for complex transfers. | One "super-activity" forces workflow steps on everything. | PRD 3.2: Scenario-based planning separate from execution. |
| **User Experience** | Planner's timeline for managers; workflows' steps for field ops. | Overwhelms casual users with unnecessary complexity. | Different personas need different views. |
| **Performance** | Light plans (list views) vs. heavy workflows (multi-action); targeted recomputes. | Bloated queries joining everything for simple checks. | Scales to 10k+ batches (PRD 4.1). |
| **Maintainability** | Discrete apps with isolated concerns; signals/Celery decouple logic. | Ripple effects from shared models; bigger test surface. | Solo-friendly: Fix variance without workflow regressions. |

They share primitives (status lifecycles: PENDING → COMPLETED; audit via simple-history) without merge bloat.

---

## The Fourth Pillar: Live Forward Projection

While the three pillars above handle **past** (assimilation), **present** (workflows), and **planned future** (planner), they don't answer a critical operational question: *"Given where we actually are today, when will this batch really be ready?"*

**Live Forward Projection** bridges this gap by projecting forward from the latest `ActualDailyAssignmentState` using TGC growth models and temperature-corrected profiles. This creates data-driven harvest and transfer forecasts that update nightly, reflecting reality rather than stale scenario assumptions.

| Component | Purpose | Key Models/Tables | Data Flow Role |
|-----------|---------|-------------------|---------------|
| **Live Forward Projection** | Nightly recompute of "when will we reach harvest/transfer weight?" based on current actuals | `batch_liveforwardprojection` (hypertable); `batch_containerforecastsummary` (dashboard cache). | Starts from latest actual state; applies temp bias + TGC; outputs daily projections; feeds Executive Dashboard with tiered forecasts. |

### The Three-Tier Forecast Architecture

Live Forward Projection enables executive decision-making via tiered urgency classification:

| Tier | Name | Condition | Action |
|------|------|-----------|--------|
| **1** | PLANNED | `PlannedActivity` (HARVEST/TRANSFER) exists | Execute as scheduled |
| **2** | PROJECTED | Live Forward predicts threshold crossing, no plan yet | Create plan when appropriate |
| **3** | NEEDS_ATTENTION | Within 30 days of threshold, still no plan | **Urgent**: Create plan now |

This ensures executives focus on exceptions rather than reviewing every batch.

### Key Innovation: Temperature Bias

Scenario projections assume idealized temperatures from `TemperatureProfile`. Reality diverges. Live Forward computes a **temperature bias** from recent sensor data:

```
bias = mean(actual_temp - profile_temp) over last 14 days
```

This bias is applied to all future temperature predictions, making projections more accurate as operational data accumulates.

📚 **Full Documentation**: See [Live Forward Projection Guide](./live_forward_projection_guide.md) for complete details on computation, API endpoints, TimescaleDB configuration, and troubleshooting.

---

## Data Flow and Interplay

Phase 8/8.5 implementation (December 2025) closed the loop with bidirectional signals—actuals trigger plans; completed plans/workflows anchor actuals. This creates a true feedback engine.

### The Symbiotic Loop

```
[Planner: Scenarios + Templates] ──spawns──> [Workflows: Multi-Step Exec] ──mutates──> [Core: Batch/Health/Env/Inventory]
     ↑                                                                 ↓
     │                                                       recompute (Celery + Signals)
     │                                                                 │
[Assimilation: Daily Actuals + Anchors] <──anchors── [Core: e.g., weights from actions, mortalities]
     │                                                                 │
     ├──────────triggers/eval──────────────┘ (WEIGHT/STAGE hooks; variance joins; FCR tracking)
     │
     ▼
[Live Forward Projection] ──projects──> [Executive Dashboard: Tiered Forecasts]
     │                                           │
     └───────────────────────────────────────────┘ (NEEDS_ATTENTION tier → prompts PlannedActivity creation)
```

### Forward Flow (Plan → Execute → Track)

1. **Planner** generates activities via templates (e.g., WEIGHT_THRESHOLD at 100g → TRANSFER plan in "Aggressive Scenario").
2. **Workflows** spawn from TRANSFER plans (one-to-one link via `planned_activity` FK), executing steps that mutate core tables (e.g., update `lifecycle_stage` on `batch_batch`, log mortalities to `health_mortalityrecord`).
3. **Assimilation** recomputes daily states post-execution (signal on COMPLETED triggers Celery task), using anchors (e.g., measured weights from workflow actions) to refine TGC models. Outputs accurate biomass for next plans.

### Feedback Loop (Track → Learn → Adjust)

1. **Assimilation** feeds actuals back:
   - **Trigger Evaluation** (Phase 8.1): Daily recompute evaluates ActivityTemplates—if `avg_weight_g > WEIGHT_THRESHOLD`, auto-generates PlannedActivity. Same for `STAGE_TRANSITION` triggers.
   - **Deduplication**: Uses `[TemplateID:X]` markers in notes to prevent duplicate activities per batch/template.
   - **FCR Calculation** (Phase 8.5): Computes feed conversion ratio from `FeedingEvent` totals vs. weight gain; stores in `ActualDailyAssignmentState.fcr` for variance analysis.

2. **Planner** analyzes via reports:
   - **Variance Reports**: Compare planned due dates to actual completion; join with `ActualDailyAssignmentState` for weight/FCR at completion.
   - **Projection Previews**: Tooltip shows scenario-based rationale (projected weight, population, day number) for activity due dates.

3. **Workflows** get smarter: Completed workflows sync status to plans via `post_save` signal, feeding audit trails for compliance.

### Detailed Signal Flow (Phase 8 Implementation)

| Signal Source | Trigger Condition | Action | Target |
|---------------|------------------|--------|--------|
| `GrowthSample` post_save | Sample created/updated | Enqueue batch recompute | Assimilation engine |
| `TransferAction` post_save | Transfer completed with weights | High-priority anchor creation | `ActualDailyAssignmentState` |
| `MortalityEvent` post_save | Mortality recorded | Population adjustment + recompute | Assimilation engine |
| `PlannedActivity` post_save | Status changed to COMPLETED | Enqueue batch recompute for TRANSFER/VACCINATION/SAMPLING | Assimilation engine |
| Assimilation daily compute | Weight > threshold OR stage transition | Auto-generate PlannedActivity | Production Planner |

### Edge Cases Handled

- **Overdue Plans**: Red badges in UI; assimilation flags low-confidence weights as potential reschedule candidates.
- **Multi-Scenario**: Activities isolated per scenario; assimilation uses batch's "pinned" projection run or first available scenario for trigger evaluation.
- **Ghost Plans Prevention** (Edge Guard): `get_baseline_scenario()` ensures PlannedActivities always have a scenario—raises `ValueError` if none available, prompting user to create scenario first.
- **Null Safety**: FCR returns `None` with `'sources': 'insufficient_data'` when no feeding events; numeric comparisons use explicit `is not None` checks.
- **Broodstock Integration** (Optional): If `BreedingTraitPriority` exists for batch's parentage with `disease_resistance_weight < 0.5`, can trigger TREATMENT activities. Implemented as optional hook—broodstock module may not be active at go-live.

---

## API Endpoints (Phase 8/8.5)

### Variance Analysis

**GET** `/api/v1/planning/planned-activities/{id}/variance-from-actual/`

Returns planned vs. actual comparison for a completed activity:
```json
{
  "activity_id": 123,
  "planned_date": "2025-03-15",
  "actual_date": "2025-03-17",
  "variance_days": 2,
  "actual_weight_g": 105.3,
  "actual_population": 48500,
  "actual_fcr": 1.15,
  "projected_weight_g": 100.0
}
```

### Projection Preview

**GET** `/api/v1/planning/planned-activities/{id}/projection-preview/`

Returns scenario-based rationale for activity due date (used by hover tooltips):
```json
{
  "activity_id": 456,
  "due_date": "2025-04-20",
  "scenario_id": 12,
  "scenario_name": "Optimal Growth",
  "projected_weight_g": 150.5,
  "projected_population": 47000,
  "projected_biomass_kg": 7073.5,
  "day_number": 180,
  "rationale": "Projected from scenario model at day 180"
}
```

---

## FCR Tracking (Phase 8.5)

Feed Conversion Ratio is calculated during daily state computation:

```python
# In _compute_daily_state()
if weight_gain_g > 0 and cumulative_feed_kg > 0:
    fcr = cumulative_feed_kg / (weight_gain_kg)
else:
    fcr = None  # Insufficient data
```

**Thresholds** (displayed in UI with color coding):
- **Excellent**: FCR ≤ 1.2 (emerald)
- **Acceptable**: 1.2 < FCR ≤ 1.5 (amber)
- **Needs Attention**: FCR > 1.5 (rose)

FCR metrics appear in:
1. **VarianceReportPage**: FCR status card with color-coded indicator
2. **Variance API**: `actual_fcr` field in variance-from-actual response
3. **Daily States**: Stored in `ActualDailyAssignmentState.fcr` (NUMERIC 8,3)

---

## Architecture Sanity Check

From `data_model.md` inspection (December 2025):

- **Integrity**: No orphans—FKs cascade cleanly (e.g., delete scenario → drop activities). Indexes on timestamps/FKs support queries.
- **Hypertables**: `environmental_environmentalreading` and `batch_actualdailyassignmentstate` scale time-series; 7-day compression policy caps growth.
- **Audit Coverage**: Simple-history covers 10+ models per app—reg-ready. All changes logged with user attribution.
- **No Red Flags**: Planning endpoints align with flows; variance joins work via `planned_activity` FK on daily states.

**Phase 8/8.5 Additions**:
- `ActualDailyAssignmentState.planned_activity` FK links daily states to triggering activities
- `ANCHOR_TYPE_CHOICES` expanded with `'planned_activity'` option
- `PlannedActivity._original_status` tracking for signal deduplication (only fires on status *change* to COMPLETED)

---

## Best Practices for Users

### Planning
- Use templates for lifecycle spines (DAY_OFFSET for standard timing; WEIGHT_THRESHOLD/STAGE_TRANSITION for condition-based triggers)
- Fork scenarios for what-ifs (e.g., "High-Mortality Variant")
- Leverage projection previews to understand due date rationale

### Execution
- Link transfers early—workflows auto-anchor actuals for better variance
- Mark activities complete promptly to trigger recomputes
- Use spawn workflow for TRANSFER activities to get full step tracking

### Tracking
- Pin baseline scenario in batch views for consistent trigger evaluation
- Review weekly variance for patterns (e.g., late culls from feed gaps)
- Monitor FCR trends—rising ratios may indicate feed quality issues

### Troubleshooting
- **Overdue activities?** Check assimilation confidence (low temp data = suspect weights)
- **Missing projections?** Ensure batch has a scenario with TGC/FCR/Mortality models
- **Duplicate activities?** Verify template deduplication—check notes for `[TemplateID:X]` markers
- **FCR null?** Confirm feeding events exist for the date range

---

## Technical Reference

### Key Files (Phase 8/8.5)

**Backend**:
- `apps/batch/services/growth_assimilation.py`: `_evaluate_planner_triggers()`, `_compute_daily_state()` with FCR
- `apps/batch/signals.py`: `on_planned_activity_completed()`, deduplication helpers
- `apps/planning/api/viewsets/planned_activity_viewset.py`: `variance_from_actual()`, `projection_preview()` actions
- `apps/planning/api/serializers/planned_activity_serializer.py`: Edge Guard scenario validation
- `apps/batch/models/batch.py`: `get_baseline_scenario()` helper

**Frontend**:
- `client/src/features/production-planner/components/ProjectionPreviewTooltip.tsx`: Hover tooltip
- `client/src/features/production-planner/pages/VarianceReportPage.tsx`: FCR metrics card
- `client/src/features/production-planner/api/api.ts`: `useProjectionPreview()` hook with JWT auth

### Test Coverage

- `apps/batch/tests/test_phase8_planner_integration.py`: Trigger evaluation, signal firing, variance API
- `apps/batch/tests/test_phase85_polish.py`: Edge Guard, FCR calculation, projection preview
- `client/src/features/production-planner/__tests__/phase85_polish.test.tsx`: Tooltip rendering, FCR helpers

---

## References

- PRD Section 3.2: Operational Planning
- Data Model: `docs/database/data_model.md`
- Implementation Plan: `docs/progress/batch_growth_assimilation/batch-growth-assimilation-plan.md` (Phase 8/8.5)
- Executive Forecast Dashboard: `docs/progress/executive_forecast_dashboard/` (Phase 9 planning)
- **Live Forward Projection Guide**: `docs/user_guides/live_forward_projection_guide.md` (Phase 9 implementation)

---

**End of Document**
