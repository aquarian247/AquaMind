# Audit Trail Verification & Fix Playbook

**Purpose**: Systematic verification and fixing of audit trail compliance across all AquaMind apps  
**Context**: Based on Health app fixes completed during Phase 4 (commits `143a2dd`, `0721568`)  
**Target Apps**: Infrastructure, Batch, Inventory, Broodstock, Scenario, Harvest, Environmental, Users  
**Status**: Template for future agent execution

---

## 🎯 Executive Summary

**Goal**: Ensure 100% audit trail compliance across all apps for Faroese and Scottish regulatory requirements.

**Two-Part Fix**:
1. **Models**: Add `HistoricalRecords()` to all tracked models
2. **Viewsets**: Add `HistoryReasonMixin` to all viewsets (must be first in MRO chain)

**Expected Outcome**: Complete audit trail with descriptive change reasons for all CUD operations

---

## 📋 Verification Workflow (Per App)

### Step 1: Analyze Current State

Run these commands for each app (replace `{APP}` with app name):

```bash
# 1. Check which models have HistoricalRecords
cd /Users/aquarian247/Projects/AquaMind
python manage.py shell -c "
from django.apps import apps
from apps.{APP}.models import *

# Get all non-historical models
models = [m for m in apps.get_app_config('{APP}').get_models() 
          if 'historical' not in m._meta.model_name.lower()]

# Check which have history attribute
models_with_history = [m.__name__ for m in models if hasattr(m, 'history')]
models_without_history = [m.__name__ for m in models if not hasattr(m, 'history')]

print('Models WITH history:', models_with_history)
print('Models WITHOUT history:', models_without_history)
print(f'Coverage: {len(models_with_history)}/{len(models)} ({len(models_with_history)/len(models)*100:.0f}%)')
"

# 2. Check which viewsets have HistoryReasonMixin
grep -r "HistoryReasonMixin" apps/{APP}/api/viewsets/*.py

# 3. Count viewsets that SHOULD have the mixin
find apps/{APP}/api/viewsets -name "*.py" ! -name "__init__.py" ! -name "history.py" | wc -l

# 4. Verify historical tables exist in database
python manage.py shell -c "
from django.apps import apps
historical_models = [m for m in apps.get_app_config('{APP}').get_models() 
                     if 'historical' in m._meta.model_name.lower()]
print('Historical tables:', sorted([m._meta.db_table for m in historical_models]))
print(f'Total: {len(historical_models)}')
"
```

### Step 2: Document Findings

Create a summary table:

| Component | Expected | Actual | Status | Gap |
|-----------|----------|--------|--------|-----|
| Models with HistoricalRecords | X | Y | ✅/❌ | Z missing |
| Viewsets with HistoryReasonMixin | X | Y | ✅/❌ | Z missing |
| Historical tables in DB | X | Y | ✅/❌ | Z missing |

### Step 3: Cross-Reference with data_model.md

Check `aquamind/docs/database/data_model.md` lines 21-127 for:
- Which models SHOULD be tracked (per regulatory requirements)
- Expected historical tables (section 3.1)
- Audit trail requirements

### Step 4: Identify Priority Fixes

**High Priority** (user-facing, regulatory critical):
- Models involved in batch tracking (egg to plate traceability)
- Models with CUD operations via frontend forms
- Models referenced in regulatory compliance

**Medium Priority** (operational):
- Reference data models (species, lifecycle stages, etc.)
- Configuration models

**Low Priority** (skip if not tracked):
- Read-only models
- System models
- Models explicitly excluded from history tracking

---

## 🔧 Fix Implementation

### Fix 1: Add HistoryReasonMixin to Viewsets

**For each viewset file** in `apps/{APP}/api/viewsets/`:

**Before**:
```python
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin

class MyEntityViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                     StandardFilterMixin, viewsets.ModelViewSet):
    """API endpoint for managing MyEntity."""
    queryset = MyEntity.objects.all()
```

