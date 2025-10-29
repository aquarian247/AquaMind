# Inventory Aggregation Enhancements for Finance Reporting

**Feature Branch**: `feature/inventory-finance-aggregation-enhancements`  
**Status**: In Progress  
**Priority**: High (UAT Blocker)  
**Estimated Effort**: 8-12 hours

---

## Executive Summary

Finance team requires flexible, high-performance feed usage and cost reporting with multi-dimensional filtering capabilities. Current API lacks geographic filters, feed property filters, cost aggregation, and flexible breakdown options. This enhancement provides comprehensive backend aggregation to eliminate inefficient client-side processing.

### Business Requirements

Finance personnel must be able to query:
- *"How much feed of type X with fat % > 12 from supplier Y was used in the past 32 days in Scotland?"*
- *"What were total feed expenses in Area 3 last quarter, broken down by feed type?"*
- *"Show me weekly feed consumption trends for Station 5 with protein % > 31"*

### Technical Approach

Implement comprehensive backend filtering and aggregation using Django ORM optimizations, avoiding N+1 queries and enabling server-side calculations. Maintain API contract-first workflow with OpenAPI schema updates and frontend synchronization.

---

## Phase 1: Enhanced Filtering Infrastructure

### Task 1.1: Extend FeedingEventFilter with Geographic Relationships
**File**: `apps/inventory/api/filters/feeding.py`  
**Effort**: 30 minutes  
**Testing**: Unit tests for filter application

**Requirements**:
- Add geographic filters via container relationships
- Support multi-value filtering (`__in` lookups)
- Maintain backward compatibility

**Filters to Add**:
```python
# Geographic dimension filters
area = NumberFilter(field_name='container__area__id')
area__in = BaseInFilter(field_name='container__area__id')
geography = NumberFilter(field_name='container__area__geography__id')
geography__in = BaseInFilter(field_name='container__area__geography__id')
freshwater_station = NumberFilter(field_name='container__hall__freshwater_station__id')
freshwater_station__in = BaseInFilter(field_name='container__hall__freshwater_station__id')
hall = NumberFilter(field_name='container__hall__id')
hall__in = BaseInFilter(field_name='container__hall__id')
```

**Test Cases** (`apps/inventory/tests/test_filters.py`):
- Filter by single area returns correct events
- Filter by multiple geographies returns combined results
- Filter by freshwater_station excludes non-matching events
- Combined geographic + date filters work correctly

---

### Task 1.2: Add Feed Property Filters
**File**: `apps/inventory/api/filters/feeding.py`  
**Effort**: 30 minutes  
**Testing**: Unit tests for nutritional filtering

**Filters to Add**:
```python
# Feed nutritional property filters
feed__protein_percentage__gte = NumberFilter(field_name='feed__protein_percentage', lookup_expr='gte')
feed__protein_percentage__lte = NumberFilter(field_name='feed__protein_percentage', lookup_expr='lte')
feed__fat_percentage__gte = NumberFilter(field_name='feed__fat_percentage', lookup_expr='gte')
feed__fat_percentage__lte = NumberFilter(field_name='feed__fat_percentage', lookup_expr='lte')
feed__brand = CharFilter(field_name='feed__brand', lookup_expr='iexact')
feed__brand__in = BaseInFilter(field_name='feed__brand')
feed__size_category = ChoiceFilter(field_name='feed__size_category')
feed__size_category__in = MultipleChoiceFilter(field_name='feed__size_category')
```

**Test Cases** (`apps/inventory/tests/test_filters.py`):
- Filter protein_percentage >= 45 returns high-protein feeds only
- Filter fat_percentage range returns within bounds
- Filter brand returns exact matches (case-insensitive)
- Combined nutritional filters work as AND conditions

---

### Task 1.3: Add Cost-Based Filters
**File**: `apps/inventory/api/filters/feeding.py`  
**Effort**: 45 minutes  
**Testing**: Integration tests for FIFO cost relationships

**Challenge**: Feed cost comes from `FeedPurchase` via `FeedContainerStock`, not directly on `FeedingEvent`.

**Filters to Add**:
```python
# Direct cost filters on FeedingEvent
feed_cost__gte = NumberFilter(field_name='feed_cost', lookup_expr='gte')
feed_cost__lte = NumberFilter(field_name='feed_cost', lookup_expr='lte')

# Supplier filters (requires join through feed purchase)
feed_purchase__supplier = CharFilter(
    field_name='feed__purchases__supplier',
    lookup_expr='icontains'
)
```

**Note**: For purchase-level cost filtering (cost_per_kg), may require custom FilterMethod since relationship is indirect via FIFO.

**Test Cases** (`apps/inventory/tests/test_filters.py`):
- Filter feed_cost >= 100 returns high-cost events
- Filter by supplier name returns correct purchases
- Verify no duplicate results from many-to-many joins

---

## Phase 2: Enhanced Aggregation Endpoint

### Task 2.1: Create Finance Report Endpoint
**File**: `apps/inventory/api/viewsets/feeding.py`  
**Effort**: 2 hours  
**Testing**: Integration tests with complex filter combinations

**Endpoint**: `POST /api/v1/inventory/feeding-events/finance-report/`

**Accepts All FeedingEventFilter Parameters** (from Phase 1) plus:
```python
group_by: str  # Options: 'feed_type', 'area', 'geography', 'container', 'date', 'week', 'month'
include_time_series: bool  # Include daily/weekly breakdown
include_breakdowns: bool  # Include dimensional breakdowns
```

