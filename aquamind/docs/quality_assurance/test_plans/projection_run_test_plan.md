# ProjectionRun Implementation Test Plan

**Feature**: Projection Run Version Control for Scenario Planning  
**Implementation Date**: 2025-11-28  
**Test Plan Version**: 1.0  
**Status**: Ready for UAT

---

## 1. Overview

### 1.1 Purpose
This test plan validates the ProjectionRun implementation, which decouples projection data from scenario configuration. The feature enables:
- Version control for scenario projections
- History preservation when re-running projections
- Explicit batch pinning to specific projection runs
- Prevention of unexpected side effects when scenarios are updated

### 1.2 Scope
**In Scope:**
- Backend model changes (ProjectionRun, ScenarioProjection, Batch.pinned_projection_run)
- Data migrations and integrity
- API endpoints for projection runs
- Frontend UI integration in Growth Analysis tab
- Cross-domain functionality (signals, Celery tasks, growth assimilation)

**Out of Scope:**
- Performance optimization beyond baseline validation
- Advanced comparison UI features
- Automated run retention policies

### 1.3 Test Environment
- **Database**: PostgreSQL (production-like) and SQLite (CI)
- **Backend**: Django 4.2.11, Python 3.11
- **Frontend**: React 18, TypeScript, Vite
- **Test Data**: Migrated production-like scenarios (145 scenarios migrated)

---

## 2. Backend Testing

### 2.1 Model Layer Tests

#### Test Case 2.1.1: ProjectionRun Model Creation
**Objective**: Verify ProjectionRun model creates correctly with all fields

**Prerequisites**:
- Scenario exists with TGC, FCR, and mortality models
- User account exists

**Steps**:
1. Create a ProjectionRun with run_number=1
2. Verify all fields are set correctly
3. Check unique_together constraint on (scenario, run_number)

**Expected Results**:
- ProjectionRun created with auto-incrementing run_id
- run_date set automatically
- parameters_snapshot stores model data
- String representation shows "Scenario Name - Run #1"

**Database Verification**:
```sql
SELECT run_id, scenario_id, run_number, label, run_date, 
       total_projections, final_weight_g, final_biomass_kg, created_by_id
FROM scenario_projection_run
WHERE scenario_id = <test_scenario_id>;
```

**Expected Row Count**: 1  
**Expected Data**: run_number=1, total_projections >= 0

---

#### Test Case 2.1.2: ScenarioProjection Links to ProjectionRun
**Objective**: Verify ScenarioProjection correctly references ProjectionRun

**Prerequisites**:
- ProjectionRun exists

**Steps**:
1. Create multiple ScenarioProjection records linked to ProjectionRun
2. Query projections via projection_run.projections.all()
3. Verify foreign key relationship

**Expected Results**:
- All projections linked to correct ProjectionRun
- Cascade delete works (deleting run deletes projections)
- Ordering by day_number works correctly

**Database Verification**:
```sql
SELECT COUNT(*), MIN(day_number), MAX(day_number)
FROM scenario_scenarioprojection
WHERE projection_run_id = <test_run_id>;
```

**Expected**: COUNT matches duration_days, day_number range is 0 to duration_days-1

---

#### Test Case 2.1.3: Batch Pins to ProjectionRun
**Objective**: Verify Batch.pinned_projection_run field works correctly

**Prerequisites**:
- Batch exists
- Multiple ProjectionRuns exist for a scenario

**Steps**:
1. Pin batch to ProjectionRun #1
2. Verify batch.pinned_projection_run points to Run #1
3. Create ProjectionRun #2
4. Verify batch still pinned to Run #1 (unchanged)
5. Manually switch to Run #2
6. Verify batch now pinned to Run #2

**Expected Results**:
- Batch pinning persists correctly
- Re-running projections doesn't change pinned_projection_run
- SET_NULL on delete works (batch.pinned_projection_run becomes null if run deleted)

**Database Verification**:
```sql
SELECT id, batch_number, pinned_projection_run_id, pinned_scenario_id
FROM batch_batch
WHERE id = <test_batch_id>;

SELECT run_id, run_number, scenario_id
FROM scenario_projection_run
WHERE run_id = <pinned_run_id>;
```

---

### 2.2 Service Layer Tests

#### Test Case 2.2.1: ProjectionEngine Creates New Runs
**Objective**: Verify ProjectionEngine.run_projection() creates new runs instead of deleting

**Prerequisites**:
- Scenario with valid models

**Steps**:
1. Run `engine.run_projection(save_results=True, label="Run 1", current_user=user)`
2. Verify Run #1 created with projections
3. Count projections for Run #1
4. Run `engine.run_projection(save_results=True, label="Run 2", current_user=user)`
5. Verify Run #2 created
6. Verify Run #1 still exists with all projections

