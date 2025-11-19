# Batch Growth Assimilation - Handover Document

**Issue**: #112  
**Branch**: `feature/batch-growth-assimilation-112`  
**Date**: November 14, 2025  
**For**: Next Agent (Phases 4-9)

---

## 🎯 Mission

Implement daily "Actual" growth series by assimilating real measurements with TGC models. This is **the crux of AquaMind** - providing day-to-day insight into weight, population, and biomass for operational planning.

**Status**: Phases 1-3 complete (foundation built). Phases 4-9 remaining (event-driven, API, UI, validation).

---

## ✅ What's Complete & Working

### Phase 1: Schema Enhancements ✅
**Files**: 3 migrations, model updates  
**Status**: Applied, tested, working

**What it does**: Added fields to capture measured weights during operational events
- TransferAction: 6 measured weight fields + selection_method
- Treatment: includes_weighing flag + links to sampling events
- Batch: pinned_scenario field

**Key Files**:
- `apps/batch/migrations/0031_add_measured_fields_to_transferaction.py`
- `apps/batch/migrations/0032_add_pinned_scenario_to_batch.py`
- `apps/health/migrations/0027_add_weighing_links_to_treatment.py`

### Phase 2: Hypertable + CAGG ✅
**Files**: Model + 2 migrations + production scripts  
**Status**: Model working as regular PostgreSQL table, TimescaleDB configured in dev

**What it does**: Created ActualDailyAssignmentState model (18 fields) for time-series storage
- In dev: Works as regular PostgreSQL table
- In prod: TimescaleDB hypertable with compression (manual setup via scripts)
- Hypertable IS configured in dev database (you ran the script!)

**Key Files**:
- `apps/batch/models/actual_daily_state.py` (the model)
- `apps/batch/migrations/0033_create_actual_daily_state_model.py`
- `apps/batch/migrations/0034_setup_timescaledb_hypertable.py` (skips in CI)
- `scripts/timescaledb/setup_daily_state_hypertable.sql` (already run in dev!)