**Returns**:
```json
{
  "summary": {
    "total_feed_kg": 15420.50,
    "total_feed_cost": 77102.50,
    "events_count": 1250,
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-03-31"
    },
    "filters_applied": {
      "geography": "Scotland",
      "feed__fat_percentage__gte": 12,
      "feed__brand": "Premium Brand"
    }
  },
  "by_feed_type": [
    {
      "feed_id": 3,
      "feed_name": "Premium Starter",
      "brand": "Premium Brand",
      "protein_percentage": 45.0,
      "fat_percentage": 15.0,
      "total_kg": 5200.00,
      "total_cost": 31200.00,
      "events_count": 420,
      "avg_cost_per_kg": 6.00
    }
  ],
  "by_geography": [
    {
      "geography_id": 1,
      "geography_name": "Scotland",
      "total_kg": 10200.00,
      "total_cost": 51000.00,
      "events_count": 850,
      "area_count": 3
    }
  ],
  "by_area": [
    {
      "area_id": 5,
      "area_name": "Area 3",
      "geography": "Scotland",
      "total_kg": 3400.00,
      "total_cost": 17000.00,
      "events_count": 280,
      "container_count": 4
    }
  ],
  "by_container": [
    {
      "container_id": 12,
      "container_name": "Tank A-5",
      "area": "Area 3",
      "total_kg": 850.00,
      "total_cost": 4250.00,
      "events_count": 70,
      "feed_type_count": 2
    }
  ],
  "time_series": [
    {
      "date": "2024-01-01",
      "total_kg": 150.00,
      "total_cost": 750.00,
      "events_count": 12
    },
    {
      "date": "2024-01-02",
      "total_kg": 165.00,
      "total_cost": 825.00,
      "events_count": 13
    }
  ]
}
```

**Implementation Approach**:
1. Apply all filters from enhanced `FeedingEventFilter`
2. Use `select_related()` for container, feed, area, geography (avoid N+1)
3. Use `prefetch_related()` for feed purchases if needed
4. Single-pass aggregation with conditional breakdowns
5. Optimize for large datasets (>10k events)

**Test Cases** (`apps/inventory/tests/test_finance_reporting.py`):
- Basic aggregation returns correct totals
- Geographic filter (Scotland) returns only Scottish events
- Feed property filters (protein > 31) return correct subset
- Combined filters work as AND conditions
- Cost aggregation matches manual calculation
- Breakdown by feed_type sums correctly
- Breakdown by area groups correctly
- Time series returns daily values
- Empty results return zero values (not null)
- Invalid filter parameters return 400 error
- Date range validation works

**Performance Requirements**:
- Query execution < 2 seconds for 10,000 events
- Database queries < 10 (check with `django-debug-toolbar`)
- Response size < 1MB

---

### Task 2.2: Update Existing Summary Endpoint
**File**: `apps/inventory/api/viewsets/feeding.py`  
**Effort**: 30 minutes  
**Testing**: Update existing tests

**Changes**:
- Add `total_feed_cost` to aggregation (currently missing!)
- Add `feed__in` filter support to `/summary/` endpoint
- Maintain backward compatibility

**Before**:
```json
{
  "events_count": 150,
  "total_feed_kg": 1250.5
}
```

**After**:
```json
{
  "events_count": 150,
  "total_feed_kg": 1250.5,
  "total_feed_cost": 6252.50  // NEW
}
```

**Test Cases** (`apps/inventory/tests/test_viewsets.py`):
- Update existing summary tests to assert `total_feed_cost`
- Verify cost calculation matches sum of `feed_cost` fields
- Ensure backward compatibility (no breaking changes)

---

## Phase 3: OpenAPI Schema & Documentation

### Task 3.1: Add drf-spectacular Schema Decorators
**File**: `apps/inventory/api/viewsets/feeding.py`  
**Effort**: 1 hour  
**Testing**: Schema validation

**Requirements**:
- Add comprehensive `@extend_schema` decorator to `finance_report` action
- Document all query parameters with types, defaults, descriptions
- Define complete response schema with examples
- Follow API Standards (Section 8)

**Schema Definition**:
```python
@extend_schema(
    operation_id="feeding-events-finance-report",
    summary="Comprehensive finance report with flexible filtering and aggregations",
    description="""
    Provides detailed feed usage and cost analysis with multi-dimensional filtering.
    
    Supports filtering by:
    - Time periods (date ranges, months, quarters, years)
    - Geography (geography, area, freshwater_station, hall, container)
    - Feed properties (protein %, fat %, brand, size category)
    - Cost ranges (feed_cost, supplier)
    - Feed types (multiple selection)
    
    Returns aggregated totals and breakdowns by selected dimensions.
    """,
    parameters=[
        # Date filters
        OpenApiParameter(name='start_date', type=OpenApiTypes.DATE, ...),
        OpenApiParameter(name='end_date', type=OpenApiTypes.DATE, ...),
        
        # Geographic filters
        OpenApiParameter(name='geography', type=OpenApiTypes.INT, ...),
        OpenApiParameter(name='geography__in', type={'type': 'array', 'items': {'type': 'integer'}}, ...),
        OpenApiParameter(name='area', type=OpenApiTypes.INT, ...),
        OpenApiParameter(name='area__in', type={'type': 'array', 'items': {'type': 'integer'}}, ...),
        OpenApiParameter(name='freshwater_station', type=OpenApiTypes.INT, ...),
        
        # Feed property filters
        OpenApiParameter(name='feed__protein_percentage__gte', type=OpenApiTypes.DECIMAL, ...),
        OpenApiParameter(name='feed__fat_percentage__gte', type=OpenApiTypes.DECIMAL, ...),
        OpenApiParameter(name='feed__brand', type=OpenApiTypes.STR, ...),
        
        # Cost filters
        OpenApiParameter(name='feed_cost__gte', type=OpenApiTypes.DECIMAL, ...),
        
        # Grouping options
        OpenApiParameter(name='group_by', type=OpenApiTypes.STR, enum=['feed_type', 'area', 'geography', 'container', 'date', 'week', 'month'], ...),
        OpenApiParameter(name='include_time_series', type=OpenApiTypes.BOOL, default=False, ...),
        OpenApiParameter(name='include_breakdowns', type=OpenApiTypes.BOOL, default=True, ...),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "summary": {...},
                "by_feed_type": {...},
                "by_geography": {...},
                "by_area": {...},
                "by_container": {...},
                "time_series": {...}
            }
        }
    }
)
```

