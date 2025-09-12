# Aggregation Implementation Playbook

> **Purpose**: Standardize how we build aggregation endpoints for KPI cards. This playbook provides copy-pasteable code snippets, patterns, and validation steps to minimize context rot across engineering sessions.

## Session Workflow

1. **Pre-read**: Review recommendations and API standards
2. **Scaffold**: Add endpoint skeleton with explicit kebab-case basename and `extend_schema`
3. **Implement**: Use DB-level aggregates, add 30–60s cache via `cache_page`
4. **Test**: Add tests for happy-path + edge cases + filter variations
5. **Validate**: Run Django tests + OpenAPI validation; ensure no drf-spectacular warnings

## Pattern Selection

### Use `@action` for Detail-Level Aggregation
```python
# Use for entity-specific KPIs: /infrastructure/areas/{id}/summary
@action(detail=True, methods=['get'])
def summary(self, request, pk=None):
    # Query entity and compute aggregates
```

### Use `@action` for Collection-Level Aggregation
```python
# Use for global summaries: /batch/container-assignments/summary
@action(detail=False, methods=['get'])
def summary(self, request):
    # Query collection and compute aggregates
```

### Use `APIView` for Complex Multi-Entity Aggregation
```python
# Use for infrastructure overview requiring multiple models
class InfrastructureOverviewView(APIView):
    # Complex aggregation logic
```

## Required Imports

```python
from django.db.models import Count, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse
```

## Caching Pattern

```python
@method_decorator(cache_page(30))  # 30-60 seconds for KPI data
@extend_schema(
    operation_id="area-summary",
    description="Get KPI summary for an area",
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "container_count": {"type": "integer"},
                    "active_biomass_kg": {"type": "number"},
                    "population_count": {"type": "integer"},
                    "avg_weight_kg": {"type": "number"},
                },
                "required": ["container_count", "active_biomass_kg", "population_count", "avg_weight_kg"],
            },
            description="Area KPI metrics",
        )
    },
)
def summary(self, request, pk=None):
    area = self.get_object()

    # DB-level aggregates for performance
    aggregates = Container.objects.filter(area=area).aggregate(
        container_count=Count('id'),
        total_biomass=Sum('batch_assignments__biomass_kg'),  # Through relation
        total_population=Sum('batch_assignments__population_count'),
    )

    # Compute derived metrics
    biomass_kg = float(aggregates['total_biomass'] or 0)
    population_count = aggregates['total_population'] or 0
    avg_weight_kg = biomass_kg / population_count if population_count > 0 else 0

    return Response({
        'container_count': aggregates['container_count'] or 0,
        'active_biomass_kg': biomass_kg,
        'population_count': population_count,
        'avg_weight_kg': round(avg_weight_kg, 3),
    })
```

## Router Registration

```python
# apps/infrastructure/api/routers.py
from rest_framework.routers import DefaultRouter
from apps.infrastructure.api.viewsets import AreaViewSet

router = DefaultRouter()
router.register(r'areas', AreaViewSet, basename='areas')  # Explicit kebab-case basename
```

## Test Template

```python
# apps/infrastructure/tests/api/test_area_summary.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from apps.infrastructure.models import Area, Container
from apps.batch.models import BatchContainerAssignment


class AreaSummaryTestCase(APITestCase):
    def setUp(self):
        # Create test data
        self.area = Area.objects.create(name="Test Area")
        self.container = Container.objects.create(
            name="Test Container",
            area=self.area,
            max_biomass_kg=1000
        )
        # Create assignment with biomass
        self.assignment = BatchContainerAssignment.objects.create(
            container=self.container,
            biomass_kg=500,
            population_count=10000,
            is_active=True
        )

    def test_area_summary_success(self):
        """Test successful area summary retrieval."""
        url = reverse('areas-summary', kwargs={'pk': self.area.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('container_count', response.data)
        self.assertIn('active_biomass_kg', response.data)
        self.assertIn('population_count', response.data)
        self.assertIn('avg_weight_kg', response.data)

    def test_area_summary_with_zero_population(self):
        """Test area summary with no active assignments."""
        # Remove assignment
        self.assignment.delete()

        url = reverse('areas-summary', kwargs={'pk': self.area.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['container_count'], 1)
        self.assertEqual(response.data['active_biomass_kg'], 0)
        self.assertEqual(response.data['population_count'], 0)
        self.assertEqual(response.data['avg_weight_kg'], 0)

    def test_area_summary_nonexistent(self):
        """Test area summary for non-existent area."""
        url = reverse('areas-summary', kwargs={'pk': 999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

## OpenAPI Validation Commands

```bash
# Validate schema generation (no warnings/errors)
python manage.py spectacular --validate --file /tmp/schema.yaml --settings=aquamind.settings_ci

# Regenerate OpenAPI schema
python manage.py spectacular --file openapi.yaml --settings=aquamind.settings_ci

# Check for schema generation warnings
python manage.py spectacular --settings=aquamind.settings_ci 2>&1 | grep -i warning
```

## Quality Checks

### Pre-commit Checklist
- [ ] Endpoint URL follows `/api/v1/{app}/{resource}/{id}/summary/` pattern
- [ ] Basename is explicit kebab-case
- [ ] Schema includes `extend_schema` with proper response types
- [ ] Caching set to 30-60 seconds
- [ ] Tests cover happy path, edge cases, and filters
- [ ] OpenAPI validates without warnings

### Common Pitfalls
- **Missing basename**: Always add explicit basename to `router.register()`
- **Wrong action type**: Use `detail=True` for entity-specific, `detail=False` for collection
- **No caching**: KPI data should be cached for performance
- **Missing schema**: Always add `extend_schema` for API documentation
- **Inefficient queries**: Use DB aggregates, avoid Python loops
- **Wrong URL patterns**: Use kebab-case, follow API standards

## References

- [Server-side Aggregation Recommendations](../progress/aggregation/server-side-aggregation-kpi-recommendations.md)
- [API Standards](../quality_assurance/api_standards.md)
- [Infrastructure Overview Example](../../apps/infrastructure/api/viewsets/overview.py)
- [Batch Assignment Summary Example](../../apps/batch/api/viewsets.py)
- [Feeding Summary Example](../../apps/inventory/api/viewsets/feeding.py)