**Expected Results**:
- First run creates run_number=1
- Second run creates run_number=2
- Both runs have complete projection data
- Run #1 projections unchanged after Run #2 creation
- parameters_snapshot captured for both runs

**Database Verification**:
```sql
SELECT run_id, run_number, total_projections, label, created_by_id
FROM scenario_projection_run
WHERE scenario_id = <test_scenario_id>
ORDER BY run_number;

-- Should show 2 rows with run_number 1 and 2
```

---

#### Test Case 2.2.2: Parameters Snapshot Captured
**Objective**: Verify _capture_parameters_snapshot() stores model data correctly

**Prerequisites**:
- Scenario with TGC value=0.025, FCR values, mortality rate=0.1

**Steps**:
1. Run projections
2. Retrieve ProjectionRun.parameters_snapshot
3. Verify TGC, FCR, mortality data present
4. Verify scenario initial conditions present

**Expected Results**:
```json
{
  "tgc_model": {
    "id": 1,
    "name": "Test TGC",
    "tgc_value": 0.025,
    "exponent_n": 0.33,
    "exponent_m": 0.66,
    "location": "Test Location",
    "release_period": "Spring"
  },
  "fcr_model": {"id": 1, "name": "Test FCR"},
  "mortality_model": {"id": 1, "name": "Low Mortality", "rate": 0.1, "frequency": "daily"},
  "scenario": {
    "initial_weight": 50.0,
    "initial_count": 10000,
    "duration_days": 90
  },
  "captured_at": "2025-11-28T..."
}
```

---

#### Test Case 2.2.3: GrowthAssimilationService Uses Pinned Run
**Objective**: Verify Growth Assimilation prioritizes pinned_projection_run

**Prerequisites**:
- Batch with pinned_projection_run
- Batch also has pinned_scenario (deprecated field)

**Steps**:
1. Call `GrowthAssimilationEngine(assignment)._get_scenario()`
2. Verify it returns projection_run.scenario (not pinned_scenario)
3. Remove pinned_projection_run, keep pinned_scenario
4. Verify it falls back to pinned_scenario with warning log
5. Remove both, add scenario relationship
6. Verify it falls back to first scenario

**Expected Results**:
- Priority order: pinned_projection_run > pinned_scenario > first scenario
- Warning logged when using deprecated pinned_scenario
- ValueError raised if no scenario available

---

### 2.3 API Layer Tests

#### Test Case 2.3.1: List Projection Runs for Scenario
**Endpoint**: `GET /api/v1/scenario/scenarios/{id}/projection_runs/`

**Steps**:
1. Create scenario with 3 projection runs
2. Call endpoint
3. Verify response structure

**Expected Response**:
```json
[
  {
    "run_id": 3,
    "scenario": 1,
    "scenario_name": "Test Scenario",
    "run_number": 3,
    "label": "Latest Run",
    "run_date": "2025-11-28T12:00:00Z",
    "total_projections": 90,
    "final_weight_g": 4500.5,
    "final_biomass_kg": 414000.0,
    "pinned_batch_count": 2,
    "created_by": 1,
    "created_at": "2025-11-28T12:00:00Z"
  },
  ...
]
```

**Assertions**:
- Array ordered by -run_number (newest first)
- pinned_batch_count shows correct count
- All runs for scenario returned

---

#### Test Case 2.3.2: Get Single Projection Run Detail
**Endpoint**: `GET /api/v1/scenario/projection-runs/{id}/`

**Steps**:
1. Get projection run detail
2. Verify parameters_snapshot included
3. Verify notes and created_by_name included

**Expected Response**:
```json
{
  "run_id": 1,
  "scenario": 1,
  "scenario_name": "Test Scenario",
  "run_number": 1,
  "label": "Baseline",
  "run_date": "2025-11-20T10:00:00Z",
  "total_projections": 90,
  "final_weight_g": 4500.0,
  "final_biomass_kg": 414000.0,
  "pinned_batch_count": 5,
  "parameters_snapshot": {
    "tgc_model": {...},
    "fcr_model": {...},
    "mortality_model": {...},
    "scenario": {...}
  },
  "notes": "Initial baseline run",
  "created_by_name": "admin",
  "created_by": 1,
  "created_at": "2025-11-20T10:00:00Z",
  "updated_at": "2025-11-20T10:00:00Z"
}
```

---

#### Test Case 2.3.3: Get Projections for Specific Run
**Endpoint**: `GET /api/v1/scenario/projection-runs/{id}/projections/`

**Steps**:
1. Get projections with `?aggregation=daily`
2. Get projections with `?aggregation=weekly`
3. Get projections with `?aggregation=monthly`

**Expected Results**:
- Daily: All projections returned (90 for 90-day scenario)
- Weekly: Every 7th day (days 0, 7, 14, 21, ...)
- Monthly: Every 30th day (days 0, 30, 60, 90)
- Each projection has all fields: day_number, average_weight, population, biomass, etc.

---