**Validation**:
```bash
# Must pass with zero warnings
python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn
```

---

### Task 3.2: Update OpenAPI Documentation
**Files**: `api/openapi.yaml`, API docstrings  
**Effort**: 30 minutes  
**Testing**: Schema validation, documentation review

**Actions**:
1. Regenerate OpenAPI schema: `python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`
2. Verify no drf-spectacular warnings
3. Review Swagger UI documentation
4. Ensure examples are clear and accurate

**Validation Checklist**:
- [ ] Zero Spectacular warnings during generation
- [ ] All parameters documented with types and descriptions
- [ ] Response schema includes all fields with types
- [ ] Examples demonstrate common use cases
- [ ] Swagger UI renders correctly

---

## Phase 4: Service Layer Implementation

### Task 4.1: Create FinanceReportingService
**File**: `apps/inventory/services/finance_reporting_service.py` (NEW)  
**Effort**: 3 hours  
**Testing**: Comprehensive unit tests

**Purpose**: Encapsulate complex aggregation logic, separate from ViewSet concerns.

**Service Methods**:
```python
class FinanceReportingService:
    @classmethod
    def generate_finance_report(
        cls,
        queryset: QuerySet[FeedingEvent],
        include_breakdowns: bool = True,
        include_time_series: bool = False,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive finance report from filtered queryset.
        
        Args:
            queryset: Pre-filtered FeedingEvent queryset
            include_breakdowns: Include dimensional breakdowns
            include_time_series: Include daily/weekly time series
            group_by: Primary grouping dimension
            
        Returns:
            Dict with summary, breakdowns, and optional time series
        """
        
    @classmethod
    def calculate_summary(cls, queryset: QuerySet) -> Dict[str, Any]:
        """Calculate top-level summary metrics."""
        
    @classmethod
    def breakdown_by_feed_type(cls, queryset: QuerySet) -> List[Dict]:
        """Aggregate by feed type with nutritional info."""
        
    @classmethod
    def breakdown_by_geography(cls, queryset: QuerySet) -> List[Dict]:
        """Aggregate by geography with area counts."""
        
    @classmethod
    def breakdown_by_area(cls, queryset: QuerySet) -> List[Dict]:
        """Aggregate by area with container counts."""
        
    @classmethod
    def breakdown_by_container(cls, queryset: QuerySet) -> List[Dict]:
        """Aggregate by container with feed diversity."""
        
    @classmethod
    def generate_time_series(
        cls, 
        queryset: QuerySet,
        interval: str = 'day'
    ) -> List[Dict]:
        """Generate time series with specified interval (day/week/month)."""
```

**Optimization Requirements**:
- Use `select_related()` for: `container`, `container__area`, `container__area__geography`, `feed`
- Use `prefetch_related()` for: feed purchases (if cost attribution needed)
- Single database query per breakdown method
- Annotate queryset rather than Python loops where possible
- Use `values()` + `annotate()` for efficient grouping

**Test Cases** (`apps/inventory/tests/test_services/test_finance_reporting.py`):
- Summary calculation with 1000 events returns correct totals
- Feed type breakdown groups correctly
- Geography breakdown includes all geographies
- Area breakdown calculates container counts correctly
- Time series generates correct daily buckets
- Empty queryset returns zero values
- Performance test: 10k events < 2 seconds
- Query count test: Each method < 5 queries

---

## Phase 5: ViewSet Integration

### Task 5.1: Implement finance_report Action
**File**: `apps/inventory/api/viewsets/feeding.py`  
**Effort**: 1.5 hours  
**Testing**: API integration tests

**Implementation**:
```python
@extend_schema(...)  # From Task 3.1
@action(detail=False, methods=['get'])
@method_decorator(cache_page(60))  # Cache for 1 minute
def finance_report(self, request):
    """
    Comprehensive finance report with flexible filtering and breakdowns.
    """
    # 1. Apply all filters from FeedingEventFilter
    queryset = self.filter_queryset(self.get_queryset())
    
    # 2. Extract grouping options
    include_breakdowns = request.query_params.get('include_breakdowns', 'true').lower() == 'true'
    include_time_series = request.query_params.get('include_time_series', 'false').lower() == 'true'
    group_by = request.query_params.get('group_by')
    
    # 3. Validate date range provided (required for finance reports)
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if not (start_date and end_date):
        return Response(
            {"error": "Both start_date and end_date are required for finance reports"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 4. Generate report via service
    try:
        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=include_breakdowns,
            include_time_series=include_time_series,
            group_by=group_by
        )
        return Response(report)
    except Exception as e:
        logger.exception("Finance report generation failed")
        return Response(
            {"error": "Report generation failed", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Test Cases** (`apps/inventory/tests/test_finance_api.py`):
- Unauthenticated request returns 401
- Missing date range returns 400 error
- Valid request returns complete report structure
- Geographic filter (geography=1) filters correctly
- Feed filter (protein >= 45) filters correctly
- Cost filter (feed_cost >= 100) filters correctly
- Supplier filter returns correct results
- Combined multi-dimensional filters work
- Breakdowns sum to total
- Time series covers date range
- group_by parameter groups correctly
- Empty results return valid structure
- Performance: 10k events < 2 seconds
- Cached response returns quickly on second call

---

### Task 5.2: Enhance Existing Summary Endpoint
**File**: `apps/inventory/api/viewsets/feeding.py`  
**Effort**: 45 minutes  
**Testing**: Update existing tests

**Changes**:
1. Add `total_feed_cost` to aggregation
2. Support feed type filtering in summary
3. Maintain backward compatibility
4. Update schema documentation

**Implementation**:
```python
aggregates = qs.aggregate(
    events_count=Count("id"),
    total_feed_kg=Sum("amount_kg"),
    total_feed_cost=Sum("feed_cost"),  # NEW
)

