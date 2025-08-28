# API Standards and Conventions

## 1. Overview

This document defines the API standards established during the API Consolidation Project (August 2025) to ensure consistency, maintainability, and proper contract synchronization across the AquaMind platform. These standards address the root causes of URL conflicts, duplicate endpoints, and inconsistent naming conventions that previously complicated API development and testing.

By following these standards, we ensure:
- Clean, predictable URL structures
- Consistent naming across all endpoints
- No duplicate route registrations
- Reliable OpenAPI schema generation
- Reliable API testing and validation

These standards are **mandatory** for all new API development and modifications to existing endpoints.

## 2. URL Pattern Standards

### General Rules

- **Use kebab-case** for all URL segments
  - ✅ `/growth-samples/`, `/feed-containers/`
  - ❌ `/growthSamples/`, `/feed_containers/`

- **Use plural forms** for collection endpoints
  - ✅ `/batches/`, `/species/`
  - ❌ `/batch/`, `/specie/`

- **Keep URLs RESTful and resource-oriented**
  - ✅ `/batches/{id}/growth-analysis/` (resource with sub-resource)
  - ❌ `/get-batch-growth-analysis/{id}/` (verb in URL)

- **Maintain consistent depth**
  - ✅ `/batches/{id}/transfers/` (logical nesting)
  - ❌ `/batches/{batch_id}/containers/{container_id}/transfers/` (excessive nesting)

### URL Structure Patterns

```
/api/v1/<app>/<resource>/                  # Collection endpoint
/api/v1/<app>/<resource>/{id}/             # Detail endpoint
/api/v1/<app>/<resource>/{id}/<action>/    # Action endpoint
```

Examples:
```
/api/v1/batch/batches/                     # List/create batches
/api/v1/batch/batches/5/                   # Get/update/delete batch #5
/api/v1/batch/batches/5/growth-analysis/   # Custom action on batch #5
```

## 3. DRF Router Registration

### Required Pattern

Every ViewSet registration MUST follow this pattern:

```python
router.register(r'url-pattern', ViewSetClass, basename='kebab-case-basename')
```

**Critical**: Never omit the basename parameter - this prevents auto-generated conflicts.

### Examples

✅ **Correct**:
```python
router.register(r'batches', BatchViewSet, basename='batches')
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-samples')
router.register(r'feed-containers', FeedContainerViewSet, basename='feed-containers')
```

❌ **Incorrect**:
```python
# Missing basename - NEVER do this!
router.register(r'batches', BatchViewSet)

# CamelCase basename - NEVER do this!
router.register(r'growth-samples', GrowthSampleViewSet, basename='growthSamples')

# Snake_case basename - NEVER do this!
router.register(r'feed-containers', FeedContainerViewSet, basename='feed_containers')
```

## 4. Basename Conventions

### Naming Rules

1. **Format**: Always kebab-case (lowercase with hyphens)
   ```python
   basename='growth-samples'  # ✅ Correct
   basename='growthSamples'   # ❌ Wrong: camelCase
   basename='growth_samples'  # ❌ Wrong: snake_case
   ```

2. **Uniqueness**: Must be unique across the entire project
   ```python
   # In infrastructure/api/routers.py
   router.register(r'containers', ContainerViewSet, basename='containers')
   
   # In inventory/api/routers.py
   router.register(r'containers', InventoryContainerViewSet, basename='inventory-containers')  # ✅ Unique
   router.register(r'containers', InventoryContainerViewSet, basename='containers')  # ❌ Duplicate!
   ```

3. **Consistency**: Should match the URL pattern
   ```python
   # URL is 'growth-samples', basename should match
   router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-samples')  # ✅
   router.register(r'growth-samples', GrowthSampleViewSet, basename='samples')  # ❌ Mismatch
   ```

4. **No Prefixes**: Don't include app name in basename
   ```python
   # In batch/api/routers.py
   router.register(r'batches', BatchViewSet, basename='batches')  # ✅ Correct
   router.register(r'batches', BatchViewSet, basename='batch-batches')  # ❌ Redundant prefix
   ```

5. **Plural Form**: Use plural for collection endpoints
   ```python
   router.register(r'species', SpeciesViewSet, basename='species')  # ✅ Correct
   router.register(r'species', SpeciesViewSet, basename='specie')  # ❌ Wrong: singular
   ```

### Examples Table

| URL Pattern | ✅ Correct Basename | ❌ Wrong Basename |
|-------------|---------------------|------------------|
| `batches/` | `'batches'` | `'batch'`, `'BatchList'`, `'batch-list'` |
| `growth-samples/` | `'growth-samples'` | `'growthSamples'`, `'growth_samples'` |
| `container-types/` | `'container-types'` | `'containerTypes'`, `'container_types'` |

