# Executive Forecast Dashboard Implementation Plan

**Version**: 1.0  
**Last Updated**: December 10, 2025  
**Owner**: Engineering (Solo Dev)  
**Target Repository**: `aquarian247/AquaMind`  
**Estimated Duration**: 4-5 days (Backend: 2 days; Frontend: 2-3 days)  
**Priority**: High (CFO Request - Steering Committee Dec 2025)

---

## Executive Summary

This plan implements a **portfolio-level forecast dashboard** enabling executives to visualize upcoming harvests and sea-transfers across all batches. It leverages the existing Batch Growth Assimilation (Phase 8/8.5) and Production Planner infrastructure—no new models or heavy computation required.

**CFO Value Proposition**: "When will batches be ready? How many harvests in Q2? Which sea-transfers are delayed?"

**Key Deliverables**:
1. **Harvest Forecast API**: Aggregated view of batches approaching harvest weight
2. **Sea-Transfer Forecast API**: Batches nearing smolt stage for freshwater→sea transition
3. **Dashboard Cards**: Executive-friendly summary with drill-down capability
4. **Confidence Indicators**: Flag uncertain projections based on assimilation confidence scores

---

## Prerequisites

- [x] Phase 8: Planner-Assimilation Integration (triggers, variance-from-actual)
- [x] Phase 8.5: FCR precision, projection-preview endpoint
- [x] Scenario projections (`ProjectionDay` model with TGC-based weight curves)
- [x] Activity templates with `WEIGHT_THRESHOLD` triggers
- [ ] Executive Dashboard skeleton (currently on hold)

---

## Architecture Overview

### Data Sources (Already Exist)

| Source | Model | Relevant Fields |
|--------|-------|-----------------|
| Weight Projections | `scenario_projectionday` | `batch`, `day_date`, `avg_weight_g`, `projection_run` |
| Planned Activities | `planning_plannedactivity` | `activity_type`, `batch`, `due_date`, `status`, `scenario` |
| Actual States | `batch_actualdailyassignmentstate` | `avg_weight_g`, `confidence_scores`, `population` |
| Batch Info | `batch_batch` | `lifecycle_stage`, `batch_number`, `species` |
| Facilities | `infrastructure_*` | Station/area geography for filtering |

### Query Strategy

```
Harvest Forecast = 
  ProjectionDay WHERE avg_weight_g >= harvest_threshold (species-specific)
  GROUP BY batch
  FIRST day_date per batch (earliest harvest-ready date)
  + confidence from ActualDailyAssignmentState
  + existing HARVEST PlannedActivity (if any)

Sea-Transfer Forecast = 
  Batch WHERE lifecycle_stage approaching 'Smolt'
  OR PlannedActivity WHERE activity_type = 'SEA_TRANSFER'
  + days until stage change (from assimilation velocity)
  + confidence scoring
```

---

## Phase 1: Backend Aggregation Endpoints (2 days)

### 1.1 Harvest Forecast Endpoint

**Endpoint**: `GET /api/v1/dashboard/harvest-forecast/`

**Query Parameters**:
- `facility_id` (optional): Filter by freshwater station or farming area
- `species_id` (optional): Filter by species
- `from_date`, `to_date` (optional): Date range for projections
- `min_confidence` (optional, default 0.5): Exclude low-confidence projections

**Response Schema**:
```json
{
  "summary": {
    "total_batches": 45,
    "harvest_ready_count": 12,
    "avg_days_to_harvest": 67,
    "total_projected_biomass_tonnes": 2450.5
  },
  "upcoming": [
    {
      "batch_id": 123,
      "batch_number": "B-2024-001",
      "species": "Atlantic Salmon",
      "facility": "Norðtoftir",
      "current_weight_g": 4200,
      "target_weight_g": 5000,
      "projected_harvest_date": "2026-03-15",
      "days_until_harvest": 95,
      "projected_biomass_kg": 52000,
      "confidence": 0.92,
      "confidence_factors": {
        "weight": 0.95,
        "temperature": 0.88,
        "mortality": 0.93
      },
      "planned_activity_id": 456,  // null if no HARVEST planned yet
      "planned_activity_status": "PENDING",
      "variance_days": 3  // actual vs planned (positive = ahead)
    }
  ],
  "by_quarter": {
    "Q1_2026": {"count": 5, "biomass_tonnes": 650},
    "Q2_2026": {"count": 7, "biomass_tonnes": 890}
  }
}
```

