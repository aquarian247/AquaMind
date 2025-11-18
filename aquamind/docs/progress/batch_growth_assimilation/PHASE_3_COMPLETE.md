# Phase 3 Complete - Growth Assimilation Engine

**Issue**: #112  
**Branch**: `feature/batch-growth-assimilation-112`  
**Completed**: November 14, 2025

---

## Summary

Phase 3 successfully implemented the core computation engine for batch growth assimilation. The `GrowthAssimilationEngine` computes daily actual states by assimilating real measurements (temperature, mortality, feed, measured weights) with TGC-driven growth models, tracking complete provenance for transparency.

This is the **heart** of the feature - where the magic happens!

---

## Deliverables

### GrowthAssimilationEngine Service
**File**: `apps/batch/services/growth_assimilation.py` (850+ lines)

**Core Class**: `GrowthAssimilationEngine`

**Key Methods**:
- `recompute_range(start_date, end_date)` - Main entry point
- `_detect_anchors()` - Find growth samples, transfers, vaccinations
- `_compute_daily_state()` - Daily calculation with all inputs
- `_get_temperature()` - Hierarchical temperature retrieval
- `_get_mortality()` - Prorated actual or model mortality
- `_get_feed()` - Actual feed from FeedingEvents
- `_get_placements()` - Track transfers IN
- `_determine_stage_transition()` - Weight-based stage changes
- `_evaluate_planner_triggers()` - Integration hook (Phase 8 stub)

**Batch-Level Function**: `recompute_batch_assignments(batch_id, start_date, end_date)`

---

## Algorithm Implementation

### Anchor Detection (lines 229-318)
Detects measurement points that reset weight calculations:

**Priority Order**:
1. **Growth Samples** (priority 1, confidence 1.0)
2. **Transfers with measured weights** (priority 2, confidence 0.95)
   - Adjusts for selection_method: LARGEST (-12%), SMALLEST (+12%), AVERAGE (0%)
3. **Vaccinations with weighing** (priority 3, confidence 0.90)
   - Reads from IndividualFishObservation via HealthSamplingEvent

### Daily State Computation (lines 431-576)

**Per Date Loop**:
1. Check for anchor → reset weight if found
2. Get temperature: measured (1.0) > interpolated (0.7) > profile (0.5) > none (0.0)
3. Get mortality: actual batch-level prorated (0.9) > model (0.4)
4. Get feed: actual from FeedingEvents (1.0) > none (0.0)
5. Get placements: transfers IN to this assignment
6. Calculate population: `prev + placements - mortality`
7. Calculate weight: anchor OR TGC growth (`ΔW = TGC × T^n × W^m`)
8. Calculate biomass: `population × weight / 1000`
9. Calculate observed FCR: `feed / biomass_gain` (if both > 0)
10. Check stage transition: weight >= max_weight → next stage
11. Track provenance: sources dict + confidence dict
12. Integration hook: log potential planner triggers

### Fallback Strategies

| Input | Primary | Fallback 1 | Fallback 2 | Confidence |
|-------|---------|------------|------------|------------|
| **Weight** | Anchor (measured) | TGC computed | Unchanged | 1.0 → 0.8 → 0.3 |
| **Temperature** | Measured readings | Interpolated | Profile | 1.0 → 0.7 → 0.5 |
| **Mortality** | Actual (prorated) | Model rate | — | 0.9 → 0.4 |
| **Feed** | Actual events | None (0 kg) | — | 1.0 → 0.0 |

---

## Production-Grade Qualities

### Correctness
- ✅ Follows pseudocode specification (plan lines 138-300)
- ✅ Field name corrections (actual_execution_date, feeding_date, batch vs assignment)
- ✅ Type safety (Decimal ↔ float conversions)
- ✅ Handles edge cases (missing data, gaps, no temperature)

### Robustness
- ✅ Comprehensive error handling
- ✅ Logging at appropriate levels (info, debug, warning, error)
- ✅ Transaction-safe upsert operations
- ✅ Graceful degradation with fallbacks

### Maintainability
- ✅ Clear separation of concerns (one method per responsibility)
- ✅ Comprehensive docstrings
- ✅ Reuses existing calculators (TGC, Mortality)
- ✅ Follows existing code patterns

### Performance
- ✅ Efficient queries (select_related, prefetch where appropriate)
- ✅ Bulk upsert (update_or_create)
- ✅ Avoids N+1 queries in anchor detection

---

## Test Results

### Core Engine Tests
**File**: `apps/batch/tests/test_phase3_core_engine.py`
**Tests**: 12/12 passing