#### Test Case 2.3.4: Pin Projection Run to Batch
**Endpoint**: `POST /api/v1/batch/batches/{id}/pin-projection-run/`

**Request Body**:
```json
{
  "projection_run_id": 123
}
```

**Steps**:
1. Create batch without pinned run
2. Call endpoint with valid run_id
3. Verify response
4. Check database

**Expected Response**:
```json
{
  "success": true,
  "pinned_projection_run_id": 123,
  "scenario_name": "Test Scenario",
  "run_number": 2,
  "run_label": "Updated TGC"
}
```

**Database Verification**:
```sql
SELECT pinned_projection_run_id 
FROM batch_batch 
WHERE id = <batch_id>;
-- Should be 123
```

---

#### Test Case 2.3.5: Run Projection Creates New Run
**Endpoint**: `POST /api/v1/scenario/scenarios/{id}/run_projection/`

**Request Body**:
```json
{
  "label": "Updated TGC Model"
}
```

**Steps**:
1. Check existing run count for scenario
2. Call endpoint
3. Verify new run created
4. Verify old runs preserved

**Expected Response**:
```json
{
  "success": true,
  "projection_run_id": 456,
  "run_number": 3,
  "message": "Projection run #3 created.",
  "summary": {
    "duration_days": 90,
    "final_weight": 4500.5,
    ...
  },
  "warnings": []
}
```

**Database Verification**:
```sql
SELECT COUNT(*) as run_count
FROM scenario_projection_run
WHERE scenario_id = <scenario_id>;
-- Should increment by 1

SELECT COUNT(*) as projection_count
FROM scenario_scenarioprojection
WHERE projection_run_id = <new_run_id>;
-- Should equal duration_days
```

---

### 2.4 Data Migration Tests

#### Test Case 2.4.1: Existing Scenarios Migrated
**Objective**: Verify data migration created ProjectionRuns for existing scenarios

**Steps**:
1. Query scenarios that had projections before migration
2. Verify each has one ProjectionRun with run_number=1
3. Verify all old projections now linked to the run
4. Verify no orphaned projections exist

**Database Verification**:
```sql
-- Check all scenarios with projections got a run
SELECT s.scenario_id, s.name, COUNT(pr.run_id) as run_count
FROM scenario s
LEFT JOIN scenario_projection_run pr ON s.scenario_id = pr.scenario_id
GROUP BY s.scenario_id, s.name
HAVING COUNT(pr.run_id) > 0;

-- Verify no orphaned projections
SELECT COUNT(*) 
FROM scenario_scenarioprojection
WHERE projection_run_id IS NULL;
-- Should be 0

-- Verify projection counts match
SELECT pr.run_id, pr.total_projections, COUNT(sp.projection_id) as actual_count
FROM scenario_projection_run pr
LEFT JOIN scenario_scenarioprojection sp ON pr.run_id = sp.projection_run_id
GROUP BY pr.run_id, pr.total_projections
HAVING pr.total_projections != COUNT(sp.projection_id);
-- Should return 0 rows (all counts match)
```

**Expected**: All scenarios with projections have ProjectionRun, no orphans, counts match

---

#### Test Case 2.4.2: Batch Pinning Migrated
**Objective**: Verify batches with pinned_scenario migrated to pinned_projection_run

**Steps**:
1. Query batches that had pinned_scenario before migration
2. Verify each now has pinned_projection_run pointing to latest run
3. Verify pinned_scenario still set (for backward compatibility)

**Database Verification**:
```sql
SELECT b.id, b.batch_number, b.pinned_scenario_id, b.pinned_projection_run_id,
       pr.scenario_id, pr.run_number
FROM batch_batch b
LEFT JOIN scenario_projection_run pr ON b.pinned_projection_run_id = pr.run_id
WHERE b.pinned_scenario_id IS NOT NULL;

-- Verify pinned_projection_run.scenario matches pinned_scenario
SELECT COUNT(*) as mismatch_count
FROM batch_batch b
INNER JOIN scenario_projection_run pr ON b.pinned_projection_run_id = pr.run_id
WHERE b.pinned_scenario_id != pr.scenario_id 
  AND b.pinned_scenario_id IS NOT NULL;
-- Should be 0
```

**Expected**: All batches with pinned_scenario have matching pinned_projection_run

---

### 2.5 Integration Tests

#### Test Case 2.5.1: Growth Assimilation Uses Correct Run
**Objective**: Verify growth assimilation calculations use pinned_projection_run

**Prerequisites**:
- Batch with pinned_projection_run pointing to Run #1
- Run #2 exists with different TGC values

**Steps**:
1. Trigger growth assimilation calculation
2. Verify it uses Run #1's TGC model (from parameters_snapshot)
3. Create Run #2, verify batch still uses Run #1
4. Switch batch to Run #2
5. Trigger calculation again
6. Verify it now uses Run #2's TGC model