return Response({
    "events_count": aggregates["events_count"] or 0,
    "total_feed_kg": float(aggregates["total_feed_kg"] or 0),
    "total_feed_cost": float(aggregates["total_feed_cost"] or 0),  # NEW
})
```

**Test Cases** (`apps/inventory/tests/test_viewsets.py`):
- Update `FeedingEventSummaryTest` to assert `total_feed_cost`
- Verify cost calculation correctness
- Ensure existing tests still pass (backward compatibility)

---

## Phase 6: Testing & Quality Assurance

### Task 6.1: Comprehensive Unit Tests
**File**: `apps/inventory/tests/test_finance_reporting.py` (NEW)  
**Effort**: 2 hours  
**Coverage Target**: 95%+ for new code

**Test Structure**:
```python
class FinanceReportingServiceTest(TestCase):
    """Tests for FinanceReportingService."""
    
    def setUp(self):
        """Create comprehensive test fixture."""
        # Multiple geographies, areas, containers
        # Multiple feed types with varying properties
        # Feed purchases with different costs
        # Feeding events spanning date range
        
    def test_summary_calculation(self):
        """Test top-level summary metrics."""
        
    def test_breakdown_by_feed_type(self):
        """Test feed type aggregation with nutritional data."""
        
    def test_breakdown_by_geography(self):
        """Test geography aggregation."""
        
    def test_breakdown_by_area(self):
        """Test area aggregation with container counts."""
        
    def test_time_series_daily(self):
        """Test daily time series generation."""
        
    def test_time_series_weekly(self):
        """Test weekly time series buckets."""
        
    def test_time_series_monthly(self):
        """Test monthly time series buckets."""
        
    def test_empty_queryset_handling(self):
        """Test graceful handling of no results."""
        
    def test_performance_with_10k_events(self):
        """Performance test with large dataset."""


class FinanceReportAPITest(TestCase):
    """API integration tests for finance reporting."""
    
    def setUp(self):
        """Setup API client and test data."""
        
    def test_complex_filter_combination(self):
        """Test Scotland + protein > 31 + last 32 days."""
        # This is the exact use case from requirements!
        
    def test_supplier_and_geography_filter(self):
        """Test supplier Y in geography Scotland."""
        
    def test_nutritional_range_filtering(self):
        """Test fat % > 12 with feed type X."""
        
    def test_cost_range_filtering(self):
        """Test cost_per_kg filtering."""
        
    def test_quarterly_aggregation(self):
        """Test Q1 2024 aggregation."""
        
    def test_weekly_trends(self):
        """Test weekly time series."""
```

**Coverage Verification**:
```bash
coverage run --source='apps.inventory' manage.py test apps.inventory.tests.test_finance_reporting
coverage report --show-missing
# Target: 95%+ for services/finance_reporting_service.py
```

---

### Task 6.2: API Contract Tests
**File**: `tests/api/test_inventory_finance.py` (NEW)  
**Effort**: 1 hour  
**Testing**: Contract compliance

**Test Cases**:
- Finance report endpoint exists and responds
- All documented parameters work
- Response structure matches schema
- Error responses match documented format
- Authentication enforcement works
- Caching behavior correct

---

## Phase 7: Frontend Integration

### Task 7.1: Regenerate OpenAPI Client
**Repo**: AquaMind-Frontend  
**Effort**: 15 minutes  
**Testing**: Build verification

**Steps**:
1. Copy updated `api/openapi.yaml` from backend to frontend
2. Run `npm run sync:openapi` to regenerate client
3. Verify generated TypeScript types
4. Commit generated code

**Verification**:
```bash
cd /Users/aquarian247/Projects/AquaMind-Frontend
npm run sync:openapi
npm run build  # Ensure no TypeScript errors
```

---

### Task 7.2: Update Frontend Feature Documentation
**File**: `AquaMind-Frontend/docs/features/inventory-finance-reporting.md` (NEW)  
**Effort**: 30 minutes

**Document**:
- Available filter parameters
- Response structure
- Usage examples
- Common query patterns
- Performance considerations

---

## Phase 8: Performance Validation & Documentation

### Task 8.1: Performance Benchmarking
**File**: `apps/inventory/tests/performance/test_finance_performance.py` (NEW)  
**Effort**: 2 hours  
**Note**: Performance tests are SEPARATE from unit tests - run less frequently, use realistic data

**Test Structure**:
```python
"""
Performance tests for finance reporting.

These tests use realistic data structures with proper relationships
and are separate from unit tests to avoid slowing down regular test runs.

Run with: python manage.py test apps.inventory.tests.performance
Skip with: @unittest.skip("Performance test - run manually")
"""