**After**:
```python
from aquamind.utils.history_mixins import HistoryReasonMixin  # ADD THIS
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin

class MyEntityViewSet(HistoryReasonMixin, UserAssignmentMixin,  # ADD FIRST
                     OptimizedQuerysetMixin, StandardFilterMixin, 
                     viewsets.ModelViewSet):
    """
    API endpoint for managing MyEntity.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.  # ADD THIS
    """
    queryset = MyEntity.objects.all()
```

**Critical Rules**:
1. ✅ Import from `aquamind.utils.history_mixins`
2. ✅ Place `HistoryReasonMixin` **FIRST** in inheritance chain (leftmost)
3. ✅ Update docstring to mention audit trail capture
4. ✅ No changes to queryset or other configuration needed

**Why First**: Python MRO (Method Resolution Order) - first class wins for `perform_create/update/destroy` overrides

### Fix 2: Add HistoricalRecords to Models

**For each model** missing `history = HistoricalRecords()`:

**Before**:
```python
from django.db import models

class MyEntity(models.Model):
    # ... fields ...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
```

**After**:
```python
from django.db import models
from simple_history.models import HistoricalRecords  # ADD THIS

class MyEntity(models.Model):
    # ... fields ...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()  # ADD THIS (before Meta or after timestamps)

    class Meta:
        ordering = ['-created_at']
```

**Critical Rules**:
1. ✅ Import `HistoricalRecords` at top of file
2. ✅ Add `history = HistoricalRecords()` to model class
3. ✅ Place before `class Meta` or after timestamp fields
4. ✅ Run migrations after all models updated

### Fix 3: Create and Run Migrations

```bash
# Create migrations
cd /Users/aquarian247/Projects/AquaMind
python manage.py makemigrations {APP} --name add_history_to_models

# Review migration (check what historical tables will be created)
cat apps/{APP}/migrations/XXXX_add_history_to_models.py

# Run migrations
python manage.py migrate

# Verify historical tables created
python manage.py shell -c "
from django.apps import apps
historical_models = [m for m in apps.get_app_config('{APP}').get_models() 
                     if 'historical' in m._meta.model_name.lower()]
print(f'Created {len(historical_models)} historical tables')
print('Tables:', [m._meta.db_table for m in historical_models])
"
```

### Fix 4: Regenerate OpenAPI Schema

```bash
# Regenerate schema
cd /Users/aquarian247/Projects/AquaMind
python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn

# Verify zero warnings
echo "✅ Schema regenerated successfully"

# Sync to frontend
cp api/openapi.yaml /Users/aquarian247/Projects/AquaMind-Frontend/api/openapi.yaml
echo "✅ Schema synced to frontend"
```

### Fix 5: Test & Verify

```bash
# Run app-specific tests
python manage.py test apps.{APP} --settings=aquamind.settings_ci

# Run API contract tests
python manage.py test apps.api.tests.test_contract --settings=aquamind.settings_ci

# Verify all tests pass
echo "✅ All tests passing"
```

---

## 🐛 Common Issues & Solutions

### Issue 1: NOT NULL constraint failed on user_id

**Symptom**:
```
IntegrityError: NOT NULL constraint failed: {app}_{model}.user_id
```

**Root Cause**: `HistoryReasonMixin` bypasses `UserAssignmentMixin` due to MRO

**Solution**: Already fixed in `aquamind/utils/history_mixins.py` (commit `0721568`)
- HistoryReasonMixin now detects `user_field` attribute
- Auto-populates user if viewset has UserAssignmentMixin

**Verify fix exists**:
```bash
grep -A 10 "def perform_create" /Users/aquarian247/Projects/AquaMind/aquamind/utils/history_mixins.py | grep "user_field"
# Should see: if hasattr(self, 'user_field')...
```

### Issue 2: Migration creates tables for related apps

**Symptom**: Running `makemigrations {APP}` creates migrations in other apps

**Root Cause**: Models have FK relationships, schema changes cascade