**Implementation**:
```python
# apps/dashboard/api/viewsets/forecast_viewset.py

class HarvestForecastViewSet(viewsets.ViewSet):
    """
    Executive dashboard endpoint for harvest forecasting.
    Aggregates projection data across all batches.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def harvest(self, request):
        # Get species-specific harvest thresholds
        thresholds = self._get_harvest_thresholds()
        
        # Query projections approaching harvest weight
        upcoming = []
        for batch in Batch.objects.filter(status='ACTIVE'):
            projection = self._get_harvest_projection(batch, thresholds)
            if projection:
                upcoming.append(projection)
        
        # Sort by projected date, add quarterly aggregates
        upcoming.sort(key=lambda x: x['projected_harvest_date'])
        
        return Response({
            'summary': self._compute_summary(upcoming),
            'upcoming': upcoming,
            'by_quarter': self._aggregate_by_quarter(upcoming)
        })
```

### 1.2 Sea-Transfer Forecast Endpoint

**Endpoint**: `GET /api/v1/dashboard/sea-transfer-forecast/`

**Response Schema**:
```json
{
  "summary": {
    "total_freshwater_batches": 28,
    "transfer_ready_count": 8,
    "avg_days_to_transfer": 42
  },
  "upcoming": [
    {
      "batch_id": 789,
      "batch_number": "B-2024-042",
      "current_stage": "Parr",
      "target_stage": "Smolt",
      "current_facility": "Hósvík Freshwater",
      "target_facility": "Hvannasund",  // from planned activity or default
      "projected_transfer_date": "2025-06-01",
      "days_until_transfer": 45,
      "smolt_criteria": {
        "weight_g": {"current": 85, "target": 100, "met": false},
        "photoperiod_days": {"current": 28, "target": 42, "met": false}
      },
      "confidence": 0.85,
      "planned_activity_id": 321,
      "workflow_id": null  // populated when transfer initiated
    }
  ],
  "by_month": {
    "2025-06": {"count": 4},
    "2025-07": {"count": 4}
  }
}
```

**Implementation Notes**:
- Smolt readiness combines weight threshold + lifecycle stage
- Use `ActivityTemplate` with `STAGE_CHANGE` trigger type for auto-detection
- Sea-transfer forecast requires freshwater facility filter (only FW batches)

### 1.3 Configuration: Harvest Thresholds

Add species-specific harvest thresholds (leverage existing `Species` model):

```python
# Option A: Add to Species model (preferred - no migration if using JSONField)
# Already has flexibility via existing fields

# Option B: Settings-based (quick implementation)
# aquamind/settings.py
HARVEST_THRESHOLDS = {
    'atlantic_salmon': {'min_weight_g': 4500, 'target_weight_g': 5000},
    'rainbow_trout': {'min_weight_g': 2500, 'target_weight_g': 3000},
    'default': {'min_weight_g': 4000, 'target_weight_g': 5000}
}

SEA_TRANSFER_CRITERIA = {
    'atlantic_salmon': {'min_weight_g': 80, 'target_stage': 'Smolt'},
    'default': {'min_weight_g': 100, 'target_stage': 'Smolt'}
}
```

### 1.4 Tests

**File**: `apps/dashboard/tests/test_forecast_endpoints.py`

```python
class TestHarvestForecastEndpoint(APITestCase):
    def test_harvest_forecast_returns_upcoming_batches(self):
        """Batches near harvest weight should appear in forecast."""
        
    def test_harvest_forecast_filters_by_facility(self):
        """Facility filter should restrict results."""
        
    def test_harvest_forecast_confidence_threshold(self):
        """Low-confidence batches should be excluded with min_confidence."""
        
    def test_harvest_forecast_quarterly_aggregation(self):
        """by_quarter should correctly group batches."""

class TestSeaTransferForecastEndpoint(APITestCase):
    def test_sea_transfer_forecast_smolt_criteria(self):
        """Batches meeting smolt criteria should appear."""
        
    def test_sea_transfer_only_freshwater_batches(self):
        """Only FW batches should appear in sea-transfer forecast."""
```