class FinanceReportPerformanceTest(TestCase):
    """
    Performance validation for finance reporting with realistic data.
    
    Uses complete relationship chains:
    - Geography → Area → Container
    - Batch → BatchContainerAssignment → Container
    - Feed → FeedPurchase → FeedContainerStock → FeedContainer
    - FeedingEvent with proper batch_assignment and calculated costs
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Create realistic test infrastructure ONCE for all performance tests.
        
        Creates:
        - 2 geographies (Scotland, Faroe Islands)
        - 6 areas (3 per geography)
        - 1 freshwater station with 2 halls
        - 30 containers (5 per area)
        - 5 feed types with varying nutritional profiles
        - 5 feed purchases (one per feed type)
        - FeedContainerStock entries (FIFO inventory)
        - 10 batches with proper BatchContainerAssignments
        """
        super().setUpClass()
        
        # Geography/Area hierarchy
        cls.scotland = Geography.objects.create(name="Scotland")
        cls.faroe = Geography.objects.create(name="Faroe Islands")
        
        cls.areas = []
        for geo in [cls.scotland, cls.faroe]:
            for i in range(3):
                area = Area.objects.create(
                    name=f"{geo.name} Area {i+1}",
                    geography=geo,
                    latitude=Decimal('57.0') + i,
                    longitude=Decimal('-3.0') - i,
                    max_biomass=Decimal('50000.0')
                )
                cls.areas.append(area)
        
        # Freshwater station/hall (for hall-based filtering tests)
        cls.station = FreshwaterStation.objects.create(
            name="Test Station",
            geography=cls.scotland,
            station_type="HATCHERY",
            latitude=Decimal('57.5'),
            longitude=Decimal('-3.5')
        )
        cls.halls = [
            Hall.objects.create(
                name=f"Hall {i+1}",
                freshwater_station=cls.station
            )
            for i in range(2)
        ]
        
        # Containers (area-based + hall-based)
        cls.container_type = ContainerType.objects.create(
            name="Standard Tank",
            category="TANK",
            max_volume_m3=Decimal('200.0')
        )
        
        cls.containers = []
        # Area-based containers
        for area in cls.areas:
            for i in range(5):
                container = Container.objects.create(
                    name=f"{area.name} Tank {i+1}",
                    container_type=cls.container_type,
                    area=area,
                    volume_m3=Decimal('100.0'),
                    max_biomass_kg=Decimal('5000.0')
                )
                cls.containers.append(container)
        
        # Hall-based containers
        for hall in cls.halls:
            for i in range(2):
                container = Container.objects.create(
                    name=f"{hall.name} Tank {i+1}",
                    container_type=cls.container_type,
                    hall=hall,
                    volume_m3=Decimal('100.0'),
                    max_biomass_kg=Decimal('5000.0')
                )
                cls.containers.append(container)
        
        # Feeds with varying nutritional profiles
        cls.feeds_with_purchases = []
        nutritional_profiles = [
            ("Premium Starter", "Supplier A", 50, 22, Decimal('7.50')),
            ("Growth Feed", "Supplier B", 46, 20, Decimal('6.50')),
            ("Standard Feed", "Supplier A", 42, 16, Decimal('5.50')),
            ("Economy Feed", "Supplier C", 38, 12, Decimal('4.50')),
            ("Finishing Feed", "Supplier B", 36, 10, Decimal('4.00')),
        ]
        
        for name, supplier, protein, fat, cost in nutritional_profiles:
            feed = Feed.objects.create(
                name=name,
                brand=supplier,
                size_category="MEDIUM",
                protein_percentage=Decimal(str(protein)),
                fat_percentage=Decimal(str(fat))
            )
            
            purchase = FeedPurchase.objects.create(
                feed=feed,
                quantity_kg=Decimal('100000.0'),  # Large purchase
                cost_per_kg=cost,
                supplier=supplier,
                purchase_date=timezone.now().date() - timedelta(days=60),
                batch_number=f"BATCH-{name[:3].upper()}-001"
            )
            
            cls.feeds_with_purchases.append((feed, purchase, cost))
        
        # Create feed containers and stock
        cls.feed_containers = []
        for area in cls.areas[:3]:  # 3 feed containers
            feed_container = FeedContainer.objects.create(
                name=f"{area.name} Feed Silo",
                area=area,
                capacity_kg=Decimal('50000.0')
            )
            cls.feed_containers.append(feed_container)
            
            # Add each feed type to this container (FIFO inventory)
            for feed, purchase, cost in cls.feeds_with_purchases:
                FeedContainerStock.objects.create(
                    feed_container=feed_container,
                    feed_purchase=purchase,
                    quantity_kg=Decimal('10000.0'),
                    entry_date=timezone.now() - timedelta(days=30)
                )
        
        # Create batches with proper container assignments
        cls.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        cls.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=cls.species,
            order=1
        )
        
        cls.batches_with_assignments = []
        for i, container in enumerate(cls.containers[:10]):  # 10 active batches
            batch = Batch.objects.create(
                batch_number=f"PERF-BATCH-{i+1:04d}",
                species=cls.species,
                lifecycle_stage=cls.lifecycle_stage,
                start_date=timezone.now().date() - timedelta(days=90),
                status='ACTIVE'
            )
            
            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=cls.lifecycle_stage,
                population_count=10000 + (i * 500),
                avg_weight_g=Decimal('100.0') + i,
                biomass_kg=Decimal('1000.0') + (i * 50),
                assignment_date=timezone.now().date() - timedelta(days=60),
                is_active=True
            )
            
            cls.batches_with_assignments.append((batch, assignment, container))
    
    def test_finance_report_performance_10k_events(self):
        """
        Finance report with 10,000 events should complete < 2s.
        
        Tests realistic scenario with proper relationships:
        - 10 batches with BatchContainerAssignments
        - 5 feed types with FeedPurchases
        - Geographic distribution across 6 areas, 2 geographies
        - Date spread across 365 days
        - Proper cost calculation from purchase data
        """
        # Bulk create 10k feeding events with realistic distribution
        events = []
        base_date = timezone.now().date()
        
        for i in range(10000):
            # Distribute across batches, feeds, and dates realistically
            batch, assignment, container = self.batches_with_assignments[i % 10]
            feed, purchase, cost_per_kg = self.feeds_with_purchases[i % 5]
            
            # Vary amounts and costs
            amount_kg = Decimal('8.0') + (Decimal(i % 20) / 10)  # 8.0 to 9.9 kg
            calculated_cost = amount_kg * cost_per_kg
            
            events.append(FeedingEvent(
                batch=batch,
                batch_assignment=assignment,
                container=container,
                feed=feed,
                feeding_date=base_date - timedelta(days=(i % 365)),
                feeding_time=timezone.now().time(),
                amount_kg=amount_kg,
                batch_biomass_kg=assignment.biomass_kg,
                feed_cost=calculated_cost,
                method=['MANUAL', 'AUTOMATIC', 'BROADCAST'][i % 3]
            ))
        
        # Bulk create with batching
        FeedingEvent.objects.bulk_create(events, batch_size=1000)
        
        # Verify data created
        total_events = FeedingEvent.objects.count()
        self.assertEqual(total_events, 10000)
        
        # Test performance with complex filter
        import time
        start = time.time()
        
        response = self.client.get('/api/v1/inventory/feeding-events/finance_report/', {
            'start_date': (base_date - timedelta(days=90)).isoformat(),
            'end_date': base_date.isoformat(),
            'geography': self.scotland.id,
            'feed__protein_percentage__gte': 40,
            'include_breakdowns': 'true',
            'include_time_series': 'false'
        })
        
        duration = time.time() - start
        
        # Performance assertions
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 2.0, f"Response took {duration:.2f}s, expected < 2s")
        
        # Verify data integrity
        self.assertGreater(response.data['summary']['events_count'], 0)
        self.assertGreater(len(response.data['by_feed_type']), 0)
    
    def test_query_count_optimization(self):
        """Finance report should use < 10 database queries."""
        # Only create 100 events for query count test (faster)
        events = []
        base_date = timezone.now().date()
        
        for i in range(100):
            batch, assignment, container = self.batches_with_assignments[i % 10]
            feed, purchase, cost = self.feeds_with_purchases[i % 5]
            
            events.append(FeedingEvent(
                batch=batch,
                batch_assignment=assignment,
                container=container,
                feed=feed,
                feeding_date=base_date - timedelta(days=(i % 30)),
                feeding_time=timezone.now().time(),
                amount_kg=Decimal('10.0'),
                batch_biomass_kg=assignment.biomass_kg,
                feed_cost=Decimal('50.0'),
                method='MANUAL'
            ))
        
        FeedingEvent.objects.bulk_create(events, batch_size=100)
        
        # Test query count
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import utils
        
        with self.assertNumQueries(10):  # Max 10 queries
            response = self.client.get('/api/v1/inventory/feeding-events/finance_report/', {
                'start_date': (base_date - timedelta(days=30)).isoformat(),
                'end_date': base_date.isoformat(),
                'include_breakdowns': 'true'
            })
            
            self.assertEqual(response.status_code, 200)