**Solution**: This is **normal and harmless**
- Review both migrations
- Apply both migrations
- Verify tests still pass

**Example**: Adding HistoricalRecords to health models triggered batch migration

### Issue 3: Tests fail after adding HistoryReasonMixin

**Symptom**: Existing tests fail with unexpected behavior

**Root Cause**: Tests may need to account for historical records

**Solution**: 
1. Check if test explicitly checks instance.history
2. Update test to expect historical records
3. Or add `.exclude()` to filter out historical tables

---

## 📊 Per-App Checklist

### Infrastructure App

**Expected Models with History** (per data_model.md):
- [ ] Geography
- [ ] Area
- [ ] FreshwaterStation
- [ ] Hall
- [ ] ContainerType
- [ ] Container
- [ ] Sensor
- [ ] FeedContainer

**Viewsets to Check**:
- [ ] GeographyViewSet
- [ ] AreaViewSet
- [ ] FreshwaterStationViewSet
- [ ] HallViewSet
- [ ] ContainerTypeViewSet
- [ ] ContainerViewSet
- [ ] SensorViewSet
- [ ] FeedContainerViewSet

**Verification Command**:
```bash
python manage.py test apps.infrastructure --settings=aquamind.settings_ci
```

### Batch App

**Expected Models with History** (per data_model.md):
- [ ] Species
- [ ] LifeCycleStage
- [ ] Batch
- [ ] BatchContainerAssignment
- [ ] BatchComposition
- [ ] BatchTransfer
- [ ] MortalityEvent
- [ ] GrowthSample

**Viewsets to Check**:
- [ ] SpeciesViewSet
- [ ] LifeCycleStageViewSet
- [ ] BatchViewSet
- [ ] BatchContainerAssignmentViewSet
- [ ] BatchTransferViewSet
- [ ] MortalityEventViewSet
- [ ] GrowthSampleViewSet

**Verification Command**:
```bash
python manage.py test apps.batch --settings=aquamind.settings_ci
```

### Inventory App

**Expected Models with History** (per data_model.md):
- [ ] Feed
- [ ] FeedPurchase
- [ ] FeedStock
- [ ] FeedingEvent
- [ ] ContainerFeedingSummary
- [ ] BatchFeedingSummary
- [ ] FeedContainerStock

**Viewsets to Check**:
- [ ] FeedViewSet
- [ ] FeedPurchaseViewSet
- [ ] FeedStockViewSet
- [ ] FeedingEventViewSet
- [ ] FeedContainerStockViewSet

**Verification Command**:
```bash
python manage.py test apps.inventory --settings=aquamind.settings_ci
```

**Note**: Inventory was verified in Phase 3 - should be 100% compliant already!

### Broodstock App

**Expected Models with History** (per data_model.md):
- [ ] BroodstockFish
- [ ] FishMovement
- [ ] BreedingPair
- [ ] BreedingPlan
- [ ] BreedingTraitPriority
- [ ] EggProduction
- [ ] EggSupplier
- [ ] ExternalEggBatch
- [ ] BatchParentage

**Verification Command**:
```bash
python manage.py test apps.broodstock --settings=aquamind.settings_ci
```

### Scenario App

**Expected Models with History** (per data_model.md):
- [ ] Scenario
- [ ] ScenarioModelChange
- [ ] ScenarioProjection
- [ ] TemperatureProfile
- [ ] TemperatureReading
- [ ] TGCModel
- [ ] FCRModel
- [ ] FCRModelStage
- [ ] MortalityModel

**Verification Command**:
```bash
python manage.py test apps.scenario --settings=aquamind.settings_ci
```

### Harvest App

**Expected Models with History** (per data_model.md):
- [ ] HarvestEvent
- [ ] HarvestLot
- [ ] HarvestWaste
- [ ] ProductGrade

**Verification Command**:
```bash
python manage.py test apps.harvest --settings=aquamind.settings_ci
```

### Users App

**Expected Models with History** (per data_model.md):
- [ ] UserProfile

