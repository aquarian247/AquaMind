# Scenario Integration Tests TODO for API Consolidation

This document outlines the specific issues with scenario integration tests discovered during Phase 2b of the QA Improvement project. These tests are currently skipped pending API consolidation due to namespace issues and other router configuration problems.

## Context

During Phase 2b of the QA Improvement project, we implemented comprehensive tests for the scenario app, achieving 59% coverage. However, 7 integration tests had to be skipped due to API namespace issues. These tests expect URL patterns using `reverse('api:scenario-...')` but fail because the router doesn't define an 'api' namespace.

## Skipped Integration Tests

The following 7 tests in `apps/scenario/tests/test_integration.py` are skipped with `@unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")`:

1. **`test_create_scenario_from_scratch`**
   - Tests creating a scenario and running a projection
   - Fails on: `reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk})`

2. **`test_compare_multiple_scenarios`**
   - Tests comparing multiple scenarios side by side
   - Fails on: `reverse('api:scenario-compare', kwargs={'pk': scenario1.pk})`

3. **`test_sensitivity_analysis`**
   - Tests sensitivity analysis by varying TGC values
   - Fails on: `reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk})`

4. **`test_export_data`**
   - Tests exporting scenario data to CSV
   - Fails on: `reverse('api:scenario-export', kwargs={'pk': scenario.pk})`

5. **`test_chart_data_generation`**
   - Tests generating chart data for scenarios
   - Fails on: `reverse('api:scenario-chart-data', kwargs={'pk': scenario.pk})`

6. **`test_model_changes_mid_scenario`**
   - Tests applying model changes mid-scenario
   - Fails on: `reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk})`

7. **`test_temperature_profile_upload`**
   - Tests uploading temperature profile data
   - Fails on: `reverse('api:temperature-profile-upload', kwargs={'pk': new_profile.pk})`

## API Namespace Issues

The core issue is that the tests expect an 'api' namespace for URL reversing, but this namespace doesn't exist in the current URL configuration. The error is:

```
django.urls.exceptions.NoReverseMatch: 'api' is not a registered namespace
```

This highlights a broader inconsistency in how API endpoints are registered and accessed across the project.

## Router Registration Problems

The API Structure Analysis Report identified several issues with router registration:

1. **Double Registration**: The main router in `aquamind/api/router.py` uses a problematic dual approach:

```python
# First, it extends the registry
router.registry.extend(batch_router.registry)
router.registry.extend(environmental_router.registry)
# ... other apps

# Then it also includes them explicitly
path('environmental/', include((environmental_router.urls, 'environmental'))),
path('batch/', include((batch_router.urls, 'batch'))),
# ... other apps
```

2. **Inconsistent Namespace Usage**: Some app routers have namespaces, others don't.

3. **Inconsistent URL Construction**: Some tests use `reverse()` with namespaces, others use direct string construction.

## Recommended Solutions

### Option A: Add 'api' Namespace (Preferred)

1. Modify the main router configuration to include the 'api' namespace:

```python
# aquamind/api/router.py
urlpatterns = [
    # App-specific API endpoints with consistent namespacing
    path('batch/', include((batch_router.urls, 'batch'), namespace='api')),
    path('broodstock/', include((broodstock_router.urls, 'broodstock'), namespace='api')),
    path('environmental/', include((environmental_router.urls, 'environmental'), namespace='api')),
    # ... other apps
]
```

2. Remove the registry extensions to avoid duplication.

### Option B: Update Integration Tests

Alternatively, modify the tests to use direct URL construction instead of `reverse()`:

```python
# Instead of:
reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk})

# Use:
f'/api/v1/scenario/scenarios/{scenario.pk}/run_projection/'
```

However, this approach is less maintainable as URL patterns may change.

## Additional Test Isolation Issues

Beyond the API namespace issues, several other test isolation problems were discovered:

1. **`test_create_scenario_from_batch`**
   - References `scenario.species` which doesn't exist in the Scenario model
   - Fix: Remove this reference or add appropriate field

2. **`test_complete_scenario_workflow`**
   - Uses incorrect constructor parameters for `ProjectionEngine`
   - Fix: Update to match actual implementation (`ProjectionEngine(scenario)`)

3. **Database Constraint Violations**
   - Several model validation tests fail due to unique constraint violations
   - Fix: Improve test isolation with `transaction.atomic()` and unique test data

4. **`ProjectionEngine._load_lifecycle_stages`**
   - Tries to order by `typical_start_weight` which doesn't exist
   - Fix: Update to use correct field name or remove ordering

## Implementation Steps

1. **Fix Router Registration**
   - Choose between Option A (add 'api' namespace) or Option B (update tests)
   - Remove duplicate registry extensions
   - Standardize namespace usage across all apps

2. **Update Integration Tests**
   - Enable the 7 skipped tests once namespace issues are resolved
   - Fix additional test isolation issues

3. **Standardize URL Construction**
   - Create a centralized URL construction utility for tests
   - Update all tests to use consistent patterns

4. **Add Contract Testing**
   - Implement tests to ensure API contract compliance
   - Verify all endpoints are documented in OpenAPI spec

## Conclusion

These issues highlight the need for consistent API patterns and URL construction across the project. Resolving them will not only enable the skipped integration tests but also improve overall code maintainability and reduce future issues.

The recommended approach is Option A (adding the 'api' namespace) as it maintains compatibility with existing test patterns and follows Django best practices for URL namespacing.