```

**Test Execution**:
```bash
# Regular unit tests (fast, run always)
python manage.py test apps.inventory.tests.test_filters
python manage.py test apps.inventory.tests.test_services
python manage.py test apps.inventory.tests.test_finance_api

# Performance tests (slow, run occasionally)
python manage.py test apps.inventory.tests.performance

# Or skip during development
python manage.py test apps.inventory --exclude-tag=performance
```

---

### Task 8.2: Update PRD Documentation
**File**: `aquamind/docs/prd.md`  
**Effort**: 20 minutes

**Update Section 3.1.3** (Inventory Analytics and Reporting):
- Document new finance reporting capabilities
- Update acceptance criteria with specific examples
- Note performance characteristics

---

## Implementation Checklist

### Pre-Implementation
- [x] Feature branch created: `feature/inventory-finance-aggregation-enhancements`
- [ ] Planning document reviewed and approved
- [ ] Test data generation plan confirmed

### Phase 1: Enhanced Filtering (Day 1)
- [ ] Task 1.1: Geographic filters implemented and tested
- [ ] Task 1.2: Feed property filters implemented and tested
- [ ] Task 1.3: Cost filters implemented and tested
- [ ] All filter unit tests passing (target: 100%)

### Phase 2: Aggregation Endpoint (Day 1-2)
- [ ] Task 2.1: Finance report endpoint implemented
- [ ] Task 2.2: Existing summary endpoint enhanced
- [ ] Service layer fully tested (target: 95%+)
- [ ] API integration tests passing

### Phase 3: Documentation (Day 2)
- [ ] Task 3.1: Schema decorators complete
- [ ] Task 3.2: OpenAPI schema regenerated
- [ ] Zero Spectacular warnings
- [ ] Swagger UI documentation verified

### Phase 4: Quality Assurance (Day 2)
- [ ] Task 6.1: Unit tests complete (125+ new tests)
- [ ] Task 6.2: Contract tests complete
- [ ] All inventory tests passing (CI + PostgreSQL)
- [ ] Coverage targets met (95%+ new code)

### Phase 5: Performance (Day 3)
- [ ] Task 8.1: Performance benchmarks passing
- [ ] Query optimization verified (< 10 queries)
- [ ] Response time < 2s for 10k events
- [ ] Caching behavior validated

### Phase 6: Frontend Sync (Day 3)
- [ ] Task 7.1: OpenAPI client regenerated
- [ ] Task 7.2: Frontend documentation complete
- [ ] TypeScript compilation successful
- [ ] No breaking changes to existing frontend code

### Phase 7: Integration Testing (Day 3)
- [ ] Full test suite passing (both DB variants)
- [ ] UAT test cases documented
- [ ] Performance monitoring in place
- [ ] Error handling verified

### Final Validation
- [ ] Code review completed
- [ ] Documentation reviewed
- [ ] UAT scenarios tested
- [ ] Ready for merge to develop

---

## Testing Strategy

### Test Coverage Targets

| Component | Target | Validation Method |
|-----------|--------|-------------------|
| Filter classes | 100% | Unit tests with all filter combinations |
| Service layer | 95%+ | Unit tests with edge cases |
| ViewSet actions | 90%+ | Integration tests + contract tests |
| Performance | N/A | Benchmark tests < 2s for 10k events |

### Test File Organization

```
apps/inventory/tests/
├── test_filters.py                    # Filter unit tests (NEW)
├── test_services/
│   └── test_finance_reporting.py      # Service unit tests (NEW)
├── test_finance_api.py                # API integration tests (NEW)
├── test_performance.py                # Performance benchmarks (NEW)
└── test_viewsets.py                   # Update existing tests