**Verification Command**:
```bash
python manage.py test apps.users --settings=aquamind.settings_ci
```

---

## 🤖 Agent Execution Template

**Use this prompt for the audit trail verification agent**:

```
Task: Verify and fix audit trail compliance for AquaMind apps following the AUDIT_TRAIL_VERIFICATION_PLAYBOOK.md

Context:
- Health app is 100% compliant (reference implementation)
- Infrastructure, Batch, Inventory apps likely need fixes
- Broodstock, Scenario, Harvest apps definitely need fixes

Instructions:
1. Read AUDIT_TRAIL_VERIFICATION_PLAYBOOK.md
2. Read BACKEND_AUDIT_TRAIL_FIXES.md (Health app reference)
3. For EACH app (start with Infrastructure):
   a. Run Step 1 verification commands
   b. Document findings in table format
   c. Identify gaps (missing HistoricalRecords or HistoryReasonMixin)
   d. Apply fixes following the exact patterns from Health app
   e. Create migrations and run them
   f. Run tests to verify no regressions
   g. Move to next app

4. After ALL apps fixed:
   a. Regenerate OpenAPI schema
   b. Run full test suite (all apps)
   c. Sync schema to frontend
   d. Commit with descriptive message
   e. Push to main

5. Create AUDIT_TRAIL_COMPLIANCE_REPORT.md with:
   - Per-app findings and fixes
   - Before/after statistics
   - Test results
   - Regulatory compliance status

Quality Gates:
- Zero test failures
- Zero OpenAPI warnings
- 100% model coverage (all tracked models have HistoricalRecords)
- 100% viewset coverage (all viewsets have HistoryReasonMixin)

Estimated Time: 4-6 hours for all apps
```

---

## 📊 Expected Findings Template

### App: {APP_NAME}

**Models Analysis**:
- Total models: X
- Models WITH history: Y (Z%)
- Models WITHOUT history: W
- **Gap**: List missing models

**Viewsets Analysis**:
- Total viewsets: X
- Viewsets WITH mixin: Y (Z%)
- Viewsets WITHOUT mixin: W
- **Gap**: List missing viewsets

**Priority**:
- [ ] High - Has frontend forms
- [ ] Medium - Operational data
- [ ] Low - Reference data only

**Action Required**:
- [ ] Add HistoricalRecords to W models
- [ ] Add HistoryReasonMixin to W viewsets
- [ ] Create migration
- [ ] Run tests

---

## 🎓 Reference: Health App Solution

### What Was Fixed (Example)

**Models** (3 missing):
```python
# apps/health/models/health_observation.py
from simple_history.models import HistoricalRecords

class HealthParameter(models.Model):
    # ... fields ...
    history = HistoricalRecords()  # ADDED

class HealthSamplingEvent(models.Model):
    # ... fields ...
    history = HistoricalRecords()  # ADDED

class IndividualFishObservation(models.Model):
    # ... fields ...
    history = HistoricalRecords()  # ADDED
```

**Viewsets** (10 total):
```python
# apps/health/api/viewsets/journal_entry.py
from aquamind.utils.history_mixins import HistoryReasonMixin  # ADDED

class JournalEntryViewSet(HistoryReasonMixin, UserAssignmentMixin,  # ADDED FIRST
                         OptimizedQuerysetMixin, StandardFilterMixin,
                         viewsets.ModelViewSet):
    """
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.  # ADDED
    """
```

**Migration**:
```bash
python manage.py makemigrations health --name add_history_to_models
# Created: apps/health/migrations/0019_add_history_to_observation_models.py

python manage.py migrate
# Applied: health.0019, batch.0021 (side effect)
```

**Testing**:
```bash
python manage.py test apps.health --settings=aquamind.settings_ci
# Result: 122/122 pass ✅
```

---

## 🔍 Verification Commands Reference