**Expected Results**:
- Calculations use correct TGC model from pinned run
- Re-running scenario projections doesn't affect batch calculations
- Explicit run change updates calculations

---

#### Test Case 2.5.2: Celery Tasks Work with ProjectionRun
**Objective**: Verify async tasks handle ProjectionRun correctly

**Prerequisites**:
- Celery workers running
- Batch with pinned_projection_run

**Steps**:
1. Trigger recompute_assignment_window task
2. Verify task completes without errors
3. Check logs for projection run usage
4. Verify no "No scenario available" errors

**Expected Results**:
- Tasks complete successfully
- Correct scenario retrieved via projection_run
- No regression in task execution

---

### 2.6 Backend Test Suite Results

#### Test Case 2.6.1: Full Backend Test Suite - SQLite
**Command**: `python manage.py test --settings=aquamind.settings_ci`

**Expected Results**:
- **Total Tests**: 1276
- **Passing**: 1276
- **Failing**: 0
- **Skipped**: ~62
- **Duration**: < 120 seconds

**Critical Test Suites**:
- `apps.scenario.tests.api.test_endpoints` - All projection tests pass
- `apps.scenario.tests.api.test_integration` - Workflow tests pass
- `apps.scenario.tests.api.test_projections_aggregation` - All 11 tests pass
- `apps.batch.tests.test_phase*` - Growth assimilation tests pass

---

#### Test Case 2.6.2: Full Backend Test Suite - PostgreSQL
**Command**: `python manage.py test --settings=aquamind.settings_test`

**Expected Results**:
- Same pass rate as SQLite
- TimescaleDB hypertables work correctly
- Foreign key constraints enforced

---

### 2.7 API Schema Validation

#### Test Case 2.7.1: OpenAPI Schema Generation
**Command**: `python manage.py spectacular --file api/openapi.yaml --validate`