tests/api/
└── test_inventory_finance.py          # Contract tests (NEW)
```

### Test Execution Plan

```bash
# Run new filter tests
python manage.py test apps.inventory.tests.test_filters --settings=aquamind.settings_ci

# Run service layer tests
python manage.py test apps.inventory.tests.test_services.test_finance_reporting --settings=aquamind.settings_ci

# Run API tests
python manage.py test apps.inventory.tests.test_finance_api --settings=aquamind.settings_ci

# Run contract tests
python manage.py test tests.api.test_inventory_finance --settings=aquamind.settings_ci

# Run full inventory suite
python manage.py test apps.inventory --settings=aquamind.settings_ci --parallel 4

# Run with PostgreSQL
python manage.py test apps.inventory --parallel 4

# Performance validation
python manage.py test apps.inventory.tests.test_performance

# Full test suite (final validation)
python manage.py test --settings=aquamind.settings_ci --parallel 4
python manage.py test --parallel 4
```

---

## Code Quality Standards

### Adherence to Guidelines

| Guideline | Reference | Key Points |
|-----------|-----------|------------|
| **Testing** | `testing_guide.md` | - 95%+ coverage for new code<br>- Follow existing test patterns<br>- Use `get_api_url()` helper |
| **API Standards** | `api_standards.md` | - Kebab-case basenames<br>- Complete `@extend_schema` decorators<br>- Zero Spectacular warnings |
| **Code Organization** | Backend rules | - Service layer < 200 LOC per method<br>- ViewSet methods < 50 LOC<br>- Single responsibility principle |

### File Size Limits

| File Type | Max LOC | Action if Exceeded |
|-----------|---------|---------------------|
| Service method | 50 | Extract helper methods |
| ViewSet action | 50 | Delegate to service layer |
| Test class | 300 | Split into multiple test classes |
| Filter class | 200 | Split by concern (geographic, nutritional, cost) |

### Code Review Checklist

**Filters**:
- [ ] All filters follow django-filters conventions
- [ ] Relationship lookups use correct field paths
- [ ] No N+1 query potential in filter definitions
- [ ] All filters have corresponding unit tests

**Service Layer**:
- [ ] Methods are pure (no side effects)
- [ ] Clear separation of concerns
- [ ] Comprehensive docstrings
- [ ] Type hints on all parameters and returns
- [ ] Error handling with specific exceptions

**ViewSet**:
- [ ] `@extend_schema` precedes `@action`
- [ ] All query parameters documented
- [ ] Proper error responses (400, 500)
- [ ] Caching strategy appropriate
- [ ] Logging for debugging

**Tests**:
- [ ] Test data setup is minimal and focused
- [ ] Assertions are specific and meaningful
- [ ] Edge cases covered (empty, large datasets)
- [ ] Performance tests validate requirements
- [ ] Tests follow existing patterns

---

## Performance Requirements

### Response Time Targets

| Dataset Size | Target Response Time | Max Queries |
|--------------|---------------------|-------------|
| 100 events | < 200ms | 5 |
| 1,000 events | < 500ms | 8 |
| 10,000 events | < 2s | 10 |
| 50,000 events | < 5s | 12 |

### Optimization Strategies

1. **Query Optimization**:
   - Use `select_related()` for all foreign keys in SELECT
   - Use `prefetch_related()` for reverse relationships
   - Use `only()` to limit fields if response is large
   - Use `values()` + `annotate()` for aggregations

2. **Caching**:
   - Cache finance report responses for 60 seconds
   - Cache key includes all filter parameters
   - Invalidate cache on feeding event create/update/delete

3. **Database Indexes** (if needed):
   - Compound index on `(feeding_date, container__area__geography)`
   - Index on `feed__protein_percentage`, `feed__fat_percentage`
   - Verify with `EXPLAIN ANALYZE` on large datasets

---

## Risk Mitigation

### Identified Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Query performance with complex joins | High | Comprehensive performance tests + query optimization |
| Breaking existing frontend | High | Maintain backward compatibility, version endpoints if needed |
| Incomplete filter combinations | Medium | Exhaustive integration tests with multi-filter scenarios |
| FIFO cost calculation errors | High | Validate against manual calculations in tests |
| Schema validation failures | Medium | Run `spectacular --validate` in CI |

### Rollback Plan

If issues arise post-deployment:
1. Feature flag can disable new endpoint (return 501 Not Implemented)
2. Frontend falls back to client-side aggregation
3. Revert feature branch merge
4. Fix identified issues in separate hotfix

---

## Success Criteria

### Functional Requirements

- [ ] Finance user can filter feed usage by geography (Scotland/Faroe Islands)
- [ ] Finance user can filter by area and freshwater station
- [ ] Finance user can filter by feed properties (protein %, fat %, brand)
- [ ] Finance user can filter by supplier
- [ ] Finance user can filter by cost ranges
- [ ] Report shows total feed consumption (kg)
- [ ] Report shows total feed cost
- [ ] Report breaks down by feed type
- [ ] Report breaks down by geography/area/container
- [ ] Report includes time series for trend analysis
- [ ] All filter combinations work correctly

### Technical Requirements

- [ ] Zero Spectacular warnings on schema generation
- [ ] All new tests passing (target: 125+ new tests)
- [ ] Coverage ≥ 95% on new service layer code
- [ ] Performance targets met (< 2s for 10k events)
- [ ] Query count optimized (< 10 queries per request)
- [ ] OpenAPI schema updated and validated
- [ ] Frontend client regenerated successfully
- [ ] No breaking changes to existing API

### Quality Requirements

- [ ] Code follows all organizational guidelines
- [ ] All methods < 50 LOC
- [ ] Service file < 400 LOC total
- [ ] Comprehensive error handling
- [ ] Logging for debugging
- [ ] API documentation complete and accurate

---

## Timeline

**Total Estimated Effort**: 12-14 hours

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| **Day 1** | Filtering + Service Layer | 5-6h | Enhanced filters, Service implementation, Unit tests |
| **Day 2** | ViewSet + Schema + Testing | 4-5h | API endpoints, OpenAPI schema, Integration tests |
| **Day 3** | Performance + Frontend Sync | 3h | Performance validation, Frontend sync, Final QA |

**Target Completion**: 3 working days

---

## Appendix A: Example Finance Queries

### Query 1: Scotland Feed Usage - Last Quarter
```bash
GET /api/v1/inventory/feeding-events/finance-report/
  ?start_date=2024-01-01
  &end_date=2024-03-31
  &geography=1
  &include_breakdowns=true