### Check Model Coverage
```bash
# Per app
python manage.py shell -c "
from apps.{APP}.models import *
import inspect
models = [obj for name, obj in inspect.getmembers(
    __import__('apps.{APP}.models'), 
    inspect.isclass
) if hasattr(obj, '_meta') and obj._meta.app_label == '{APP}']
models_with_history = [m.__name__ for m in models if hasattr(m, 'history')]
print(f'{len(models_with_history)}/{len(models)} models have history')
"
```

### Check Viewset Coverage
```bash
# Count viewsets with mixin
grep -l "HistoryReasonMixin" apps/{APP}/api/viewsets/*.py | wc -l

# List viewsets WITHOUT mixin
for f in apps/{APP}/api/viewsets/*.py; do
  if ! grep -q "HistoryReasonMixin" "$f" 2>/dev/null; then
    echo "Missing: $f"
  fi
done
```

### Check Historical Tables in Database
```bash
# PostgreSQL
psql -d aquamind -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE '{APP}_historical%'
ORDER BY table_name;
"

# Via Django ORM (works with any DB)
python manage.py shell -c "
from django.apps import apps
tables = [m._meta.db_table for m in apps.get_app_config('{APP}').get_models() 
          if 'historical' in m._meta.model_name.lower()]
for t in sorted(tables): print(t)
"
```

---

## 🚨 Critical MRO Issue & Fix (Already Applied)

### The Problem (Discovered in Health App)

**Symptom**: Tests fail with `NOT NULL constraint failed: {model}.user_id`

**Root Cause**: Method Resolution Order conflict
```python
class MyViewSet(HistoryReasonMixin, UserAssignmentMixin, viewsets.ModelViewSet):
    user_field = 'user'
```

Python calls `HistoryReasonMixin.perform_create()` → `UserAssignmentMixin.perform_create()` never runs → user_id stays NULL!

### The Solution (Already in history_mixins.py)

**File**: `aquamind/utils/history_mixins.py` (commit `0721568`)

```python
def perform_create(self, serializer):
    # Check if viewset has a user_field (for UserAssignmentMixin compatibility)
    kwargs = {}
    if hasattr(self, 'user_field') and self.request.user.is_authenticated:
        kwargs[self.user_field] = self.request.user
    
    instance = serializer.save(**kwargs)  # ✅ User populated!
    # ... rest of history logic
```

**Verify this fix exists before starting**:
```bash
grep -A 5 "Check if viewset has a user_field" \
  /Users/aquarian247/Projects/AquaMind/aquamind/utils/history_mixins.py
# Should show the compatibility code
```

**If missing**: Apply the fix from commit `0721568` before proceeding!

---

## 📈 Success Metrics

### Per-App Goals

| Metric | Target | Verification |
|--------|--------|--------------|
| Models with HistoricalRecords | 100% | All tracked models have `history` attribute |
| Viewsets with HistoryReasonMixin | 100% | All viewsets have mixin imported and first |
| Historical tables in DB | Complete | Migration creates all expected tables |
| Tests passing | 100% | No regressions after fixes |
| OpenAPI warnings | 0 | Schema validates cleanly |

### Project-Wide Goals

**Final State**:
- ✅ All apps: 100% audit trail coverage
- ✅ All viewsets: HistoryReasonMixin first in chain
- ✅ All models: HistoricalRecords present
- ✅ All tests: Passing
- ✅ Regulatory compliance: Complete

---

## 🎯 Execution Priority

### Recommended Order

1. **Infrastructure** - Has frontend forms (Phase 1), high priority
2. **Batch** - Has frontend forms (Phase 2), high priority
3. **Inventory** - Has frontend forms (Phase 3), likely already compliant
4. **Broodstock** - Has data model, medium priority
5. **Scenario** - Has data model, medium priority
6. **Harvest** - Recently added, medium priority
7. **Users** - Simple app, low priority
8. **Environmental** - Read-only mostly, low priority (check if needs tracking)

### Batch Execution Strategy

**Option A - One app at a time**:
- Fix app → Test → Commit → Move to next
- Safer, easier to debug
- Longer overall time

