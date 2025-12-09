# AquaMind Operational Core Integration Guide

**Version**: 1.0  
**Last Updated**: December 09, 2025  
**Owner**: Engineering (Solo Dev)  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/architecture/`  

---

## Overview

This guide documents the interplay between AquaMind's three core operational features: **Production Planner** (scenario-based planning), **Batch Growth Assimilation** (daily "actuals" computation), and **Transfer Workflows** (multi-step execution). These form a symbiotic "plan → execute → track → learn" loop, enabling proactive management of 50-60+ concurrent batches while grounding decisions in real data.

The design separates concerns for flexibility—plans for what-ifs, workflows for high-risk executions (e.g., transfers), and assimilation for truth-telling actuals—without redundancy. This aligns with Bakkafrost's multi-subsidiary ops (e.g., Freshwater → Farming handoffs) and regulatory needs (audit trails via `django-simple-history`). 

For superusers: Think of it as a feedback engine. Plans sketch the future; workflows make it happen; assimilation measures reality and auto-adjusts. No manual reconciliation—signals and Celery tasks keep it live.

**Key Benefits**:
- **Agility**: What-if scenarios without workflow overhead.
- **Accuracy**: Daily states anchor sparse samples (e.g., 10-15 growth measurements over 900 days).
- **Compliance**: Full audit from plan spawn to actual completion.
- **Scalability**: Handles 10k+ records via hypertables and targeted recomputes.

---

## Core Components Recap

| Component | Purpose | Key Models/Tables | Data Flow Role |
|-----------|---------|-------------------|---------------|
| **Production Planner** | Scenario-driven scheduling for ops (vaccinations, transfers, culls). | `planning_plannedactivity` (activity_type, due_date, status); `planning_activitytemplate` (triggers: DAY_OFFSET, WEIGHT_THRESHOLD). | Generates activities/templates; variance reports on planned vs. actual. |
| **Batch Growth Assimilation** | Computes daily weights/pop/biomass from anchors (samples, transfers) + TGC models. | `batch_actualdailyassignmentstate` (hypertable: avg_weight_g, population, provenance JSONB). | Anchors from workflows/plans; triggers new activities; feeds variance. |
| **Transfer Workflows** | Orchestrates multi-day moves with steps (prep, ship, check). | `batch_batchtransferworkflow` (linked to PlannedActivity); `batch_transferaction` (measured weights, mortalities). | Executes TRANSFER plans; updates core tables (e.g., stage changes). |

Shared: Status lifecycles (PENDING → COMPLETED); audit via `HistoricalRecords`; core ties to `batch_batch` and `batch_batchcontainerassignment`.

---

## Data Flow and Interplay

The system forms a closed loop: Plans project forward, workflows execute and mutate data, assimilation recomputes reality, feeding back to refine plans. Bidirectional signals (Phase 8 implementation) ensure sync—no loose ends.

### High-Level Flow
1. **Plan**: Template auto-gens activities (e.g., TRANSFER at 100g via WEIGHT_THRESHOLD).
2. **Execute**: Spawn workflow → steps update core tables (e.g., `lifecycle_stage` on `batch_batch`).
3. **Track**: Workflow complete → signal anchors assimilation (e.g., measured weights reset daily states).
4. **Learn**: Actuals trigger new plans (e.g., low biomass → CULL suggestion); variance flags delays.

**Text Diagram** (for quick ref):
```
[Planner: Scenarios/Templates] ──spawns──> [Workflows: Steps/Actions] ──mutates──> [Core: Batch/Health/Env/Inventory]
     ↑                                                                 ↓
     │                                                       recompute (Celery + Signals)
     │                                                                 │
[Assimilation: Daily Actuals/Anchors] <──anchors── [Core: e.g., weights from actions, mortalities]
     │                                                                 │
     └──────────triggers/eval──────────────┘ (e.g., threshold hits → new activity; variance joins)
```

### Detailed Interactions
- **Planner → Workflows**: TRANSFER activities spawn one-to-one workflows (`planned_activity` FK on `batch_batchtransferworkflow`). Completion auto-syncs status (post_save signal).
- **Workflows → Assimilation**: Actions log anchors (e.g., `measured_weight_g` on `batch_transferaction` → high-priority reset in `recompute_actual_daily_state`). Mortalities update `health_mortalityrecord` → population adjustments.
- **Assimilation → Planner**: Daily states eval templates (e.g., `avg_weight_g > threshold` → gen PlannedActivity). Provenance/confidence scores feed variance (e.g., late transfers due to "low confidence temp data").
- **Cross-Cutting**: All tie to `batch_batchcontainerassignment` for per-container accuracy (weighted aggregates). Geography/role filters (`users_userprofile`) enforce subsidiary access (e.g., Logistics sees workflows only).

**Edge Handling**:
- Overdue plans: Red badges; assimilation flags (e.g., weight drift → reschedule suggestion).
- Multi-scenario: Activities per scenario; assimilation uses "pinned" baseline for triggers.
- Audit: Simple-history logs all (e.g., `historicalplannedactivity` for changes).

---

## Architecture Sanity Check
From `data_model.md` (Dec 2025 inspection):
- **Integrity**: No orphans—FKs cascade cleanly (e.g., delete scenario → drop activities). Indexes on timestamps/FKs support queries (e.g., `idx_plannedactivity_scenario_due_date`).
- **No Red Flags**: Hypertables (`environmental_environmentalreading`) scale time-series; compression (7-day policy) caps growth. Audit covers 10+ models per app—reg-ready. Planning endpoints (e.g., `/variance-report/`) align with flows.
- **Gaps?**: Minor—add `fcr` precision (decimal(5,3)) to assimilation for PRD parity. Broodstock ties (e.g., `broodstock_batchparentage`) could hook to plans for genetic triggers (Phase 3).

Superusers: This modularity means you can tweak a scenario without breaking workflows—e.g., test "Aggressive Treatment" in planner, execute via workflow, see actuals adjust biomass.

---

## Best Practices for Users
- **Planning**: Use templates for lifecycle spines; fork scenarios for what-ifs (e.g., "High-Mortality Variant").
- **Execution**: Link transfers early—workflows auto-anchor actuals for better variance.
- **Tracking**: Pin baseline scenario in batch views; review weekly variance for patterns (e.g., late culls from feed gaps).
- **Troubleshooting**: Overdue? Check assimilation confidence (low temp data = suspect weights). Duplicates? Scenario isolation prevents.

---

## References
- PRD Section 3.2: Operational Planning.
- Data Model: `docs/database/data_model.md`.
- Implementation: `docs/progress/batch-growth-assimilation-plan.md` (Phase 8).

**End of Document**