```

### Query 2: High-Protein Feed - Area 3 - Last Month
```bash
GET /api/v1/inventory/feeding-events/finance-report/
  ?start_date=2024-03-01
  &end_date=2024-03-31
  &area=3
  &feed__protein_percentage__gte=45
  &include_time_series=true
```

### Query 3: Premium Brand - High Fat - Scotland - Last 32 Days
```bash
GET /api/v1/inventory/feeding-events/finance-report/
  ?start_date=2024-03-01
  &end_date=2024-04-01
  &geography=1
  &feed__brand=Premium Brand
  &feed__fat_percentage__gte=12
  &include_breakdowns=true
```

### Query 4: Weekly Trends - Station 5 - Specific Supplier
```bash
GET /api/v1/inventory/feeding-events/finance-report/
  ?start_date=2024-01-01
  &end_date=2024-03-31
  &freshwater_station=5
  &feed_purchase__supplier__icontains=AquaFeed Co
  &group_by=week
  &include_time_series=true
```

---

## Appendix B: Database Schema Validation

### Verify Relationships Exist

```sql
-- Verify container → area → geography path
SELECT 
    c.id as container_id,
    c.name as container_name,
    a.id as area_id,
    a.name as area_name,
    g.id as geography_id,
    g.name as geography_name
FROM infrastructure_container c
LEFT JOIN infrastructure_area a ON c.area_id = a.id
LEFT JOIN infrastructure_geography g ON a.geography_id = g.id
LIMIT 5;

-- Verify container → hall → freshwater_station path
SELECT 
    c.id as container_id,
    c.name as container_name,
    h.id as hall_id,
    h.name as hall_name,
    fs.id as station_id,
    fs.name as station_name
FROM infrastructure_container c
LEFT JOIN infrastructure_hall h ON c.hall_id = h.id
LEFT JOIN infrastructure_freshwaterstation fs ON h.freshwater_station_id = fs.id
LIMIT 5;

-- Verify feed properties available
SELECT 
    id,
    name,
    brand,
    protein_percentage,
    fat_percentage,
    size_category
FROM inventory_feed
LIMIT 5;
```

---

## Appendix C: Performance Optimization Checklist

### Query Optimization
- [ ] Use `select_related()` for: container, area, geography, hall, freshwater_station, feed
- [ ] Use `only()` to limit fields if full models not needed
- [ ] Use `values()` + `annotate()` for aggregations (more efficient than Python loops)
- [ ] Avoid `count()` on large querysets (use aggregation results)
- [ ] Use database functions (`TruncDate`, `TruncWeek`) for time bucketing

### Caching Strategy
- [ ] Cache finance reports for 60 seconds (data changes infrequently)
- [ ] Cache key includes all filter parameters (unique per query)
- [ ] Invalidate cache on FeedingEvent create/update/delete signals
- [ ] Cache per-user if permissions affect visibility

### Database Indexes
Check existing indexes cover filter fields:
```sql
-- Verify indexes exist for common filter paths
\d inventory_feedingevent;  -- Check indexes
\d inventory_feed;           -- Check indexes on protein_percentage, fat_percentage
\d infrastructure_container; -- Check indexes on area_id, hall_id
```

If performance tests fail, add compound indexes via migration.

---

## Notes for Implementation

### Code Quality Expectations (UAT-Ready)

This is **production-critical code** going into UAT. Standards are non-negotiable:

1. **Every function has comprehensive docstring** with Args/Returns/Raises
2. **Type hints on all parameters and returns**
3. **Error handling for all edge cases** (empty data, invalid params, DB errors)
4. **Logging at appropriate levels** (INFO for reports, ERROR for failures)
5. **No TODO comments or placeholder code**
6. **No print statements** (use logger)
7. **Consistent naming** following project conventions
8. **DRY principle** - extract reusable logic

### Testing Expectations

- Tests must be **deterministic** (no flaky tests)
- Tests must be **fast** (< 5 seconds per test file)
- Tests must be **isolated** (no shared state between tests)
- Test data must be **minimal** (only what's needed for assertion)
- Assertions must be **specific** (not just "response.status_code == 200")

### Documentation Expectations

- Every public method documented
- Complex logic explained with inline comments
- API endpoint usage examples in docstrings
- Performance characteristics noted where relevant

---

**Last Updated**: 2025-10-10  
**Author**: AI Assistant + Aquarian247  
**Review Status**: Pending Approval