---

## Phase 2: Frontend Dashboard Components (2-3 days)

### 2.1 Dashboard Route Setup

**Location**: `client/src/features/dashboard/`

```typescript
// routes.tsx
{
  path: '/dashboard/executive',
  element: <ExecutiveDashboardPage />,
  children: [
    { path: 'harvest', element: <HarvestForecastView /> },
    { path: 'transfers', element: <SeaTransferForecastView /> },
  ]
}
```

### 2.2 Harvest Forecast Card

**Component**: `<HarvestForecastCard />`

Features:
- Summary stats (total ready, avg days, total biomass)
- Mini timeline showing next 90 days
- Color-coded confidence (green ≥0.8, yellow 0.5-0.8, red <0.5)
- Click to drill-down to batch detail

```tsx
// client/src/features/dashboard/components/HarvestForecastCard.tsx

export function HarvestForecastCard() {
  const { data, isLoading } = useHarvestForecast();
  
  return (
    <Card className="p-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Fish className="h-5 w-5" />
          Harvest Forecast
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard 
            label="Ready for Harvest" 
            value={data?.summary.harvest_ready_count} 
          />
          <StatCard 
            label="Avg Days to Harvest" 
            value={data?.summary.avg_days_to_harvest} 
          />
          <StatCard 
            label="Projected Biomass" 
            value={`${data?.summary.total_projected_biomass_tonnes}t`} 
          />
        </div>
        <HarvestTimeline batches={data?.upcoming.slice(0, 10)} />
      </CardContent>
    </Card>
  );
}
```

### 2.3 Sea-Transfer Forecast Card

**Component**: `<SeaTransferForecastCard />`

Features:
- Freshwater batches approaching smolt stage
- Smolt criteria progress bars (weight, photoperiod)
- Monthly grouping for capacity planning
- Link to Transfer Workflow creation

### 2.4 Timeline Visualization

**Component**: `<ForecastTimeline />`

- Horizontal timeline (next 90/180 days)
- Batches as markers with tooltip on hover
- Color by confidence level
- Grouping toggle (by facility, by species)

```tsx
// Use recharts or similar for timeline
import { ResponsiveContainer, ScatterChart, XAxis, YAxis, Scatter, Tooltip } from 'recharts';

export function ForecastTimeline({ data, type }: ForecastTimelineProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
        <XAxis 
          dataKey="days_until" 
          type="number" 
          domain={[0, 90]}
          tickFormatter={(d) => `${d}d`}
        />
        <YAxis dataKey="biomass_kg" hide />
        <Tooltip content={<BatchTooltip />} />
        <Scatter 
          data={data} 
          fill={(d) => getConfidenceColor(d.confidence)}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
```

### 2.5 Quarterly Summary View

**Component**: `<QuarterlySummaryTable />`

| Quarter | Batches | Est. Biomass | Avg Confidence | Actions |
|---------|---------|--------------|----------------|---------|
| Q1 2026 | 5 | 650t | 0.89 | [View Details] |
| Q2 2026 | 7 | 890t | 0.82 | [View Details] |

### 2.6 API Hooks

```typescript
// client/src/features/dashboard/api/api.ts

export function useHarvestForecast(filters?: ForecastFilters) {
  return useQuery({
    queryKey: ['dashboard', 'harvest-forecast', filters],
    queryFn: () => apiClient.get('/api/v1/dashboard/harvest-forecast/', { params: filters }),
  });
}

export function useSeaTransferForecast(filters?: ForecastFilters) {
  return useQuery({
    queryKey: ['dashboard', 'sea-transfer-forecast', filters],
    queryFn: () => apiClient.get('/api/v1/dashboard/sea-transfer-forecast/', { params: filters }),
  });
}
```