**Important**: Dev database HAS TimescaleDB configured for `batch_actualdailyassignmentstate`. Temperature CAGG is NOT configured (environmental tables aren't hypertables yet - deferred per follow-up note).

### Phase 3: Assimilation Engine ✅
**Files**: 850+ LOC service + 12 tests  
**Status**: FULLY FUNCTIONAL - the magic works!

**What it does**: Computes daily states by assimilating measurements with TGC models
- Anchor detection (samples, transfers, vaccinations)
- TGC growth between anchors: `ΔW = TGC × T^n × W^m`
- Fallback hierarchies for missing data
- Provenance tracking (sources + confidence 0.0-1.0)
- Selection bias adjustment (LARGEST/SMALLEST/AVERAGE)
- Stage transitions based on weight thresholds

**Key Files**:
- `apps/batch/services/growth_assimilation.py` (THE ENGINE)
- `apps/batch/tests/test_phase3_core_engine.py` (12 tests, all pass)

**Entry Points**:
```python
from apps.batch.services.growth_assimilation import GrowthAssimilationEngine, recompute_batch_assignments

# Single assignment
engine = GrowthAssimilationEngine(assignment)
result = engine.recompute_range(start_date, end_date)

# Batch-level (all assignments)
result = recompute_batch_assignments(batch_id, start_date, end_date)
```

---

## 🚀 What's Next (Your Mission: Phases 4-9)

### Phase 4: Event-Driven Recompute + Celery ⏳ PRIORITY
**Why critical**: Makes the system real-time. Without this, engine must be run manually.

**What you need to do**:
1. **Celery Setup** (you mentioned no Celery yet - need Redis/RabbitMQ)
   - Install Celery, Redis (or RabbitMQ)
   - Configure in `aquamind/settings.py`
   - Create `apps/batch/tasks.py` for Celery tasks

2. **Django Signals** - Trigger recompute on events:
   - `GrowthSample` saved → recompute [sample_date-2, sample_date+2]
   - `TransferAction` completed with measured_weight → recompute around execution date
   - `Treatment` with includes_weighing → recompute around treatment date
   - `FeedingEvent` saved → optional (consider if needed for FCR)
   - `MortalityEvent` saved → optional (mortality is prorated anyway)

3. **Celery Task**: Wrapper around engine
```python
@shared_task(bind=True, max_retries=3)
def recompute_assignment_window(self, assignment_id, start_date, end_date):
    try:
        assignment = BatchContainerAssignment.objects.get(id=assignment_id)
        engine = GrowthAssimilationEngine(assignment)
        return engine.recompute_range(start_date, end_date)
    except Exception as exc:
        raise self.retry(exc=exc)
```

4. **Nightly Job**: Catch-up for last 7-14 days (Celery Beat or Django management command)

**Gotchas**:
- Signals should be lightweight - just enqueue task, don't compute
- Use atomic transactions
- Consider deduplication (multiple events same day → one recompute)

### Phase 5: Weekly CAGGs ⏸️
Create TimescaleDB continuous aggregates for faster charting (weekly rollups).

### Phase 6: API Endpoints ⏸️
**Critical for UI**: Combined endpoint returning Samples + Scenario + Actual overlays.
- Follow API standards: `aquamind/docs/quality_assurance/api_standards.md`
- Update OpenAPI spec: `api/openapi.yaml`
- Regenerate frontend client after OpenAPI update

### Phase 7: Frontend Overlays ⏸️
React components in `client/src/features/batch-management/` for Growth Analysis page.

### Phase 8: Production Planner Integration ⏸️
Implement the `_evaluate_planner_triggers()` hook (currently just logs).

### Phase 9: Backfill & Validation ⏸️
**Critical for UAT**: Test with real Faroe Islands data (33 batches, 456 assignments, 45,772 samples!).

---

## 🧠 Critical Context for Success

### Test Data Available
- **Faroe Islands**: 39 batches, 500+ assignments, 47,000+ growth samples (COMPLETE)
- **Scotland**: Currently generating (don't interfere)
- **Use Faroe Islands data for testing**

### Field Name Gotchas (Real vs. Pseudocode)
The pseudocode in the plan uses simplified names. Here are actual field names:

| Pseudocode | Actual Field Name | Model |
|------------|-------------------|-------|
| `execution_date` | `actual_execution_date` | TransferAction |
| `event_date` | `feeding_date` | FeedingEvent |
| `parameter='temperature'` | `parameter__name='temperature'` | EnvironmentalReading (FK) |
| `batch_container_assignment` | `batch` | MortalityEvent (batch-level!) |

### MortalityEvent Is Batch-Level
**Important**: MortalityEvent links to Batch, not BatchContainerAssignment.  
**Solution**: Engine prorates batch mortality across assignments based on population share.

### Type Safety: Decimal vs Float
- Models use `Decimal` for precision
- TGCCalculator expects `float`
- **Always convert**: `float(decimal_value)` before TGC, `Decimal(str(float_value))` before save

### TimescaleDB Strategy
Per `aquamind/docs/quality_assurance/timescaledb_testing_strategy.md`:
- **Dev**: Migrations skip TimescaleDB (but you manually configured it!)
- **CI/SQLite**: Skips TimescaleDB (regular tables work fine)
- **Tests**: Must work on both PostgreSQL and SQLite

Current state: `batch_actualdailyassignmentstate` IS a hypertable in dev (you ran the script).

### Test Helpers
**Don't reinvent the wheel** - reuse existing test utils:
- Batch: `apps/batch/tests/models/test_utils.py`
- Scenario: `apps/scenario/tests/test_helpers.py`
- Infrastructure: Check `apps/infrastructure/tests/` for container/area setup

**Field requirements** (learned the hard way):
- `Area`: needs latitude, longitude, max_biomass
- `ContainerType`: needs category='TANK', max_volume_m3
- `FeedingEvent`: needs feeding_time, batch_biomass_kg (not just amount_kg)

### Testing Requirements
**Always run both**:
```bash
python manage.py test                           # PostgreSQL
python manage.py test --settings=aquamind.settings_ci  # SQLite
```

**Before declaring phase complete**: Full suite must pass on both databases.

---

## 📁 Project Structure

### Backend (AquaMind repo)
```
apps/batch/
├── models/
│   ├── actual_daily_state.py          ← Phase 2 model
│   ├── workflow_action.py             ← Has measured_* fields (Phase 1)
│   └── ...
├── services/
│   └── growth_assimilation.py         ← THE ENGINE (Phase 3)
├── migrations/
│   ├── 0031_add_measured_fields_to_transferaction.py
│   ├── 0032_add_pinned_scenario_to_batch.py
│   ├── 0033_create_actual_daily_state_model.py
│   └── 0034_setup_timescaledb_hypertable.py
└── tests/
    ├── test_phase1_schema_migrations.py  ← 9 tests
    ├── test_phase2_schema_only.py        ← 8 tests
    └── test_phase3_core_engine.py        ← 12 tests ✅

apps/health/
└── migrations/
    └── 0027_add_weighing_links_to_treatment.py

apps/environmental/
└── migrations/
    └── 0014_create_daily_temp_cagg.py

scripts/timescaledb/
├── setup_daily_state_hypertable.sql   ← Already run in dev!
├── setup_temperature_cagg.sql
└── setup_environmental_hypertables.sql

aquamind/docs/progress/batch_growth_assimilation/
├── batch-growth-assimilation-plan.md  ← Master plan (442 lines)
├── technical_design.md                ← Deep dive on architecture
├── PHASE_1_COMPLETE.md               ← Schema details
├── PHASE_2_COMPLETE.md               ← Hypertable details
├── PHASE_3_COMPLETE.md               ← Engine details
└── HANDOVER.md                        ← YOU ARE HERE
```

### Frontend (AquaMind-Frontend repo)
**Not touched yet** - Phase 7 will add React components for Growth Analysis page.

---

## 🔧 Development Setup

### Database Status
- **Dev PostgreSQL**: Running, TimescaleDB extension installed
- **Hypertable**: `batch_actualdailyassignmentstate` IS configured (1 dimension, compression enabled)
- **Migrations**: All applied through 0034
- **Test Data**: Faroe Islands complete (33 batches ready for Phase 9 testing)

### Git Status
- **Branch**: `feature/batch-growth-assimilation-112`
- **Main**: Clean, rebased
- **Commits**: 8 commits so far (schema, hypertable, engine, docs)
- **Ready for**: Phase 4+ commits

### Environment
- **Python**: 3.11.9 (pyenv)
- **Django**: 4.2.x
- **PostgreSQL**: With TimescaleDB extension
- **Machine**: M4 Max MacBook Pro, 128GB RAM (plenty of headroom!)

---

## 🎓 Lessons Learned (Don't Repeat)

### ✅ Do This
1. **Use existing test helpers** - they handle all the field requirements correctly
2. **Check actual field names** - don't trust pseudocode naming
3. **Simple core tests** - complex edge cases belong in Phase 9 with real data
4. **Database-agnostic tests** - use Django model introspection, not raw SQL
5. **Type conversions** - Decimal ↔ float explicitly
6. **Run both databases** - PostgreSQL AND SQLite before declaring success

### ❌ Don't Do This
1. **Don't reinvent test fixtures** - existing helpers are battle-tested
2. **Don't use PostgreSQL-specific SQL in tests** - breaks SQLite
3. **Don't create complex test fixtures** - they break on constraint violations
4. **Don't trust migration helpers blindly** - TimescaleDB helpers have quoting bugs
5. **Don't skip the pseudocode** - it's the specification (plan lines 138-300)

### 🐛 Known Gotchas
1. **MortalityEvent is batch-level** - must prorate to assignments
2. **FeedingEvent requires feeding_time AND feeding_date** - not just one
3. **EnvironmentalReading.parameter is FK** - join with EnvironmentalParameter table
4. **TimescaleDB migrations can abort transactions** - use skip strategy for dev/CI
5. **Test database can have stale connections** - might need to kill before fresh test run

---

## 📖 Essential Reading (In Order)

### Before Starting Phase 4
1. **Implementation Plan**: `batch-growth-assimilation-plan.md` (lines 371-381 for Phase 4)
2. **Technical Design**: `technical_design.md` (Section 5: Inter-App Communication, recommends Celery)
3. **Operational Scheduling Architecture**: `aquamind/docs/progress/operational_scheduling/operational_scheduling_architecture.md` (for Phase 8 integration context)

### Reference Docs
- **API Standards**: `aquamind/docs/quality_assurance/api_standards.md` (for Phase 6)
- **TimescaleDB Strategy**: `aquamind/docs/quality_assurance/timescaledb_testing_strategy.md` (explains skip approach)
- **Phase Completion Docs**: `PHASE_1_COMPLETE.md`, `PHASE_2_COMPLETE.md`, `PHASE_3_COMPLETE.md` (detailed specs)

### Code References
- **TGC Calculator**: `apps/scenario/services/calculations/tgc_calculator.py` (reused in engine)
- **Mortality Calculator**: `apps/scenario/services/calculations/mortality_calculator.py` (reused in engine)
- **Projection Engine**: `apps/scenario/services/calculations/projection_engine.py` (similar patterns)

---

## 🧪 Testing Strategy

### Test Requirements
- **Always run both databases** before committing
- **No regressions**: Full suite must continue to pass
- **Database-agnostic**: Use Django ORM, not raw SQL in tests
- **Simple fixtures**: Use test helpers, keep setup minimal

### Current Test Counts
- **Phase 1**: 9 schema validation tests
- **Phase 2**: 8 schema validation tests  
- **Phase 3**: 12 core engine tests
- **Total Suite**: 1243 tests (all passing on both databases)

### For Phase 4+ Testing
- **Celery tests**: Mock/patch Celery tasks, don't rely on broker
- **Signal tests**: Verify signal handlers enqueue tasks (don't execute)
- **Integration tests**: Use real Faroe Islands data in Phase 9

---

## 🔍 Quick Debugging Guide

### If Tests Fail
1. **Field name issue?** Check actual model fields vs. what test uses
2. **Constraint violation?** Check if test creates duplicate data (use UUID not timestamp)
3. **Type error (Decimal/float)?** Convert explicitly before passing to calculators
4. **Transaction aborted?** Check if TimescaleDB operation failed (should skip gracefully)

### If Engine Doesn't Compute
1. **No scenario?** Batch must have pinned_scenario or scenarios.first()
2. **No temperature?** Falls back to profile (should work but check TGC model has profile)
3. **States not created?** Check engine logs (logger.info/error messages)
4. **Wrong values?** Check provenance: state.sources and state.confidence_scores tell you where data came from

### If Migrations Fail
1. **TimescaleDB error?** Expected in CI/SQLite - should skip gracefully
2. **Duplicate migration?** Check `ls apps/batch/migrations/0034*` - should be only ONE 0034 file
3. **Conflict?** Run `python manage.py showmigrations` to see tree

---

## 🏗️ Phase 4 Implementation Guide

### Step 1: Celery Infrastructure Setup
```bash
# Install
pip install celery redis

# Add to requirements.txt
celery==5.3.4
redis==5.0.1
```

**Config** (`aquamind/settings.py`):
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

### Step 2: Create Celery App
Create `aquamind/__init__.py` Celery setup (follow Django Celery docs).

### Step 3: Create Tasks
**File**: `apps/batch/tasks.py`
```python
from celery import shared_task
from .services.growth_assimilation import GrowthAssimilationEngine

@shared_task(bind=True, max_retries=3)
def recompute_assignment_window(self, assignment_id, start_date, end_date):
    """Recompute daily states for assignment in date window."""
    # Implementation here
```

### Step 4: Create Signals
**File**: `apps/batch/signals.py`
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GrowthSample
from .tasks import recompute_assignment_window

@receiver(post_save, sender=GrowthSample)
def on_growth_sample_saved(sender, instance, created, **kwargs):
    if created:
        # Enqueue recompute window [sample_date-2, sample_date+2]
        recompute_assignment_window.delay(...)
```

Register in `apps/batch/apps.py`:
```python
def ready(self):
    import apps.batch.signals
```

### Step 5: Nightly Job
Create management command: `apps/batch/management/commands/recompute_daily_states.py`

### Step 6: Tests
- Test signals enqueue tasks (mock Celery)
- Test task executes engine
- Test idempotency (safe to run multiple times)

**Reference Pattern**: Look at how `apps/operational` or other apps use signals (if any exist).

---

## 🎯 Success Criteria for Phase 4

- [ ] Celery configured and worker running
- [ ] Signals created for GrowthSample, TransferAction, Treatment
- [ ] Tasks enqueue and execute without errors
- [ ] Nightly catch-up job implemented
- [ ] Tests verify signals trigger recompute
- [ ] Full test suite passes (no regressions)
- [ ] Documentation updated

**Time Estimate**: 2-4 hours (includes Celery setup, signals, tests)

---

## 🎯 Success Criteria for Phase 6 (API)

This is **critical path to frontend**:

- [ ] Endpoint: `GET /api/v1/batch/{id}/growth-analysis/combined/`
  - Returns: {samples[], scenario_projection[], actual_daily_states[]}
  - Supports: date range, granularity (daily/weekly), optional assignment_id filter
- [ ] Endpoint: `POST /api/v1/scenario/scenarios/{id}/pin_to_batch/`
- [ ] Endpoint: `POST /api/v1/batch/{id}/daily-state/recompute/` (admin)
- [ ] OpenAPI spec updated in `api/openapi.yaml`
- [ ] Frontend client regenerated: `cd client && npm run generate:api`
- [ ] API tests verify shape, pagination, permissions

**Reference**: Look at existing batch API endpoints in `apps/batch/api/viewsets/`.

---

## 🎯 Success Criteria for Phase 7 (Frontend)

**Where to work**: `client/src/features/batch-management/`

**What to add**:
- Growth Analysis page overlay toggles
- Recharts/Chart.js chart with 3 series (Samples, Scenario, Actual)
- Scenario selector + Pin button
- Container drilldown
- Tooltips showing sources/confidence

**Reference**: Existing scenario planning UI patterns in `client/src/features/scenario-planning/`.

---

## 📊 Current Git Status

```bash
Branch: feature/batch-growth-assimilation-112
Ahead of main by: 11 commits
Working tree: Clean
```

**Commits so far**:
1. docs: Add batch growth assimilation plan
2. feat: Phase 1 schema enhancements
3. fix: Database-agnostic tests
4. docs: Phase 1 complete
5. feat: Phase 2 model and TimescaleDB
6. docs: Phase 2 complete + production guide
7. docs: Environmental hypertables follow-up note
8. feat: Phase 3 engine implementation
9. docs: Phase 3 complete

**When done with all phases**: Create PR against main, reference issue #112.

---

## 💡 Pro Tips

### For Phase 4 (Celery)
- Start Celery worker locally: `celery -A aquamind worker -l info`
- Monitor with Flower (if installed): `celery -A aquamind flower`
- Test without broker in tests: Mock `task.delay()` calls

### For Phase 6 (API)
- **Contract-first**: Update OpenAPI spec FIRST, then implement
- Use DRF viewsets, not function views (consistency)
- Add pagination (queryset can be large)
- Add permissions: `can_recompute_daily_state` for admin endpoints

### For Phase 9 (Validation)
- Pick 2-3 representative Faroe Islands batches
- Run recompute for full lifecycle (~900 days)
- Compare actual vs. growth samples (should align at anchors)
- Check confidence scores make sense
- Look for anomalies in provenance

### General
- **Commit frequently** - one logical unit per commit
- **Update plan** - check off items as you complete them
- **Create PHASE_X_COMPLETE.md** after each phase
- **Run full suite** before each commit
- **Check context window** - if getting full, create summary

---

## ⚠️ Potential Challenges

### Phase 4: Celery Setup
**Challenge**: No Celery in project yet  
**Solution**: Standard Django-Celery integration, plenty of docs online  
**Time**: 1-2 hours for setup + configuration

### Phase 5: Weekly CAGGs
**Challenge**: Depends on environmental_environmentalreading being a hypertable (it's not)  
**Solution**: Either configure environmental hypertables OR create weekly rollups via Django ORM (less efficient but works)  
**Decision**: Can defer CAGG approach to production if needed

### Phase 6: OpenAPI Spec
**Challenge**: Must match frontend expectations exactly  
**Solution**: Follow existing endpoint patterns, test with Swagger UI  
**Critical**: Frontend CI auto-regenerates client from spec - spec must be correct

### Phase 8: Production Planner
**Challenge**: Planner app doesn't exist yet (per operational_scheduling_architecture.md)  
**Solution**: Phase 8 may need to coordinate with or follow planner implementation  
**Fallback**: Stub the integration, implement later

---

## 🆘 If You Get Stuck

### Common Issues & Solutions

**"Tests fail on SQLite but pass on PostgreSQL"**  
→ Check for PostgreSQL-specific SQL (information_schema, etc.)  
→ Use Django ORM introspection instead

**"Celery tasks not running"**  
→ Verify Redis is running: `redis-cli ping`  
→ Check Celery worker logs  
→ Verify task is registered: `celery -A aquamind inspect registered`

**"Engine produces wrong values"**  
→ Check provenance: `state.sources` and `state.confidence_scores`  
→ Enable debug logging: `logger.setLevel(logging.DEBUG)`  
→ Verify scenario models (TGC, mortality rates)

**"Migration conflict"**  
→ Check for duplicate 0034 files: `ls apps/batch/migrations/0034*`  
→ Should be only ONE: `0034_setup_timescaledb_hypertable.py`

### Resources
- **Celery Docs**: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
- **DRF ViewSets**: https://www.django-rest-framework.org/api-guide/viewsets/
- **TimescaleDB Docs**: https://docs.timescale.com/ (for Phase 5 CAGGs)

---

## 📝 Handover Checklist

Before you start:
- [ ] Read this handover doc fully
- [ ] Read Phase 4 section in implementation plan (lines 371-381)
- [ ] Review Phase 3 engine code (`growth_assimilation.py`) to understand what you're building on
- [ ] Check git status: `git status` and `git log --oneline -10`
- [ ] Verify tests pass: Run full suite on both databases
- [ ] Start Celery worker (Phase 4): Have Redis running

After each phase:
- [ ] Run full test suite on both databases
- [ ] Update implementation plan (check off items)
- [ ] Create PHASE_X_COMPLETE.md
- [ ] Commit with clear message referencing #112
- [ ] Update this handover if you discover new gotchas

---

## 🚀 You're Ready!

**Phases 1-3 are rock solid**. The foundation is built, the engine works, the magic happens.

**Your job**: Wire it up (Phase 4), expose it (Phase 6), visualize it (Phase 7), integrate it (Phase 8), and validate it (Phase 9).

**Confidence level**: 🟢 **High** - Clean architecture, tested foundation, clear path forward.

**Time to UAT**: Phases 4-9 are ~10-20 hours of focused work. Each phase builds on solid ground.

---

**Good luck! You've got this. The hard part is done. 🚀**

---

*End of Handover Document*