## 5. Router Organization

### File Structure

```
apps/
└── [app_name]/
    └── api/
        ├── __init__.py
        ├── routers.py      # Router definitions
        ├── viewsets/       # ViewSet implementations
        └── serializers/    # Serializer implementations
```

### Router Module Pattern

```python
# apps/[app_name]/api/routers.py
from rest_framework.routers import DefaultRouter
from apps.[app_name].api.viewsets import (
    # Import all viewsets
)

router = DefaultRouter()

# Register all viewsets with explicit basenames
router.register(r'resource-name', ResourceViewSet, basename='resource-name')
router.register(r'another-resource', AnotherResourceViewSet, basename='another-resource')
```

### URL Integration

```python
# apps/[app_name]/urls.py
from django.urls import path, include
from apps.[app_name].api.routers import router

app_name = '[app_name]'

urlpatterns = [
    path('', include((router.urls, app_name), namespace='api')),
    # Other URL patterns...
]
```

### Complete Example

```python
# apps/batch/api/routers.py
from rest_framework.routers import DefaultRouter
from apps.batch.api.viewsets import (
    BatchViewSet,
    GrowthSampleViewSet,
    MortalityEventViewSet,
    BatchTransferViewSet,
)

router = DefaultRouter()

router.register(r'batches', BatchViewSet, basename='batches')
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-samples')
router.register(r'mortality-events', MortalityEventViewSet, basename='mortality-events')
router.register(r'transfers', BatchTransferViewSet, basename='transfers')
```

```python
# apps/batch/urls.py
from django.urls import path, include
from apps.batch.api.routers import router

app_name = 'batch'

urlpatterns = [
    path('', include((router.urls, app_name), namespace='api')),
]
```

### Anti-Patterns to Avoid

❌ **Never merge routers with registry.extend()**
```python
# NEVER DO THIS
from apps.batch.api.routers import router as batch_router
from apps.health.api.routers import router as health_router

router = DefaultRouter()
router.registry.extend(batch_router.registry)  # WRONG! Creates duplicate routes
router.registry.extend(health_router.registry)  # WRONG! Creates duplicate routes
```

❌ **Never omit the basename parameter**
```python
# NEVER DO THIS
router.register(r'batches', BatchViewSet)  # WRONG! Missing basename
```

❌ **Never use inconsistent casing**
```python
# NEVER DO THIS - Mixed casing styles
router.register(r'batches', BatchViewSet, basename='batches')  # kebab-case
router.register(r'growth-samples', GrowthSampleViewSet, basename='growthSamples')  # camelCase
router.register(r'mortality-events', MortalityEventViewSet, basename='mortality_events')  # snake_case
```

## 6. Testing Implications

When using explicit basenames, ensure tests use the correct reverse patterns:

### Reverse URL Resolution

```python
# Correct - uses the explicit basename
url = reverse('batches-list')  # For collection endpoint
url = reverse('batches-detail', kwargs={'pk': 1})  # For detail endpoint
url = reverse('batches-growth-analysis', kwargs={'pk': 1})  # For custom action
```

### Test Example

```python
def test_list_batches(self):
    url = reverse('batches-list')  # Uses the basename 'batches'
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
    
def test_retrieve_batch(self):
    url = reverse('batches-detail', kwargs={'pk': self.batch.id})  # Uses the basename 'batches'
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
```

### Common Testing Errors

If you change a basename, you must update all tests that use `reverse()` with that basename:

```python
# If you change from:
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-samples')

# To:
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-data')

# You must update all tests from:
url = reverse('growth-samples-list')

# To:
url = reverse('growth-data-list')
```

## 7. Migration Guide

When updating existing code to follow these standards:

### Step 1: Audit Current Router Registrations

```bash
# List all router registrations
grep -r "router.register" --include="*.py" .

# List all URL patterns
python manage.py show_urls | grep "/api/v1/" | sort
```

### Step 2: Add Explicit Basenames

For each ViewSet registration without a basename:

```python
# Before
router.register(r'batches', BatchViewSet)

# After
router.register(r'batches', BatchViewSet, basename='batches')
```

### Step 3: Convert to kebab-case

For each non-kebab-case basename:

```python
# Before (camelCase)
router.register(r'growthSamples', GrowthSampleViewSet, basename='growthSamples')

# After (kebab-case)
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-samples')
```

### Step 4: Update Tests

Find all tests that use `reverse()` with the old basenames:

```bash
# Find all reverse() calls
grep -r "reverse(" --include="*.py" ./apps
```

Update each test to use the new basename:

```python
# Before
url = reverse('growthSamples-list')

# After
url = reverse('growth-samples-list')
```

### Step 5: Verify Changes