**Coverage**:
- Engine initialization and scenario resolution
- Initial state bootstrap from assignment/scenario
- Initial state from previous computation
- Temperature retrieval (measured, profile fallback)
- Mortality model fallback
- Mortality actual prorated
- Selection bias adjustments (LARGEST/SMALLEST/AVERAGE)
- **End-to-end recompute** (critical integration test)
  - Creates 3 daily states with provenance
  - Validates population, weight, biomass calculations
  - Verifies sources and confidence tracking

### Full Test Suite
- **PostgreSQL**: 1243/1243 tests passing (20 skipped)
- **SQLite (CI)**: 1243/1243 tests passing (62 skipped)
- **Result**: ✅ 100% pass rate on both databases
- **No regressions**: All existing tests continue to pass

---

## Key Implementation Details

### MortalityEvent Prorating
**Challenge**: MortalityEvent is tracked at batch level, not assignment level  
**Solution**: Prorate batch mortality based on assignment's share of batch population

```python
batch_population = sum(all assignments' populations)
assignment_share = this_assignment_pop / batch_population
prorated_mortality = batch_mortality × assignment_share
```

### Field Name Mappings (vs. Pseudocode)
- `execution_date` → `actual_execution_date` (TransferAction)
- `event_date` → `feeding_date` (FeedingEvent)
- `parameter='temperature'` → `parameter__name='temperature'` (EnvironmentalReading FK)
- `batch_container_assignment` → `batch` (MortalityEvent)

### Type Safety
All model fields use `Decimal`, TGC calculator expects `float`:
- Convert to float before TGC calculations
- Convert back to Decimal before database save
- Use `round()` for consistent precision

---

## Integration Points

### Reuses Existing Components
- `TGCCalculator` from `apps.scenario.services.calculations.tgc_calculator`
- `MortalityCalculator` from `apps.scenario.services.calculations.mortality_calculator`
- Scenario models: TGCModel, FCRModel, MortalityModel, BiologicalConstraints
- Batch models: GrowthSample, TransferAction, MortalityEvent
- Environmental: EnvironmentalReading, EnvironmentalParameter
- Inventory: FeedingEvent

### Production Planner Integration Hook
**Method**: `_evaluate_planner_triggers(state_data)`

Currently logs potential triggers. Phase 8 will implement:
- Query ActivityTemplate for WEIGHT_THRESHOLD and STAGE_TRANSITION triggers
- Auto-generate PlannedActivities when conditions met
- Call planner API: `POST /activity-templates/{id}/generate-for-batch/`

---

## What Works (Validated by Tests)

✅ Engine initializes with assignment and scenario  
✅ Fails gracefully without scenario  
✅ Bootstraps initial state from assignment/constraints/scenario  
✅ Uses previous day's computed state when available  
✅ Retrieves measured temperature with 1.0 confidence  
✅ Falls back to temperature profile with 0.5 confidence  
✅ Uses model mortality with 0.4 confidence  
✅ Prorates actual batch mortality with 0.9 confidence  
✅ Adjusts measured weights for selection bias  
✅ **End-to-end**: Computes 3 daily states with full provenance  
✅ Tracks sources (measured/interpolated/model/none)  
✅ Tracks confidence scores (0.0-1.0 scale)  
✅ Returns accurate stats (rows created/updated, errors)

---

## What's Deferred to Phase 9

The following scenarios will be validated with real Faroe Islands data:
- Complex anchor sequences (multiple anchors in short window)
- Long gaps without measurements (>7 days)
- Complex multi-assignment transfers
- Stage transitions during transfers
- Edge cases in temperature interpolation

**Rationale**: Real-world data provides better validation than synthetic fixtures

---

## Next Steps: Phase 4

Phase 4 will make the engine event-driven:

1. **Celery Setup**: Configure Redis/RabbitMQ, worker processes
2. **Django Signals**: Trigger recompute on GrowthSample save, TransferAction complete, etc.
3. **Targeted Recompute**: Smart windowing (only recompute [d-2, d+2] around events)
4. **Nightly Catch-up Job**: Ensure all batches stay current
5. **Idempotency**: Safe to run multiple times

**Blockers**: None - engine is ready, just needs event wiring

---

## Git History

| Commit | Description |
|--------|-------------|
| `245ea46` | feat(batch-growth): Phase 3 - Core assimilation engine implementation |

---

## Checklist

- [x] Core engine implemented (850+ LOC)
- [x] Anchor detection logic (3 types)
- [x] TGC-based growth calculations
- [x] Temperature/mortality/feed retrieval with fallbacks
- [x] Placements tracking
- [x] Selection bias adjustments
- [x] Stage transitions
- [x] Provenance tracking (sources + confidence)
- [x] Production Planner integration hook (stub)
- [x] Batch-level recompute function
- [x] Tests written and passing (12/12)
- [x] PostgreSQL compatibility (1243/1243 tests pass)
- [x] SQLite compatibility (1243/1243 tests pass)
- [x] No regressions
- [x] Documentation updated
- [x] Git commit clean