**Option B - Batch all fixes**:
- Fix all apps → Run all tests → Commit once
- Faster, but harder to debug if issues
- Recommended for experienced agent

---

## 📚 Documentation Requirements

After completing all fixes, create:

**AUDIT_TRAIL_COMPLIANCE_REPORT.md** containing:
1. Executive summary of all fixes
2. Per-app before/after statistics
3. Migration summary
4. Test results summary
5. Regulatory compliance status
6. Known issues or limitations
7. Recommendations for ongoing compliance

**Include**:
- Total models fixed
- Total viewsets fixed
- Total historical tables created
- Total migrations run
- Test coverage statistics
- Commit hashes

---

## 🔑 Key Principles

### Golden Rules

1. **HistoryReasonMixin ALWAYS first** in inheritance chain
2. **Both required**: HistoricalRecords (model) + HistoryReasonMixin (viewset)
3. **Test after each app** - don't batch blindly
4. **Verify MRO fix exists** - check history_mixins.py has user_field compatibility
5. **Document everything** - future agents need clear audit trail

### Quality Gates

**Before committing each app**:
- [ ] All app tests pass
- [ ] No new type errors
- [ ] No new linter warnings
- [ ] Historical tables verified in DB
- [ ] OpenAPI schema validates

**Before final push**:
- [ ] ALL app tests pass
- [ ] OpenAPI schema regenerated
- [ ] Frontend schema synced
- [ ] Comprehensive documentation created
- [ ] Commit message describes all changes

---

## 🎊 Success Criteria

**You're done when**:
1. ✅ All apps have 100% model coverage (HistoricalRecords)
2. ✅ All apps have 100% viewset coverage (HistoryReasonMixin)
3. ✅ All migrations applied successfully
4. ✅ All tests passing (zero failures)
5. ✅ OpenAPI schema validates with zero warnings
6. ✅ Frontend schema synced
7. ✅ Comprehensive report created
8. ✅ Changes committed and pushed to main

**Estimated Timeline**:
- Infrastructure: 1 hour
- Batch: 1 hour
- Inventory: 30 min (likely already compliant)
- Broodstock: 1 hour
- Scenario: 1 hour
- Harvest: 30 min
- Users: 15 min
- **Total**: 4-6 hours

---

## 📞 Getting Help

**Reference Documents**:
- `aquamind/docs/progress/audit_trail_gap_fixes/BACKEND_AUDIT_TRAIL_FIXES.md` - Complete Health app example
- `aquamind/docs/database/data_model.md` - Expected models with history
- `aquamind/utils/history_mixins.py` - Mixin implementation
- `apps/inventory/api/viewsets/` - Phase 3 reference (likely compliant)

**Common Questions**:

**Q**: Which models need HistoricalRecords?  
**A**: Check data_model.md section 3.1 "Tracked Models by App"

**Q**: Where does HistoryReasonMixin go in the inheritance chain?  
**A**: ALWAYS first (leftmost position)

**Q**: What if tests fail after adding mixin?  
**A**: Check for MRO fix in history_mixins.py (should auto-populate user fields)

**Q**: Do I need to update serializers?  
**A**: No! Mixin handles everything in viewset.perform_create/update/destroy

**Q**: What about OpenAPI schema changes?  
**A**: Adding mixin doesn't change API contract - only internal behavior

---

## ✅ Quick Start for Agent

```bash
# 1. Read this playbook
# 2. Read BACKEND_AUDIT_TRAIL_FIXES.md
# 3. Start with Infrastructure app:

cd /Users/aquarian247/Projects/AquaMind

# Verify current state
python manage.py shell -c "from apps.infrastructure.models import *; ..."

# Apply fixes to models and viewsets
# Create migrations
# Run tests
# Document findings

# 4. Repeat for each app
# 5. Create final compliance report
# 6. Commit and push to main
```

**Good luck! The patterns are proven - follow them carefully and you'll achieve 100% compliance!** 🎯

