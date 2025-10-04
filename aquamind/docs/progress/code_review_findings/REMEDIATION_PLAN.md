# Code Review Findings - Remediation Plan
**Created**: 2025-10-03  
**Status**: Database-Verified Issues  
**Priority Order**: Security → Runtime Errors → Data Integrity → Optimizations

---

## 🔴 CRITICAL PRIORITY (P0) - Security & Breaking Errors

### Task 1: Fix Users App Privilege Escalation Vulnerability ✅ **COMPLETED**
**Issue**: Users can modify their own role, geography, and subsidiary fields, allowing privilege escalation to admin.

**Backend Changes Completed** (2025-10-04):
- [x] Removed `role`, `geography`, `subsidiary` from `UserProfileUpdateSerializer` fields
- [x] Created `UserProfileAdminUpdateSerializer` for admin-only updates with RBAC fields
- [x] Added server-side enforcement in `UserSerializer.update()` to ignore RBAC fields unless requester is staff/superuser
- [x] Added comprehensive validation tests (9 new security tests) ensuring non-admin users cannot modify RBAC fields
- [x] Updated `UserProfileSerializer` to include RBAC fields as read-only for GET requests
- [x] Created admin-only endpoint `/api/v1/users/{id}/admin-update/` for RBAC field updates
- [x] All 43 users app tests passing including new security tests

**Frontend Impact**: 🔴 **BREAKING - REQUIRES CHANGES**
- **Location**: `AquaMind-Frontend/client/src/components/users/` or profile management components
- **Changes Needed**:
  - Remove role, geography, subsidiary from user profile edit forms (fields are now read-only in API)
  - Create separate admin-only user management interface using new `/api/v1/users/{id}/admin-update/` endpoint
  - Update API types/interfaces - RBAC fields removed from `UserProfileUpdateSerializer`
  - Add admin-only routes/components for role management
  - Update permission checks to ensure only admins see role editing UI
- **API Contract Change**:
  - `PUT/PATCH /api/v1/users/profile/` now silently ignores role/geography/subsidiary fields
  - New endpoint available: `PATCH /api/v1/users/{id}/admin-update/` (admin only, requires IsAdminUser permission)
  - `GET /api/v1/users/profile/` now includes RBAC fields for visibility (read-only)


---

### Task 2: Fix MortalityRecord UserAssignmentMixin Conflict ✅ **COMPLETED**
**Issue**: `MortalityRecordViewSet` uses `UserAssignmentMixin` but model has no `user` field, causing TypeError on create.

**Backend Changes Completed** (2025-10-04):
- [x] Removed `UserAssignmentMixin` from `MortalityRecordViewSet`
- [x] Removed conflicting filter overrides that referenced `mortality_date` and `recorded_by` fields
- [x] Updated `filterset_fields` to only include actual model fields: `event_date`, `batch`, `container`, `reason`, `count`
- [x] Fixed `LiceCountViewSet` filters to use actual fields (removed invalid `batch_container_assignment`, `fish_count`, `lice_count`)
- [x] Updated `MortalityRecordSerializer` to mark `container` as optional (`required=False, allow_null=True`)
- [x] Updated `LiceCountSerializer` to mark `container` as optional
- [x] Added 11 comprehensive tests verifying POST/GET operations and filtering
- [x] All tests passing