### 2.7 Frontend Tests

**File**: `client/src/features/dashboard/__tests__/forecast.test.tsx`

```typescript
describe('HarvestForecastCard', () => {
  it('renders summary statistics', async () => {});
  it('displays timeline with upcoming batches', async () => {});
  it('shows confidence color coding', async () => {});
  it('handles loading state', async () => {});
  it('handles empty forecast gracefully', async () => {});
});

describe('SeaTransferForecastCard', () => {
  it('shows smolt criteria progress', async () => {});
  it('filters to freshwater batches only', async () => {});
});
```

---

## Phase 3: Integration & Polish (0.5 days)

### 3.1 Navigation Integration

- Add "Executive Dashboard" to main nav (admin/superuser only)
- Add quick-links from Batch Detail page

### 3.2 Performance Optimization

- Cache forecast queries (5-min TTL via Redis)
- Pagination for large batch counts (>100)
- Lazy-load drill-down details

### 3.3 Access Control

```python
# Only executives/admins see dashboard
class IsExecutiveUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or 
            request.user.groups.filter(name='Executives').exists()
        )
```

---

## Files to Create/Modify

### Backend (New)
- `apps/dashboard/__init__.py`
- `apps/dashboard/api/__init__.py`
- `apps/dashboard/api/viewsets/__init__.py`
- `apps/dashboard/api/viewsets/forecast_viewset.py`
- `apps/dashboard/api/routers.py`
- `apps/dashboard/tests/__init__.py`
- `apps/dashboard/tests/test_forecast_endpoints.py`
- `aquamind/api/router.py` (add dashboard routes)

### Frontend (New)
- `client/src/features/dashboard/api/api.ts`
- `client/src/features/dashboard/api/types.ts`
- `client/src/features/dashboard/components/HarvestForecastCard.tsx`
- `client/src/features/dashboard/components/SeaTransferForecastCard.tsx`
- `client/src/features/dashboard/components/ForecastTimeline.tsx`
- `client/src/features/dashboard/components/QuarterlySummaryTable.tsx`
- `client/src/features/dashboard/pages/ExecutiveDashboardPage.tsx`
- `client/src/features/dashboard/__tests__/forecast.test.tsx`

### Modified
- `aquamind/settings.py` (harvest thresholds config)
- `client/src/App.tsx` (dashboard route)
- `client/src/components/layout/Sidebar.tsx` (nav link)

---

## Success Criteria

1. **Harvest Forecast**: Executives can see all batches approaching harvest weight with projected dates and confidence scores
2. **Sea-Transfer Forecast**: Freshwater managers can plan transfers based on smolt readiness
3. **Confidence Visibility**: Low-confidence projections are flagged (based on assimilation data quality)
4. **Drill-Down**: Click any batch to see detailed variance and projection history
5. **Performance**: Dashboard loads in <2 seconds for 50+ active batches
6. **Mobile**: Responsive cards work on tablet for field access

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Projection accuracy depends on TGC model quality | Medium | Show confidence scores prominently; link to model tuning |
| Large batch counts slow queries | Low | Pagination + Redis caching |
| Species without harvest thresholds | Low | Default thresholds + admin config UI |
| Executives unfamiliar with confidence scores | Medium | Add tooltip explanations; training doc |

---

## Future Enhancements (Out of Scope)

- **Harvest scheduling optimization**: Auto-suggest harvest order based on facility capacity
- **Market price integration**: Projected revenue per harvest batch
- **Weather-adjusted projections**: Adjust sea-transfer timing based on weather forecasts
- **Export to Excel**: CFO-friendly reports for board meetings
- **Alerts**: Email/Slack when batch approaches harvest threshold

---

## References

- PRD Section 3.2: Operational Planning
- Batch Growth Assimilation Plan: Phase 8/8.5
- Planning and Workflows Primer: `docs/user_guides/planning_and_workflows_primer.md`
- Existing Dashboard concepts: `docs/progress/` (on hold)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-10 | 1.0 | Initial draft based on CFO request at Steering Committee |