```bash
# Run tests
python -m coverage run --source='.' manage.py test

# Verify no duplicate URLs
python manage.py show_urls | sort | uniq -d

# Run Schemathesis
schemathesis run --base-url=http://127.0.0.1:8000 --checks all --hypothesis-max-examples=10 api/openapi.yaml
```

## 8. Enforcement

These standards are enforced through:

### Code Review Requirements

- All PR reviews must verify:
  - Explicit kebab-case basenames for all ViewSet registrations
  - No router registry extensions
  - Tests updated for any basename changes

### Automated Checks

- **Pre-commit hooks** (when implemented):
  - Check for missing basenames
  - Verify kebab-case format
  - Detect router registry extensions

### CI/CD Pipeline

- **URL pattern analysis**:
  ```bash
  python manage.py show_urls | grep "/api/v1/" | sort | uniq -c | grep -v "^ *1 "
  ```
  This command identifies duplicate URL patterns

- **Schemathesis contract testing**:
  Detects 404 errors and duplicate endpoints

### Documentation

- This standards document
- Code organization guidelines
- API contract synchronization guide

## 9. Appendix: Complete Router Example

```python
# apps/health/api/routers.py
from rest_framework.routers import DefaultRouter
from apps.health.api.viewsets import (
    HealthParameterViewSet,
    HealthSamplingEventViewSet,
    FishParameterScoreViewSet,
    HealthLabSampleViewSet,
    IndividualFishObservationViewSet,
    JournalEntryViewSet,
    LiceCountViewSet,
    MortalityReasonViewSet,
    MortalityRecordViewSet,
    SampleTypeViewSet,
    TreatmentViewSet,
    VaccinationTypeViewSet,
)

router = DefaultRouter()

# Health observation endpoints
router.register(r'health-parameters', HealthParameterViewSet, basename='health-parameters')
router.register(r'health-sampling-events', HealthSamplingEventViewSet, basename='health-sampling-events')
router.register(r'fish-parameter-scores', FishParameterScoreViewSet, basename='fish-parameter-scores')
router.register(r'individual-fish-observations', IndividualFishObservationViewSet, basename='individual-fish-observations')

# Lab samples
router.register(r'health-lab-samples', HealthLabSampleViewSet, basename='health-lab-samples')
router.register(r'sample-types', SampleTypeViewSet, basename='sample-types')

# Records
router.register(r'journal-entries', JournalEntryViewSet, basename='journal-entries')
router.register(r'lice-counts', LiceCountViewSet, basename='lice-counts')
router.register(r'mortality-reasons', MortalityReasonViewSet, basename='mortality-reasons')
router.register(r'mortality-records', MortalityRecordViewSet, basename='mortality-records')

# Treatments
router.register(r'treatments', TreatmentViewSet, basename='treatments')
router.register(r'vaccination-types', VaccinationTypeViewSet, basename='vaccination-types')
```

```python
# apps/health/urls.py
from django.urls import path, include
from apps.health.api.routers import router

app_name = 'health'

urlpatterns = [
    path('', include((router.urls, 'health'), namespace='api')),
]
```

By following these standards, we ensure a clean, consistent, and maintainable API structure across the entire AquaMind platform.

## 10. Contract Testing and Validation

The static **contract test** layer (located in `tests/contract/`) guarantees that
our implementation and documentation never drift apart.  These tests are fast,
pure-Python checks that run **before** Schemathesis in CI.

### 10.1 What They Validate

| Area                         | Assertion                                                                    |
|------------------------------|-------------------------------------------------------------------------------|
| ViewSet registration         | Every `ViewSet` class is registered in at least one DRF router               |
| Serializer presence          | `serializer_class` (or `get_serializer_class`) is defined                    |
| Authentication               | `permission_classes` are explicitly declared *(defaulting to IsAuthenticated)*|
| URL versioning               | All paths begin with `/api/v1/`                                              |
| OpenAPI schema               | Schema generation succeeds and passes OpenAPI 3.1 validation                 |
| Security schemes             | Token / JWT auth schemes appear in the schema                                |

### 10.2 Running Contract Tests Locally

```bash
# Quick run – fails fast on structural issues
python manage.py test tests.contract
```

### 10.3 CI Enforcement

The GitHub Action executes the contract suite automatically; a pull-request
cannot be merged unless **all contract tests pass**.  This ensures:

* New endpoints are documented
* No broken router registrations reach main
* The generated `openapi.yaml` remains valid

### 10.4 Relationship to Schemathesis

* **Contract tests** – static, introspective, catch obvious structural /
  documentation mistakes.
* **Schemathesis** – dynamic, property-based HTTP calls derived from the schema;
  catches behavioural and edge-case issues.

Both layers together provide high confidence in API quality and backwards
compatibility guarantees.