**Frontend Impact**: 🟡 **MINOR - MAY REQUIRE CHANGES**
- **Location**: Health monitoring/mortality recording components
- **Changes Needed**:
  - If frontend filters by `mortality_date`, change to `event_date`
  - If frontend filters by `recorded_by`, remove that filter (field doesn't exist)
  - Verify create requests don't send `user` field to MortalityRecord endpoint
  - For LiceCount: update filters from `fish_count` to `fish_sampled`
  - Container field now properly optional in both endpoints
- **API Contract Change**:
  - Filter parameter `mortality_date` → `event_date` for mortality records
  - Filter parameter `recorded_by` removed from mortality records
  - LiceCount filters updated to use actual fields (`fish_sampled`, individual count fields)
  - Container field properly optional in create requests

---

### Task 3: Fix PhotoperiodData Missing Database Columns ✅ **COMPLETED**
**Issue**: API serializer defines `artificial_light_start`, `artificial_light_end`, and `notes` fields that don't exist in database.

**Backend Changes Completed** (2025-10-04):
- [x] Remove `artificial_light_start`, `artificial_light_end`, `notes` from `PhotoperiodDataSerializer` (lines 227-243 in `apps/environmental/api/serializers.py`)
- [x] Update API documentation/OpenAPI spec
- [x] Verify no business logic depends on these fields
- [x] Added comprehensive regression tests in `test_photoperiod_api.py` (9 tests) to prevent future serializer/model drift
- [x] All 831 tests passing including new PhotoperiodData API tests

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- **Location**: Environmental data management, photoperiod forms
- **Changes Needed**:
  - **Confirmed**: No UI for artificial light times and notes exists in frontend - fields were phantom API fields only
- **API Contract Change**:
  - **Breaking but safe**: Fields removed from API responses and requests - no frontend impact since fields were never used

---


## 🟠 HIGH PRIORITY (P1) - Runtime Errors

### Task 4: Fix Broodstock Service timezone.timedelta Error ✅ **COMPLETED**
**Issue**: Using `timezone.timedelta` instead of `datetime.timedelta`, causing AttributeError.

**Backend Changes Completed** (2025-10-04):
- [x] Added `from datetime import timedelta` import to `apps/broodstock/services/broodstock_service.py`
- [x] Line 324: Changed `timezone.timedelta(days=30)` to `timedelta(days=30)` in `get_container_statistics`
- [x] Line 444: Changed `timezone.timedelta(days=7)` to `timedelta(days=7)` in `check_container_maintenance_due`
- [x] Ran existing test: `pytest apps/broodstock/tests/test_services.py::BroodstockServiceTestCase::test_get_container_statistics` (PASSED)
- [x] Verified maintenance due checks work (test passed)
- [x] All 831 tests still passing

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- These are internal service methods
- No API contract changes
- Frontend continues to call existing endpoints

---

### Task 5: Fix Batch Analytics References to Removed Fields ✅ **COMPLETED**
**Issue**: Analytics code references `batch.population_count` and `batch.biomass_kg` which don't exist as direct fields.

**Backend Changes Completed** (2025-10-04):
- [x] Fixed `BatchAnalyticsMixin.performance_metrics()` to use `batch.calculated_population_count`, `batch.calculated_biomass_kg`, `batch.calculated_avg_weight_g`
- [x] Fixed `_calculate_mortality_metrics()` to use `batch.calculated_population_count`
- [x] Fixed `_calculate_container_metrics()` to use `batch.batch_assignments` (correct related name)
- [x] Updated `BatchViewSet` queryset with annotations for `_calculated_population_count`, `_calculated_biomass_kg`, `_calculated_avg_weight_g`
- [x] Updated `BatchFilter` to use annotated fields for `biomass_min`, `biomass_max`, `population_min`, `population_max` filters
- [x] Added comprehensive regression tests for all analytics endpoints (performance_metrics, growth_analysis, compare)
- [x] Verified edge case: batches with no assignments return correct calculated values (population=0, biomass=0.00)
- [x] All analytics tests passing

**Frontend Impact**: 🟡 **MINOR - FILTER UPDATES**
- **Location**: Batch list/table views, analytics dashboards
- **Changes Needed**:
  - Review any filters that use `biomass_min`, `biomass_max`, `population_min`, `population_max`
  - If backend removes these filters, update frontend filter UI accordingly
  - Verify batch analytics charts/displays still work after backend fixes
  - No data model changes on frontend (still receiving same data structure)
- **API Contract Change**:
  - Filter parameters may be removed or renamed
  - Response data structure unchanged

---

### Task 6: Fix EnvironmentalParameter Precision Mismatch ✅ **COMPLETED**
**Issue**: Serializer accepts 4 decimal places but database only stores 2, causing data loss.

**Backend Changes Completed** (2025-10-04):
- [x] Changed `decimal_places=4` to `decimal_places=2` in `EnvironmentalParameterSerializer` for `min_value`, `max_value`, `optimal_min`, and `optimal_max` fields (lines 38-65 in `apps/environmental/api/serializers.py`)
- [x] Added comprehensive `test_decimal_precision_validation()` method with 8 test cases validating rejection of values with >2 decimal places and acceptance of valid 2-decimal values
- [x] All 8 environmental parameter API tests passing including new precision validation tests
- [x] All 37 environmental API tests passing (no regressions introduced)
- [x] Verified database model already correctly defines `decimal_places=2` for all fields
- [x] No documentation updates needed (data model and PRD don't specify precision details)

**Frontend Impact**: 🟡 **VALIDATION UPDATES**
- **Location**: Environmental parameter forms, parameter configuration
- **Changes Needed**:
  - **Check**: Update form validation to allow max 2 decimal places (e.g., step="0.01" in inputs)
  - Update number input components and formatters
  - Add client-side validation messages for decimal precision
- **API Contract Change**:
  - **Check**: Server will reject values with >2 decimal places
  
---

### Task 7: Fix Health LiceCount & Treatment Filtering ✅ **COMPLETED**
**Issue**: Filters reference non-existent fields or properties causing FieldError.

**Backend Changes Completed** (2025-10-04):
- [x] **LiceCountViewSet**: Filters already correct - uses `batch`, `container`, `user`, `count_date`, `fish_sampled`, `adult_female_count`, `adult_male_count`, `juvenile_count` (no invalid fields present)
- [x] **TreatmentViewSet**: Removed custom `filter_queryset` method that handled `withholding_end_date` filtering (property, not field)
- [x] Added comprehensive `TreatmentViewSetFixTest` class with 5 integration tests:
  - `test_create_treatment`: Basic treatment creation
  - `test_filter_by_batch`: Batch filtering
  - `test_filter_by_treatment_type`: Treatment type filtering
  - `test_filter_by_withholding_period_days`: Withholding period filtering (actual field)
  - `test_withholding_end_date_filter_removed`: Verifies withholding_end_date filter ignored
- [x] Regenerated OpenAPI specification to reflect filter changes
- [x] All 101 health app tests passing including new tests

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- **Confirmed**: LiceCountViewSet filters were already correct (no invalid fields to remove)
- **Confirmed**: TreatmentViewSet withholding_end_date was never exposed as a filter parameter in API
- **API Contract Change**:
  - No breaking changes - filters that were working remain working
  - No invalid filter parameters were exposed to frontend

---

### Task 8: Fix Growth Sample Validation ✅ **COMPLETED**
**Issue**: `GrowthSampleSerializer` validation methods called with incorrect arguments.

**Backend Changes Completed** (2025-10-04):
- [x] Fixed `validate_individual_measurements` call in `GrowthSampleSerializer.validate()` - was passing 2 args but function expects 3 (added `sample_size` as first argument)
- [x] Fixed `validate_min_max_weight` call - was passing 3 args but function expects 2 (removed extra `avg_weight_g` argument)
- [x] Updated validation functions to raise `ValidationError` instead of returning error dictionaries for consistent DRF error handling
- [x] Created comprehensive unit tests (`test_growth_sample_serializer.py`) with 18 test cases covering:
  - Valid measurement-based and manual weight entry scenarios
  - Invalid sample size mismatches, weight/length mismatches, min/max weight validation
  - Population size validation, serialization with assignment details
  - Condition factor calculation, large measurement lists, update operations
- [x] All 18 new tests passing, all 123 batch app tests still passing (no regressions)

**Frontend Impact**: 🟢 **IMPROVED ERROR HANDLING**
- **Location**: Growth sampling forms, batch weighing interfaces
- **Changes Needed**:
  - Validation errors will now be properly formatted
  - Update error display components to handle standardized ValidationError format
  - Test create/update growth sample forms to ensure errors display correctly
- **API Contract Change**:
  - Error response format becomes consistent (always JSON with field keys)
  - Previously inconsistent error formats now standardized

---

## 🟡 MEDIUM PRIORITY (P2) - Data Integrity

### Task 9: Fix WeatherData Serializer Field Coverage ✅ **COMPLETED**
**Issue**: Serializer may omit `wave_period` field and have incorrect precision for `wind_speed`/`precipitation`.

**Backend Changes Completed** (2025-10-04):
- [x] Verify `wave_period` is included in `WeatherDataSerializer` and `WeatherDataCreateSerializer`
- [x] Update `wind_speed` and `precipitation` to `max_digits=6` (previously 5)
- [x] Add explicit `wave_period` field declaration in `WeatherDataSerializer` for clarity
- [x] Add field coverage tests comparing serializer fields to model fields (4 new tests)
- [x] Test round-trip data preservation with comprehensive validation
- [x] All 15 weather API tests passing including new field coverage and precision tests

**Frontend Impact**: 🟡 **FIELD AVAILABILITY**
- **Location**: Weather data forms, environmental monitoring dashboards
- **Changes Needed**:
  - Add `wave_period` field to weather data forms if missing
  - Update validation for wind_speed/precipitation to allow larger values
  - Verify weather data tables display all available fields
- **API Contract Change**:
  - `wave_period` field now available in responses (was previously missing)
  - Larger values accepted for wind_speed and precipitation

---

### Task 10: Fix BatchFeedingSummary Field Names
**Issue**: `generate_for_batch` tries to write to non-existent fields causing FieldError.

**Backend Changes Completed** (2025-10-04):
- [ ] Locate `BatchFeedingSummary.generate_for_batch()` method
- [ ] Replace field names:
  - `average_biomass_kg` → `total_starting_biomass_kg` or appropriate field
  - `growth_kg` → `total_growth_kg`
  - `average_biomass` → use appropriate field from DB schema
- [ ] Verify all 17 columns in DB schema are properly mapped
- [ ] Add regression test for summary generation
- [ ] Test with various batch configurations

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- Internal batch analytics method
- Frontend consumes completed summaries via API
- No API contract changes to consumption endpoints

---

### Task 11: Fix Assignment & Transfer Workflows
**Issue**: Transfer operations can drive counts negative, validation bypassed for calculated fields.

**Backend Changes Completed** (2025-10-04):
- [ ] Update transfer logic to clamp population_count at zero
- [ ] Feed computed biomass_kg into `validate_container_capacity`
- [ ] Add transaction rollback on validation failures
- [ ] Add tests for:
  - Mortality exceeding population
  - Over-transfer scenarios
  - Mixed-batch compositions
  - Negative population prevention
- [ ] Add logging for unexpected negative populations

**Frontend Impact**: 🟡 **ERROR HANDLING**
- **Location**: Transfer forms, assignment management, mortality recording
- **Changes Needed**:
  - Better error messages for capacity violations
  - Validation feedback before submitting transfers
  - Real-time capacity calculations in UI
  - Warning when attempting to transfer more than available
- **API Contract Change**:
  - More validation errors returned (400 status)
  - Descriptive error messages for constraint violations

---

### Task 12: Fix Broodstock Egg Production Actions
**Issue**: View actions bypass domain service validation for egg production.

**Backend Changes Completed** (2025-10-04):
- [ ] Refactor `produce_internal` and `acquire_external` actions in `apps/broodstock/views.py`
- [ ] Delegate to `EggManagementService.produce_internal_eggs()` and `.acquire_external_eggs()`
- [ ] Ensure all validations run:
  - Inactive plans blocked
  - Unhealthy broodstock rejected
  - Duplicate supplier batches prevented
  - `BreedingPair.progeny_count` properly updated
- [ ] Wrap in `transaction.atomic()`
- [ ] Reuse `EggManagementService.generate_egg_batch_id()` for uniqueness
- [ ] Add integration tests for actions

**Frontend Impact**: 🟢 **IMPROVED RELIABILITY**
- **Location**: Broodstock management, egg production forms
- **Changes Needed**:
  - No breaking changes
  - Better error messages for validation failures
  - Verify egg production forms handle new validation errors gracefully
- **API Contract Change**:
  - More comprehensive validation (may reject previously accepted requests)
  - Consistent egg_batch_id format

---

### Task 13: Fix Broodstock Container Validation
**Issue**: Container validation uses fragile substring matching instead of category/type checks.

**Backend Changes Completed** (2025-10-04):
- [ ] Update `BroodstockFishSerializer.validate_container()` (line 24 in `apps/broodstock/serializers.py`)
- [ ] Replace `'broodstock' in container_type.name.lower()` with proper category check
- [ ] Coordinate with infrastructure team on container categorization
- [ ] Options:
  - Check `container_type.category` field
  - Use boolean flag on container type
  - Whitelist specific category enum values
- [ ] Add tests with various container type names

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- Internal validation logic improvement
- Same API behavior (reject invalid containers)
- May accept more valid containers that were previously rejected due to naming

---

### Task 14: Fix HealthSamplingEvent Aggregation
**Issue**: Aggregate metrics calculation bypassed during POST, test-specific branches in production code.

**Backend Changes Completed** (2025-10-04):
- [ ] Convert `individual_fish_observations` to nested serializer in `HealthSamplingEventSerializer`
- [ ] Validate parameter IDs eagerly
- [ ] Remove test-specific branches from `calculate_aggregate_metrics()` (e.g., `sorted(weights) == [...]`)
- [ ] Ensure `calculate_aggregate_metrics` is called after creation
- [ ] Backfill missing metrics with management command
- [ ] Add serializer tests for aggregation workflow

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- Backend fix ensures correct calculation
- Frontend continues to display aggregate metrics
- No API contract changes

---

### Task 15: Fix HealthLabSample Assignment Validation
**Issue**: Validation ignores departure_date, inconsistent error formats.

**Backend Changes Completed** (2025-10-04):
- [ ] Add `departure_date` upper bound check in lab sample validation
- [ ] Standardize all `ValidationError` payloads to consistent format
- [ ] Expand tests for historical assignment edge cases
- [ ] Reject samples for assignments that have ended

**Frontend Impact**: 🟢 **IMPROVED ERROR MESSAGES**
- **Location**: Lab sample collection forms
- **Changes Needed**:
  - Consistent error message display
  - May see new validation errors for ended assignments
- **API Contract Change**:
  - Consistent error response format
  - Additional validation constraint (departed assignments rejected)

---

## 🔵 LOW PRIORITY (P3) - Optimizations & Code Quality

### Task 16: Fix Scenario CSV Import Services
**Issue**: Only temperature handlers exist; FCR/mortality import methods missing.

**Backend Changes Completed** (2025-10-04):
- [ ] Implement `BulkDataImportService.import_fcr_data()`
- [ ] Implement `BulkDataImportService.import_mortality_data()`
- [ ] Mirror temperature flow pattern
- [ ] Add CSV format validation
- [ ] Add tests for each import type

**Frontend Impact**: 🟡 **NEW FUNCTIONALITY**
- **Location**: Data import interfaces, CSV upload forms
- **Changes Needed**:
  - Enable FCR and mortality CSV upload options (currently may be disabled/hidden)
  - Update data type selectors
  - Add format help text for each CSV type
- **API Contract Change**:
  - Endpoints that previously returned 500 will now work

---

### Task 17: Fix Scenario Projection Engine Null Weight Handling
**Issue**: Projection fails when initial_weight is null.

**Backend Changes Completed** (2025-10-04):
- [ ] Add validation in `ProjectionEngine.run_projection()`
- [ ] Either enforce non-null weights before projection or supply default
- [ ] Update serializer to require initial_weight OR provide default
- [ ] Add error message explaining weight requirement
- [ ] Test projection with various weight scenarios

**Frontend Impact**: 🟡 **VALIDATION UPDATES**
- **Location**: Scenario creation/editing forms
- **Changes Needed**:
  - Make initial_weight a required field in scenario forms
  - Add client-side validation
  - Provide helpful error messages
  - Consider adding a "typical weight" helper/suggestion
- **API Contract Change**:
  - Scenario creation may reject null initial_weight
  - Better error messages for projection failures

---

### Task 18: Fix Scenario Projections Aggregation Endpoint
**Issue**: Uses invalid `day_number__mod` lookup and returns non-serializable queryset.

**Backend Changes Completed** (2025-10-04):
- [ ] Replace `day_number__mod` with Django `Mod()` function or `TruncWeek`/`TruncMonth`
- [ ] Keep queryset as instances for serializer compatibility
- [ ] Use `ExpressionWrapper` for custom aggregations
- [ ] Add tests for weekly/monthly aggregation endpoints
- [ ] Verify serialization works correctly

**Frontend Impact**: 🟢 **NO CHANGES IF UNUSED**
- **Location**: Scenario projection charts, aggregation views
- **Changes Needed**:
  - If frontend uses weekly/monthly aggregation, verify charts still render
  - Data structure should be unchanged after fix
- **API Contract Change**:
  - Endpoints that returned 500 will now return proper data

---

### Task 19: Fix Scenario Model Change Scheduling
**Issue**: Allows change_day=0, causing changes to apply before simulation starts.

**Backend Changes Completed** (2025-10-04):
- [ ] Update `ScenarioModelChange.clean()` to enforce `change_day >= 1`
- [ ] Update serializer validation
- [ ] Fix scheduling math to use consistent indexing
- [ ] Add validation tests for boundary conditions
- [ ] Test with change_day = 0, 1, last day of simulation

**Frontend Impact**: 🟡 **VALIDATION UPDATES**
- **Location**: Scenario model change forms, simulation configuration
- **Changes Needed**:
  - Update day number input min value to 1
  - Show validation error for day 0
  - Update help text: "Day 1 is the first day of simulation"
- **API Contract Change**:
  - change_day=0 will be rejected with validation error

---

### Task 20: Optimize Environmental Reading Queries
**Issue**: "Recent" actions use N+1 query loops.

**Backend Changes Completed** (2025-10-04):
- [ ] Replace iteration with window functions or `Subquery` with `OuterRef`
- [ ] Use `distinct on` for PostgreSQL
- [ ] Add `select_related`/`prefetch_related` where applicable
- [ ] Benchmark query performance before/after
- [ ] Add tests to verify sort order maintained

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- Performance improvement only
- Faster API responses
- No contract changes

---

### Task 21: Consolidate Environmental Viewset Duplication
**Issue**: Two implementations in `views.py` and `api/viewsets.py` with overlapping logic.

**Backend Changes Completed** (2025-10-04):
- [ ] Audit both implementations for differences
- [ ] Consolidate into single implementation (prefer `api/viewsets.py`)
- [ ] Extract shared logic into mixins
- [ ] Update URL routing
- [ ] Add smoke tests for both router paths before consolidation
- [ ] Ensure no breaking changes to API endpoints

**Frontend Impact**: 🟢 **NO CHANGES NEEDED**
- URL endpoints should remain the same
- API contract unchanged
- Internal refactoring only

---

## 📊 Summary Statistics

| Priority | Count | Total Estimated Effort |
|----------|-------|------------------------|
| P0 (Critical) | 3 tasks | Backend: 7h, Frontend: 6-9h, Testing: 5h |
| P1 (High) | 5 tasks | Backend: 11.5h, Frontend: 5.5-7h, Testing: 7h |
| P2 (Medium) | 7 tasks | Backend: 18.5h, Frontend: 6.5h, Testing: 13.5h |
| P3 (Low) | 5 tasks | Backend: 16h, Frontend: 4.5-5h, Testing: 7h |
| **Total** | **21 tasks** | **Backend: 53h, Frontend: 22.5-27.5h, Testing: 32.5h** |

**Grand Total**: Approximately 108-113 hours of work

---

## 🚀 Recommended Execution Order

### Phase 1: Critical Security & Breakage 
1. Task 1 - Users privilege escalation (Security)
2. Task 2 - MortalityRecord mixin conflict
3. Task 3 - PhotoperiodData missing columns
4. Task 4 - Broodstock timedelta error

### Phase 2: Runtime Errors 
5. Task 5 - Batch analytics field references
6. Task 6 - EnvironmentalParameter precision
7. Task 7 - Health filtering issues
8. Task 8 - Growth sample validation

### Phase 3: Data Integrity 
9. Task 9 - WeatherData field coverage
10. Task 10 - BatchFeedingSummary fields
11. Task 11 - Assignment & transfer workflows
12. Task 12 - Broodstock egg production
13. Task 13 - Broodstock container validation
14. Task 14 - HealthSamplingEvent aggregation
15. Task 15 - HealthLabSample validation

### Phase 4: Optimizations 
16. Task 16 - Scenario CSV imports
17. Task 17 - Scenario projection null weights
18. Task 18 - Scenario projections aggregation
19. Task 19 - Scenario model change scheduling
20. Task 20 - Environmental query optimization
21. Task 21 - Environmental viewset consolidation

---

## 📝 Notes for Implementation

1. **Frontend Coordination**: Many tasks require frontend updates. Coordinate API contract changes before deployment.

2. **Database Migrations**: Tasks 3 (Option B), 6 (Option B) require migrations. Test thoroughly in dev/staging.

3. **Breaking Changes**: Tasks 1, 2, 5, 7 involve breaking API changes. Version or phase deployment.

4. **Testing**: Each task should include unit tests, integration tests, and manual verification.

5. **Documentation**: Update OpenAPI specs after each API contract change.

6. **Rollback Plans**: For each deployment, prepare rollback strategy especially for migration-related tasks.

---

## 🔄 API Versioning Strategy

### Overview
Several tasks involve breaking changes that require careful API version management to avoid breaking existing frontend/mobile clients.

### Breaking Changes Identified
| Task | Endpoint | Breaking Change | Impact |
|------|----------|----------------|--------|
| Task 1 | `PUT/PATCH /api/v1/users/profile/` | Rejects role/geography/subsidiary | Existing update requests will fail validation |
| Task 2 | `GET/POST /api/v1/health/mortality-records/` | Filter param changes | Queries using old param names return errors |
| Task 5 | `GET /api/v1/batch/batches/` | Removed filters | Population/biomass filters no longer available |
| Task 7 | `GET /api/v1/health/lice-counts/`, `/treatments/` | Removed filters | Invalid filter params return 400 |

### Recommended Approach: Phased Deprecation

**Phase 1: Soft Deprecation**
```python
# Add deprecation warnings without breaking existing code
from rest_framework.response import Response
from warnings import warn

class UserProfileView(generics.RetrieveUpdateAPIView):
    def update(self, request, *args, **kwargs):
        # Warn if deprecated fields are used
        deprecated_fields = ['role', 'geography', 'subsidiary']
        used_deprecated = [f for f in deprecated_fields if f in request.data]
        
        if used_deprecated:
            # Log warning
            logger.warning(
                f"Deprecated fields used in profile update: {used_deprecated}",
                extra={'user': request.user.id, 'fields': used_deprecated}
            )
            # Add deprecation header
            response = super().update(request, *args, **kwargs)
            response['Warning'] = f'299 - "Fields {used_deprecated} are deprecated and will be removed in v2"'
            # Remove deprecated fields from data (don't apply them)
            for field in used_deprecated:
                request.data.pop(field, None)
            return response
        
        return super().update(request, *args, **kwargs)
```

**Phase 2: Hard Break with Clear Errors**
```python
def update(self, request, *args, **kwargs):
    deprecated_fields = ['role', 'geography', 'subsidiary']
    used_deprecated = [f for f in deprecated_fields if f in request.data]
    
    if used_deprecated:
        raise ValidationError({
            'error': 'deprecated_fields',
            'message': 'Role management has moved to admin-only endpoint',
            'deprecated_fields': used_deprecated,
            'new_endpoint': '/api/v1/users/{id}/admin-update/ (admin only)',
            'migration_guide': 'https://docs.aquamind.io/api-migration-v2'
        })
    
    return super().update(request, *args, **kwargs)
```

### Filter Parameter Migration
```python
# For Tasks 2, 5, 7 - Map old params to new params temporarily
class MortalityRecordFilter(FilterSet):
    # Support both old and new param names during transition
    mortality_date = DateTimeFilter(
        field_name='event_date',
        help_text='DEPRECATED: Use event_date instead'
    )
    event_date = DateTimeFilter()
    
    def filter_queryset(self, queryset):
        # Warn if old param used
        if 'mortality_date' in self.data:
            logger.warning('Deprecated filter param: mortality_date')
        return super().filter_queryset(queryset)
```

### Version Headers (Optional)
```python
# Middleware to track API version usage
class APIVersionMiddleware:
    def __call__(self, request):
        api_version = request.headers.get('X-API-Version', '1.0')
        request.api_version = api_version
        response = self.get_response(request)
        response['X-API-Version'] = api_version
        return response
```

---

## 🔙 Rollback Procedures

### Task 1: Users Privilege Escalation Fix

**Rollback Scenario**: Fix breaks legitimate admin user management workflows

**Pre-Deployment Backup**:
```bash
# Backup serializer
cp apps/users/serializers.py apps/users/serializers.py.backup

# Tag current state
git tag pre-task-1-$(date +%Y%m%d)
git push origin pre-task-1-$(date +%Y%m%d)
```

**Rollback Steps**:
```bash
# 1. Revert code changes
git revert <commit-hash>

# 2. Redeploy backend
git push origin main
# Trigger deployment pipeline

# 3. No database changes to revert

# 4. Verify
curl -X PATCH $API_URL/api/v1/users/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"role": "ADMIN"}' # Should work again (BAD but functional)
```

**Post-Rollback Action**: Fix the fix - add admin-only endpoint before re-attempting.

---

### Task 2: MortalityRecord Mixin Removal

**Rollback Scenario**: Other functionality depends on the mixin pattern

**Pre-Deployment**:
```bash
# Backup viewset
cp apps/health/api/viewsets/mortality.py apps/health/api/viewsets/mortality.py.backup

# Document current filters
curl $API_URL/api/v1/health/mortality-records/?mortality_date=2025-10-01 > pre-rollback-test.json
```

**Rollback Steps**:
```bash
# 1. Restore file
cp apps/health/api/viewsets/mortality.py.backup apps/health/api/viewsets/mortality.py

# 2. Commit and deploy
git add apps/health/api/viewsets/mortality.py
git commit -m "Rollback Task 2: Restore UserAssignmentMixin"
git push origin main

# 3. Verify old behavior restored (will fail but consistently)
curl -X POST $API_URL/api/v1/health/mortality-records/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch": 1, "count": 5, "reason": 1}'
# Should return TypeError (known bad state)
```

---

### Task 5: Batch Analytics Field References

**Rollback Scenario**: Analytics break in unexpected ways

**Pre-Deployment Testing**:
```bash
# Test all analytics endpoints before deployment
endpoints=(
  "/api/v1/batch/batches/1/performance_metrics/"
  "/api/v1/batch/batches/1/growth_analysis/"
  "/api/v1/batch/batches/compare/?batch_ids=1,2"
)

for endpoint in "${endpoints[@]}"; do
  curl -X GET "$API_URL$endpoint" -H "Authorization: Bearer $TOKEN" \
    > "pre_deploy_${endpoint//\//_}.json"
done
```

**Rollback Steps**:
```bash
# 1. Identify all changed files
git diff HEAD~1 --name-only | grep batch

# 2. Revert all batch changes
git revert <commit-hash>

# 3. Verify analytics work again (even if with errors)
for endpoint in "${endpoints[@]}"; do
  curl -X GET "$API_URL$endpoint" -H "Authorization: Bearer $TOKEN"
done

# 4. Re-deploy
git push origin main
```

**Investigation Required**: If rollback needed, analytics were using calculated properties correctly elsewhere. Find those usages before re-attempting.

---

### Task 6: EnvironmentalParameter Precision (Option B - With Migration)

**Rollback Scenario**: Precision change affects existing calculations or queries

**Pre-Migration Data Audit**:
```sql
-- Record all values with >2 decimal places (shouldn't exist but verify)
SELECT id, name, min_value, max_value, optimal_min, optimal_max
FROM environmental_environmentalparameter
WHERE min_value::text ~ '\.\d{3,}'
   OR max_value::text ~ '\.\d{3,}'
   OR optimal_min::text ~ '\.\d{3,}'
   OR optimal_max::text ~ '\.\d{3,}';
-- Should return 0 rows

-- Export full table
COPY environmental_environmentalparameter TO '/tmp/env_params_backup.csv' CSV HEADER;
```

**Rollback Steps**:
```bash
# 1. Rollback migration
python manage.py migrate environmental <previous_migration_number>

# 2. Verify precision back to 2
psql -h $DB_HOST -U $DB_USER -d aquamind -c "
  SELECT column_name, numeric_precision, numeric_scale
  FROM information_schema.columns
  WHERE table_name = 'environmental_environmentalparameter'
  AND data_type = 'numeric';"
# Should show scale = 2

# 3. Restore data if needed (unlikely unless data corruption)
# Only if data was affected:
psql -h $DB_HOST -U $DB_USER -d aquamind -c "
  TRUNCATE environmental_environmentalparameter CASCADE;
  \copy environmental_environmentalparameter FROM '/tmp/env_params_backup.csv' CSV HEADER"

# 4. Revert code
git revert <commit-hash>
git push origin main
```

---

### Task 11: Assignment & Transfer Workflows

**Rollback Scenario**: Transfer validation is too strict, blocking legitimate operations

**Pre-Deployment**:
```bash
# Test transfer scenarios
python manage.py shell << EOF
from apps.batch.models import BatchTransfer, BatchContainerAssignment
# Record current state
print("Active assignments:", BatchContainerAssignment.objects.filter(is_active=True).count())
print("Recent transfers:", BatchTransfer.objects.filter(transfer_date__gte=date.today()-timedelta(days=7)).count())
EOF
```

**Rollback Steps**:
```bash
# 1. Revert validation changes
git revert <commit-hash>

# 2. Check for any transfers that failed during deployment
psql -h $DB_HOST -U $DB_USER -d aquamind << EOF
-- Look for assignments with negative populations (shouldn't exist but check)
SELECT id, batch_id, container_id, population_count, biomass_kg
FROM batch_batchcontainerassignment
WHERE population_count < 0;
EOF

# 3. Fix any negative populations manually
UPDATE batch_batchcontainerassignment 
SET population_count = 0, biomass_kg = 0 
WHERE population_count < 0;

# 4. Redeploy
git push origin main
```

**Data Cleanup Required**: If negative populations found, investigate recent transfers and mortality events.