**Expected Results**:
- **Errors**: 0
- **Warnings**: ≤ 20
- New endpoints present:
  - `/api/v1/scenario/projection-runs/` (list)
  - `/api/v1/scenario/projection-runs/{id}/` (retrieve)
  - `/api/v1/scenario/projection-runs/{id}/projections/` (projections)
  - `/api/v1/scenario/scenarios/{id}/projection_runs/` (scenario's runs)
  - `/api/v1/batch/batches/{id}/pin-projection-run/` (pin)

**Schema Verification**:
```bash
grep -c "projection-run" api/openapi.yaml
# Should be > 10 (multiple references)

grep "operationId: batch_pin_projection_run" api/openapi.yaml
# Should exist with underscore format
```

---

## 3. Frontend Testing

### 3.1 Component Tests

#### Test Case 3.1.1: ProjectionRunSelector Renders
**Component**: `ProjectionRunSelector.tsx`

**Prerequisites**:
- Scenario with 3 projection runs
- Batch pinned to Run #2

**Steps**:
1. Render component with batchId, scenarioId, currentRunId=2
2. Verify loading state shows while fetching
3. Verify dropdown populated with 3 runs
4. Verify Run #2 is selected
5. Verify "2 batches using this run" text displays (if applicable)

**Expected UI Elements**:
- Label: "Projection Run"
- Info icon with tooltip
- Select dropdown with 3 options: "Run #1", "Run #2", "Run #3"
- Each option shows label (if present) and "X ago" timestamp
- Selected value is "Run #2"

---

#### Test Case 3.1.2: ProjectionRunSelector Changes Run
**Component**: `ProjectionRunSelector.tsx`

**Steps**:
1. Render with current Run #1
2. Click dropdown
3. Select "Run #3"
4. Verify mutation called with projection_run_id=3
5. Verify onRunChange callback called with runId=3
6. Verify toast notification shown
7. Verify data refetches

**Expected Behavior**:
- Dropdown disabled while mutation pending
- Success toast: "Projection run pinned successfully"
- Combined growth data invalidated and refetched
- Chart updates with new projection data

---

#### Test Case 3.1.3: Tooltip Shows Help Text
**Component**: `ProjectionRunSelector.tsx`

**Steps**:
1. Hover over info icon
2. Verify tooltip appears

**Expected Tooltip Text**:
> Each time projections are calculated, a new "run" is created. Switch between runs to compare how projections have changed, or use an older baseline for variance analysis.

---

### 3.2 Integration Tests

#### Test Case 3.2.1: Growth Analysis Tab Shows Selector
**Page**: Batch Details → Analytics Tab → Growth Subtab

**Prerequisites**:
- Batch with pinned_projection_run
- Scenario with 2+ projection runs

**Steps**:
1. Navigate to batch detail page
2. Click Analytics tab
3. Click Growth subtab
4. Verify ProjectionRunSelector appears in left panel
5. Verify current run is selected

**Expected UI**:
- Selector appears in "Scenario" section of DataVisualizationControls
- Below scenario info (name, duration, fish count)
- Above "Refresh Data" button
- Shows current run number and label

---

#### Test Case 3.2.2: Changing Run Updates Chart
**Page**: Batch Details → Analytics → Growth

**Steps**:
1. Note current projection line on chart (green line)
2. Change projection run via selector
3. Wait for data to reload
4. Verify projection line changes
5. Verify variance analysis updates

**Expected Behavior**:
- Loading indicator during refetch
- Chart smoothly updates with new projection data
- Variance calculations reflect new baseline
- No page refresh required

---

#### Test Case 3.2.3: No Runs Available State
**Page**: Batch Details → Analytics → Growth

**Steps**:
1. Pin batch to scenario with no projection runs
2. Navigate to Growth tab

**Expected UI**:
- Selector shows: "No projection runs available. Run projections for this scenario first."
- No dropdown displayed
- Scenario info still shown
- Other controls remain functional

---

### 3.3 Frontend Test Suite

#### Test Case 3.3.1: Unit Tests Pass
**Command**: `npm run test`

**Expected Results**:
- All existing tests continue to pass
- New ProjectionRunSelector tests pass (if added)
- No regression in batch management tests

**Critical Test Files**:
- `GrowthAnalysisTabContent.test.tsx` - Integration tests
- `DataVisualizationControls.test.tsx` - Component tests
- Any new `ProjectionRunSelector.test.tsx`

---

#### Test Case 3.3.2: Type Check Passes
**Command**: `npm run type-check`

**Expected Results**:
- 0 type errors in ProjectionRun-related code
- Existing lib/api.ts errors are pre-existing (not introduced by this feature)
- All interfaces properly typed

---

#### Test Case 3.3.3: Build Succeeds
**Command**: `npm run build`

**Expected Results**:
- Build completes without errors
- No console warnings about ProjectionRun components
- Bundle size increase < 10KB

---

## 4. End-to-End User Acceptance Tests

### UAT-1: Create and Pin Projection Run

**Scenario**: Production Planner wants to establish baseline projections

**Steps**:
1. **Login** as production planner
2. **Navigate** to Scenarios page
3. **Create** scenario: "April 2025 Baseline"
   - Location: Scotland Site 1
   - Duration: 600 days
   - Initial: 100,000 fish @ 50g
   - TGC Model: Scotland April
4. **Run** projections (no label)
5. **Navigate** to Batches page
6. **Select** batch "BATCH-2025-001"
7. **Go to** Analytics → Growth tab
8. **Verify** "Run #1" appears in dropdown
9. **Pin** Run #1 to batch
10. **Verify** toast: "Projection run pinned successfully"
11. **Verify** green projection line appears on chart

**Expected Database State**:
```sql
-- Projection run created
SELECT * FROM scenario_projection_run WHERE scenario_id = <scenario_id>;
-- 1 row, run_number=1, label='', total_projections=600

-- Projections created
SELECT COUNT(*) FROM scenario_scenarioprojection WHERE projection_run_id = <run_id>;
-- 600 rows

-- Batch pinned
SELECT pinned_projection_run_id FROM batch_batch WHERE batch_number = 'BATCH-2025-001';
-- Should equal run_id
```

**Success Criteria**:
- ✅ Scenario created
- ✅ Projections run in < 5 seconds
- ✅ Run #1 created with 600 projections
- ✅ Batch successfully pinned
- ✅ Chart displays projection line
- ✅ No errors in browser console

---

### UAT-2: Update Model and Create New Run

**Scenario**: Biologist wants to test new TGC parameters without affecting production batches

**Steps**:
1. **Login** as biologist
2. **Navigate** to Scenarios page
3. **Open** scenario "April 2025 Baseline" (from UAT-1)
4. **Note**: 3 batches currently pinned to Run #1
5. **Create** new TGC model: "Scotland April v2" (TGC=0.028 instead of 0.025)
6. **Edit** scenario to use new TGC model
7. **Run** projections with label "Updated TGC 2025-11-28"
8. **Verify** Run #2 created
9. **Navigate** to batch "BATCH-2025-001" → Analytics → Growth
10. **Verify** still shows "Run #1" selected
11. **Verify** projection line unchanged
12. **Change** dropdown to "Run #2"
13. **Verify** projection line updates
14. **Compare** old vs new projection visually
15. **Leave** other 2 batches on Run #1

**Expected Database State After**:
```sql
-- Two runs exist
SELECT run_id, run_number, label, final_weight_g
FROM scenario_projection_run
WHERE scenario_id = <scenario_id>
ORDER BY run_number;
-- 2 rows: Run #1 (no label) and Run #2 (Updated TGC 2025-11-28)

-- Run #1 projections unchanged
SELECT COUNT(*), AVG(average_weight) 
FROM scenario_scenarioprojection
WHERE projection_run_id = <run1_id>;
-- Count unchanged, avg_weight unchanged

-- Batch 1 moved to Run #2
SELECT batch_number, pinned_projection_run_id
FROM batch_batch
WHERE batch_number IN ('BATCH-2025-001', 'BATCH-2025-002', 'BATCH-2025-003');
-- BATCH-001: run2_id
-- BATCH-002: run1_id  
-- BATCH-003: run1_id
```

**Success Criteria**:
- ✅ New TGC model created
- ✅ Run #2 created without deleting Run #1
- ✅ Other batches unaffected
- ✅ Selected batch updates only when user chooses
- ✅ Visual comparison possible between runs
- ✅ No data loss

---

### UAT-3: Multiple Iterations and History

**Scenario**: Testing iterative model refinement over weeks

**Steps**:
1. **Week 1**: Create scenario, run projections → Run #1
2. **Week 2**: Update mortality model, run projections with label "Reduced Mortality" → Run #2
3. **Week 3**: Update FCR model, run projections with label "Improved Feed" → Run #3
4. **Week 4**: Revert to Run #1 for one batch
5. **Verify** all 3 runs preserved with correct labels
6. **Navigate** to scenario projection runs list
7. **Verify** run history visible:
   - Run #3: "Improved Feed" - 2 days ago - 2 batches
   - Run #2: "Reduced Mortality" - 9 days ago - 1 batch
   - Run #1: "" - 16 days ago - 1 batch

**Database Verification**:
```sql
SELECT run_id, run_number, label, run_date, 
       total_projections, 
       (SELECT COUNT(*) FROM batch_batch WHERE pinned_projection_run_id = pr.run_id) as pinned_count
FROM scenario_projection_run pr
WHERE scenario_id = <scenario_id>
ORDER BY run_number;

-- All 3 runs exist
-- Each has full projection data
-- Pinned counts sum to total batches using this scenario
```

**Success Criteria**:
- ✅ All runs preserved indefinitely
- ✅ Labels help identify purpose of each run
- ✅ Pinned batch counts accurate
- ✅ Audit trail maintained
- ✅ Comparison between any two runs possible

---

### UAT-4: Error Handling and Edge Cases

#### UAT-4.1: Scenario with No Runs
**Steps**:
1. Create new scenario
2. Navigate to batch → Analytics → Growth
3. Try to pin this scenario's run
4. Verify appropriate error message

**Expected**:
- Selector shows: "No projection runs available. Run projections for this scenario first."
- No crash or console errors

---

#### UAT-4.2: Delete Projection Run
**Steps**:
1. Create Run #1, pin to batch
2. Create Run #2
3. Switch batch to Run #2
4. Delete Run #1 (if deletion allowed)
5. Verify Run #2 still works
6. OR verify deletion prevented if batches still pinned

**Expected**:
- If deletion allowed: Run #1 removed, Run #2 unaffected
- If deletion prevented: Error message about pinned batches
- No orphaned data

---

#### UAT-4.3: Scenario Deletion with Runs
**Steps**:
1. Delete scenario that has projection runs
2. Verify all runs deleted (CASCADE)
3. Verify all projections deleted (CASCADE)
4. Verify batches set pinned_projection_run to null (SET_NULL)

**Expected**:
- Clean cascading deletion
- No orphaned projection runs or projections
- Batches remain but lose pinned run

---

## 5. Performance Tests

### Test Case 5.1: Large Projection Run Performance
**Objective**: Verify performance with 900-day scenarios

**Steps**:
1. Create scenario with duration_days=900
2. Run projections
3. Measure execution time
4. Measure database size impact

**Expected Results**:
- Execution time: < 10 seconds for 900-day projection
- Database rows: 900 projections created
- Bulk insert used (not 900 individual inserts)
- Memory usage reasonable

---

### Test Case 5.2: Multiple Runs Query Performance
**Objective**: Verify listing runs performs well

**Steps**:
1. Create 10 projection runs for same scenario
2. Call `/api/v1/scenario/scenarios/{id}/projection_runs/`
3. Measure response time
4. Check query count

**Expected Results**:
- Response time: < 500ms
- Query count: ≤ 5 queries (with select_related)
- All 10 runs returned
- Ordered by -run_number

---

## 6. Regression Tests

### Test Case 6.1: Existing Features Unaffected

**Critical Paths to Verify**:
- ✅ Scenario creation still works
- ✅ TGC/FCR/Mortality model management works
- ✅ Batch creation and management works
- ✅ Container assignments work
- ✅ Growth samples recording works
- ✅ Feed events recording works
- ✅ Health monitoring works
- ✅ Transfer workflows work

**Test Method**: Run existing test suites and verify no regressions

---

### Test Case 6.2: Backward Compatibility

**Deprecated Fields**:
- `Batch.pinned_scenario` - Should still work but show warning in logs
- `ScenarioProjection.scenario` - Should still exist for migration period

**Steps**:
1. Create batch with pinned_scenario (using old API if available)
2. Verify growth assimilation works
3. Verify warning logged
4. Verify recommendation to use pinned_projection_run

---

## 7. Database Integrity Checks

### Check 7.1: Foreign Key Integrity
```sql
-- Verify all projection_run_id references are valid
SELECT COUNT(*) 
FROM scenario_scenarioprojection sp
LEFT JOIN scenario_projection_run pr ON sp.projection_run_id = pr.run_id
WHERE sp.projection_run_id IS NOT NULL AND pr.run_id IS NULL;
-- Should be 0

-- Verify all pinned_projection_run_id references are valid
SELECT COUNT(*)
FROM batch_batch b
LEFT JOIN scenario_projection_run pr ON b.pinned_projection_run_id = pr.run_id
WHERE b.pinned_projection_run_id IS NOT NULL AND pr.run_id IS NULL;
-- Should be 0
```

---

### Check 7.2: Unique Constraints
```sql
-- Verify (scenario, run_number) is unique
SELECT scenario_id, run_number, COUNT(*)
FROM scenario_projection_run
GROUP BY scenario_id, run_number
HAVING COUNT(*) > 1;
-- Should return 0 rows
```

---

### Check 7.3: Data Consistency
```sql
-- Verify total_projections matches actual count
SELECT pr.run_id, pr.total_projections, COUNT(sp.projection_id) as actual
FROM scenario_projection_run pr
LEFT JOIN scenario_scenarioprojection sp ON pr.run_id = sp.projection_run_id
GROUP BY pr.run_id, pr.total_projections
HAVING pr.total_projections != COUNT(sp.projection_id);
-- Should return 0 rows

-- Verify final metrics match last projection
SELECT pr.run_id, pr.final_weight_g, sp.average_weight,
       pr.final_biomass_kg, sp.biomass
FROM scenario_projection_run pr
INNER JOIN (
  SELECT projection_run_id, MAX(day_number) as max_day
  FROM scenario_scenarioprojection
  GROUP BY projection_run_id
) last ON pr.run_id = last.projection_run_id
INNER JOIN scenario_scenarioprojection sp 
  ON sp.projection_run_id = last.projection_run_id 
  AND sp.day_number = last.max_day
WHERE ABS(pr.final_weight_g - sp.average_weight) > 0.01
   OR ABS(pr.final_biomass_kg - sp.biomass) > 0.01;
-- Should return 0 rows
```

---

## 8. UAT Sign-Off Checklist

### 8.1 Functional Requirements
- [ ] ProjectionRun model implemented and working
- [ ] Migrations completed successfully (145 scenarios, 145 batches)
- [ ] API endpoints functional and properly documented
- [ ] Frontend selector integrated and user-friendly
- [ ] Backward compatibility maintained during transition
- [ ] No data loss during migration

### 8.2 Non-Functional Requirements
- [ ] All 1276 backend tests passing (SQLite)
- [ ] Backend tests passing (PostgreSQL - if environment available)
- [ ] Frontend type-check passes (ProjectionRun code)
- [ ] OpenAPI schema valid (0 errors)
- [ ] Performance acceptable (< 10s for 900-day projections)
- [ ] No memory leaks or resource issues

### 8.3 Documentation
- [ ] data_model.md updated with ProjectionRun tables
- [ ] PRD section 3.3.1 updated with version control feature
- [ ] Implementation plan followed and completed
- [ ] Test plan created and executed

### 8.4 User Experience
- [ ] Selector is intuitive and self-explanatory
- [ ] Tooltips provide helpful guidance
- [ ] No confusion about which run is active
- [ ] Error messages are clear and actionable
- [ ] Performance feels responsive

---

## 9. Known Issues and Limitations

### 9.1 OpenAPI Type Generation
**Issue**: Some endpoints have incorrect TypeScript types in generated client  
**Examples**:
- `run_projection` expects `Scenario` object but actually accepts `{label?: string}`
- `projection_runs` list endpoint returns array but typed as `Scenario`

**Workaround**: Type casting with `as any` or `as unknown as Type`  
**Impact**: Low - functionality works, just type safety bypassed in specific calls  
**Future Fix**: Improve @extend_schema decorators or customize OpenAPI generator

---

### 9.2 Deprecated Fields Remain
**Issue**: `Batch.pinned_scenario` and `ScenarioProjection.scenario` still exist  
**Reason**: Gradual migration, backward compatibility  
**Timeline**: Remove in Phase 2 after all batches migrated and validated  
**Monitoring**: Check logs for warnings about deprecated field usage

---

## 10. Rollback Plan

### If Critical Issues Found

**Step 1**: Stop using frontend selector (comment out import)
**Step 2**: Verify existing batches still work with pinned_projection_run
**Step 3**: If needed, create reverse data migration:
```python
# Revert pinned_projection_run to pinned_scenario
def reverse_migration(apps, schema_editor):
    Batch = apps.get_model('batch', 'Batch')
    for batch in Batch.objects.filter(pinned_projection_run__isnull=False):
        batch.pinned_scenario = batch.pinned_projection_run.scenario
        batch.save()
```

**Step 4**: Drop projection_run column if reverting fully (NOT RECOMMENDED)

---

## 11. Test Execution Log

| Test ID | Description | Status | Date | Tester | Notes |
|---------|-------------|--------|------|--------|-------|
| 2.1.1 | ProjectionRun Creation | ✅ PASS | 2025-11-28 | Auto | CI Suite |
| 2.1.2 | ScenarioProjection FK | ✅ PASS | 2025-11-28 | Auto | CI Suite |
| 2.1.3 | Batch Pinning | ✅ PASS | 2025-11-28 | Auto | CI Suite |
| 2.4.1 | Data Migration | ✅ PASS | 2025-11-28 | Auto | 145/145 migrated |
| 2.4.2 | Batch Migration | ✅ PASS | 2025-11-28 | Auto | 145/145 migrated |
| 2.6.1 | Backend Suite (SQLite) | ✅ PASS | 2025-11-28 | Auto | 1276/1276 tests |
| 2.7.1 | OpenAPI Generation | ✅ PASS | 2025-11-28 | Auto | 0 errors |
| 3.3.2 | Frontend Type Check | ⚠️ PARTIAL | 2025-11-28 | Auto | 4 pre-existing errors in lib/api.ts |
| UAT-1 | Create/Pin Run | ⏳ PENDING | TBD | Manual | - |
| UAT-2 | Update Model | ⏳ PENDING | TBD | Manual | - |
| UAT-3 | Multiple Iterations | ⏳ PENDING | TBD | Manual | - |

---

## 12. Test Data Setup

### Scenario Test Data

```python
# Create test scenario for UAT
from apps.scenario.models import Scenario, TGCModel, FCRModel, MortalityModel
from apps.scenario.services.calculations import ProjectionEngine
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='admin')

# Run projections
engine = ProjectionEngine(scenario)
result = engine.run_projection(save_results=True, label="Test Run", current_user=user)

print(f"Created Run #{result['run_number']} with {result['summary']['duration_days']} projections")
```

### Batch Test Data

```python
# Pin batch to projection run
from apps.batch.models import Batch
from apps.scenario.models import ProjectionRun

batch = Batch.objects.get(batch_number='BATCH-2025-001')
run = ProjectionRun.objects.get(run_id=1)

batch.pinned_projection_run = run
batch.save()

print(f"Pinned {batch.batch_number} to Run #{run.run_number}")
```

---

## 13. Acceptance Criteria Summary

### Must Pass Before UAT Sign-Off

1. ✅ **All backend tests passing** (1276/1276)
2. ✅ **OpenAPI schema valid** (0 errors)
3. ✅ **Data migration successful** (145 scenarios, 145 batches)
4. ✅ **Frontend compiles** without ProjectionRun errors
5. ⏳ **UAT-1 completed** successfully
6. ⏳ **UAT-2 completed** successfully
7. ⏳ **Database integrity checks** pass
8. ⏳ **No console errors** in browser during testing
9. ⏳ **Performance acceptable** (< 10s projection runs)
10. ⏳ **User feedback positive** on selector UX

### Nice to Have

- Frontend unit tests for ProjectionRunSelector component
- E2E Playwright tests for full workflow
- Load testing with 50+ projection runs
- PostgreSQL-specific tests completed

---

## 14. Post-UAT Actions

### If UAT Passes
1. **Remove deprecated fields** in Phase 2:
   - Drop `Batch.pinned_scenario` column
   - Drop `ScenarioProjection.scenario` column (keep only projection_run)
2. **Add frontend comparison UI** for Run #1 vs Run #2
3. **Implement run retention policy** (optional)
4. **Add bulk run operations** (optional)

### If UAT Fails
1. **Document issues** in test execution log
2. **Prioritize** critical vs nice-to-have fixes
3. **Create** bug tickets with reproduction steps
4. **Retest** after fixes applied

---

## 15. Contact and Support

**Feature Owner**: Development Team  
**Test Lead**: QA Team  
**UAT Coordinator**: Product Owner  
**Technical Contact**: Backend/Frontend Developers

**Issue Tracking**: GitHub Issues  
**Documentation**: `aquamind/docs/progress/PROJECTION_RUN_IMPLEMENTATION_PLAN.md`

---

**Test Plan Approval**:
- [ ] Technical Lead
- [ ] QA Lead
- [ ] Product Owner

**UAT Sign-Off**:
- [ ] Production Planner (Scenarios)
- [ ] Farm Operator (Batch Growth Analysis)
- [ ] Biologist (Model Experimentation)

---

*Last Updated: 2025-11-28*  
*Next Review: After UAT Completion*

