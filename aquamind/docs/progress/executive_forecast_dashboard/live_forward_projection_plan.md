# Live Forward Projection & Executive Forecast Enhancement

## Executive Summary

Enhance the executive forecast dashboard with **live forward projections** that predict actual harvest and transfer dates based on current reality (ActualDailyAssignmentState) rather than original plans (ScenarioProjection). Integrate PlannedActivity records as the authoritative source for confirmed operational plans, with projections providing supporting analytics.

---

## Problem Statement

### Current Limitations

1. **Static Scenario Projections**: Original scenario projections show "the plan" from batch creation, but reality diverges over time
2. **No Revised Forecast**: When a batch is 25% behind plan, there's no system to answer "when will we ACTUALLY harvest?"
3. **Missing Operational Context**: PlannedActivity records (HARVEST, TRANSFER) created by operations staff aren't surfaced in executive forecasts
4. **Batch-Level Only**: Current approach ignores that containers within a batch grow at different rates

### Business Impact

- **Contract Risk**: Sales agreements specify weight (e.g., 150,000 fish at 5kg). Harvesting overweight (5.9kg) means giving away ~18% of biomass value
- **Planning Blind Spots**: Executives can't see revised timelines based on actual performance
- **Operational Disconnect**: Field knowledge (PlannedActivity) not connected to executive visibility

---

## Proposed Solution

### Three-Tier Forecast Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXECUTIVE FORECAST DASHBOARD                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TIER 1: PLANNED ACTIVITIES (Authoritative)                             │
│  ─────────────────────────────────────────                              │
│  Source: PlannedActivity where activity_type in ('HARVEST', 'TRANSFER') │
│  These are CONFIRMED plans made by operations staff                     │
│  Flag: "PLANNED" with due_date                                          │
│                                                                          │
│  TIER 2: LIVE FORWARD PROJECTIONS (Predictive)                          │
│  ─────────────────────────────────────────────                          │
│  Source: Projection from latest ActualDailyAssignmentState              │
│  "Based on current trajectory, when will threshold be reached?"         │
│  Flag: "PROJECTED" with confidence indicator                            │
│                                                                          │
│  TIER 3: NEEDS ATTENTION (Advisory)                                     │
│  ─────────────────────────────────────────                              │
│  Containers/batches approaching threshold WITHOUT a PlannedActivity     │
│  Flag: "NEEDS PLANNING"                                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### New Data Model: LiveForwardProjection

```python
class LiveForwardProjection(models.Model):
    """
    Forward projections from latest actual state.
    
    TimescaleDB hypertable with 7-day retention policy.
    Recomputed daily. Previous days' projections are irrelevant.
    
    Stored at CONTAINER level (BatchContainerAssignment) because:
    - Containers have different temperatures, survival rates, growth
    - Harvest decisions are made per-container
    - Sales contracts require specific weights - container selection matters
    """
    
    # Partitioning key for TimescaleDB
    computed_date = models.DateField(
        db_index=True,
        help_text="When this projection was computed (for retention policy)"
    )
    
    # What we're projecting for - CONTAINER level, not batch level
    assignment = models.ForeignKey(
        'batch.BatchContainerAssignment',
        on_delete=models.CASCADE,
        related_name='live_projections'
    )
    
    # Denormalized for query efficiency
    batch = models.ForeignKey('batch.Batch', on_delete=models.CASCADE)
    container = models.ForeignKey('infrastructure.Container', on_delete=models.CASCADE)
    
    # The future date being projected
    projection_date = models.DateField()
    day_number = models.IntegerField()
    
    # Projected values
    projected_weight_g = models.DecimalField(max_digits=10, decimal_places=2)
    projected_population = models.IntegerField()
    projected_biomass_kg = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Model inputs used (for transparency/debugging)
    temperature_used = models.DecimalField(max_digits=5, decimal_places=2)
    tgc_value_used = models.DecimalField(max_digits=8, decimal_places=4)
    
    class Meta:
        db_table = 'batch_liveforwardprojection'
        indexes = [
            models.Index(fields=['computed_date', 'assignment']),
            models.Index(fields=['batch', 'computed_date']),
            models.Index(fields=['projection_date', 'projected_weight_g']),
        ]
        # Note: TimescaleDB retention policy set in migration


class ContainerForecastSummary(models.Model):
    """
    Denormalized summary of live projection results per container.
    Updated after each projection run. Used for fast dashboard queries.
    """
    assignment = models.OneToOneField(
        'batch.BatchContainerAssignment',
        on_delete=models.CASCADE,
        primary_key=True
    )
    
    # Current state (from latest ActualDailyAssignmentState)
    current_weight_g = models.DecimalField(max_digits=10, decimal_places=2)
    current_population = models.IntegerField()
    current_biomass_kg = models.DecimalField(max_digits=12, decimal_places=2)
    state_date = models.DateField()
    
    # Projection results
    projected_harvest_date = models.DateField(null=True, blank=True)
    days_to_harvest = models.IntegerField(null=True, blank=True)
    projected_harvest_weight_g = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    
    projected_transfer_date = models.DateField(null=True, blank=True)
    days_to_transfer = models.IntegerField(null=True, blank=True)
    
    # Variance from original plan
    original_harvest_date = models.DateField(null=True, blank=True)
    harvest_variance_days = models.IntegerField(null=True, blank=True)  # + = behind
    
    # Flags
    has_planned_harvest = models.BooleanField(default=False)
    has_planned_transfer = models.BooleanField(default=False)
    needs_planning_attention = models.BooleanField(default=False)
    
    last_computed = models.DateTimeField(auto_now=True)
```

### TimescaleDB Configuration

```sql
-- Create hypertable partitioned by computed_date
SELECT create_hypertable(
    'batch_liveforwardprojection', 
    'computed_date',
    chunk_time_interval => INTERVAL '1 day'
);

-- Aggressive retention: only keep last 7 days of projections
SELECT add_retention_policy(
    'batch_liveforwardprojection', 
    INTERVAL '7 days'
);

-- Optional compression for the few days we keep
SELECT add_compression_policy(
    'batch_liveforwardprojection', 
    INTERVAL '2 days'
);
```

### Data Volume Estimate

| Metric | Value |
|--------|-------|
| Active batches | ~100 |
| Containers per batch (avg) | ~6 |
| Active container assignments | ~600 |
| Projection days per container | ~300 (remaining to harvest) |
| Rows per day | ~180,000 |
| With 7-day retention | ~1.26M rows max |
| Row size (estimated) | ~100 bytes |
| **Total storage** | **~126 MB** |

This is trivial for TimescaleDB.

---

## Computation Engine

### Daily Celery Task

```python
@celery.task
def compute_all_live_forward_projections():
    """
    Run daily at 3am (after ActualDailyAssignmentState is updated).
    
    For each active container assignment:
    1. Get latest ActualDailyAssignmentState
    2. Get the batch's pinned scenario's growth models
    3. Project forward until end of scenario or max days
    4. Store projections and update ContainerForecastSummary
    """
    from apps.batch.models import BatchContainerAssignment, ActualDailyAssignmentState
    from apps.batch.services.projection_engine import LiveProjectionEngine
    
    active_assignments = BatchContainerAssignment.objects.filter(
        is_active=True,
        batch__status='ACTIVE'
    ).select_related(
        'batch__pinned_projection_run__scenario',
        'container'
    )
    
    engine = LiveProjectionEngine()
    
    for assignment in active_assignments:
        try:
            engine.compute_and_store(assignment)
        except Exception as e:
            logger.error(f"Failed to project {assignment}: {e}")
            continue
    
    # Update summary table
    update_container_forecast_summaries()


class LiveProjectionEngine:
    """
    Computes forward projections from current actual state.
    """
    
    def compute_and_store(self, assignment: BatchContainerAssignment):
        # 1. Get latest actual state for this container assignment
        latest_state = ActualDailyAssignmentState.objects.filter(
            assignment=assignment
        ).order_by('-date').first()
        
        if not latest_state:
            return  # No actuals yet
        
        # 2. Get growth models from pinned scenario
        batch = assignment.batch
        projection_run = batch.pinned_projection_run
        
        if not projection_run:
            return  # No scenario pinned
        
        scenario = projection_run.scenario
        tgc_model = scenario.tgc_model
        mortality_model = scenario.mortality_model
        temp_profile = scenario.temperature_profile  # Or use actual temps
        
        # 3. Determine projection parameters
        start_date = latest_state.date
        start_day = latest_state.day_number
        end_day = scenario.duration_days
        
        current_weight = float(latest_state.avg_weight_g)
        current_pop = latest_state.population
        
        # 4. Project forward
        projections = []
        today = date.today()
        
        for day_num in range(start_day + 1, end_day + 1):
            days_forward = day_num - start_day
            proj_date = start_date + timedelta(days=days_forward)
            
            # Skip dates in the past (shouldn't happen but safety check)
            if proj_date <= today:
                continue
            
            # Get temperature for this day
            temp = self._get_temperature(temp_profile, day_num, assignment.container)
            
            # Calculate growth using TGC model
            tgc_value = self._get_tgc(tgc_model, current_weight)
            growth = self._calculate_tgc_growth(current_weight, temp, tgc_value)
            
            # Calculate mortality
            mortality = self._calculate_mortality(mortality_model, day_num, current_pop)
            
            # Update state
            current_weight += growth
            current_pop -= mortality
            current_biomass = (current_weight * current_pop) / 1000
            
            projections.append(LiveForwardProjection(
                computed_date=today,
                assignment=assignment,
                batch=batch,
                container=assignment.container,
                projection_date=proj_date,
                day_number=day_num,
                projected_weight_g=Decimal(str(round(current_weight, 2))),
                projected_population=max(0, current_pop),
                projected_biomass_kg=Decimal(str(round(current_biomass, 2))),
                temperature_used=Decimal(str(temp)),
                tgc_value_used=Decimal(str(tgc_value)),
            ))
        
        # 5. Bulk insert
        LiveForwardProjection.objects.bulk_create(projections, batch_size=1000)
    
    def _get_temperature(self, profile, day_num, container):
        """Get temperature from profile or actual sensor data."""
        # Prefer actual recent temperature from container's sensors
        # Fall back to profile temperature for future days
        # Implementation depends on environmental data availability
        return profile.get_temperature_for_day(day_num)
    
    def _get_tgc(self, tgc_model, weight):
        """Get TGC value, accounting for stage-based overrides."""
        return tgc_model.get_tgc_for_weight(weight)
    
    def _calculate_tgc_growth(self, weight, temp, tgc):
        """
        TGC growth formula:
        W2 = (W1^(1/3) + (TGC/1000) * temp * days)^3
        For 1 day: growth = W2 - W1
        """
        w1_cuberoot = weight ** (1/3)
        w2_cuberoot = w1_cuberoot + (tgc / 1000) * temp * 1
        w2 = w2_cuberoot ** 3
        return w2 - weight
    
    def _calculate_mortality(self, model, day_num, population):
        """Calculate daily mortality based on model."""
        daily_rate = model.get_daily_rate(day_num)
        return int(population * daily_rate)
```

---

## Executive Dashboard Integration

### Harvest Forecast Endpoint (Revised)

```python
@action(detail=False, methods=['get'], url_path='harvest')
def harvest_forecast(self, request):
    """
    Returns harvest forecast combining:
    1. PLANNED: PlannedActivity(type=HARVEST) - authoritative
    2. PROJECTED: Live forward projections - predictive
    3. NEEDS_ATTENTION: Approaching threshold without plan
    """
    geography_id = request.query_params.get('geography_id')
    
    # TIER 1: Planned harvests from PlannedActivity
    planned_harvests = PlannedActivity.objects.filter(
        activity_type='HARVEST',
        status__in=['PENDING', 'IN_PROGRESS'],
    ).select_related('batch', 'container', 'scenario')
    
    if geography_id:
        planned_harvests = planned_harvests.filter(
            Q(batch__batch_assignments__container__area__geography_id=geography_id) |
            Q(container__area__geography_id=geography_id)
        ).distinct()
    
    # TIER 2 & 3: From ContainerForecastSummary
    forecasts = ContainerForecastSummary.objects.filter(
        assignment__is_active=True,
        assignment__batch__status='ACTIVE',
        projected_harvest_date__isnull=False,
    ).select_related(
        'assignment__batch__species',
        'assignment__container__area',
    )
    
    if geography_id:
        forecasts = forecasts.filter(
            assignment__container__area__geography_id=geography_id
        )
    
    # Build response
    results = []
    
    # Add planned harvests (TIER 1)
    for activity in planned_harvests:
        results.append({
            'tier': 'PLANNED',
            'batch_id': activity.batch_id,
            'batch_number': activity.batch.batch_number,
            'container_id': activity.container_id,
            'container_name': activity.container.name if activity.container else 'Batch-level',
            'planned_date': activity.due_date,
            'status': activity.status,
            'source': 'PlannedActivity',
            'notes': activity.notes,
        })
    
    # Add projections (TIER 2) and needs-attention (TIER 3)
    planned_batch_ids = {a.batch_id for a in planned_harvests}
    
    for forecast in forecasts:
        tier = 'PROJECTED' if forecast.assignment.batch_id in planned_batch_ids else 'NEEDS_ATTENTION'
        
        results.append({
            'tier': tier,
            'batch_id': forecast.assignment.batch_id,
            'batch_number': forecast.assignment.batch.batch_number,
            'container_id': forecast.assignment.container_id,
            'container_name': forecast.assignment.container.name,
            'current_weight_g': forecast.current_weight_g,
            'projected_harvest_date': forecast.projected_harvest_date,
            'projected_harvest_weight_g': forecast.projected_harvest_weight_g,
            'days_to_harvest': forecast.days_to_harvest,
            'variance_days': forecast.harvest_variance_days,
            'source': 'LiveForwardProjection',
        })
    
    # Sort: PLANNED first, then by date
    tier_order = {'PLANNED': 0, 'PROJECTED': 1, 'NEEDS_ATTENTION': 2}
    results.sort(key=lambda x: (
        tier_order.get(x['tier'], 99),
        x.get('planned_date') or x.get('projected_harvest_date') or date.max
    ))
    
    return Response({
        'summary': {
            'planned_count': len([r for r in results if r['tier'] == 'PLANNED']),
            'projected_count': len([r for r in results if r['tier'] == 'PROJECTED']),
            'needs_attention_count': len([r for r in results if r['tier'] == 'NEEDS_ATTENTION']),
        },
        'forecasts': results,
    })
```

---

## Container-Level Considerations

### Why Container-Level Matters

```
BATCH: FAR-2024-001 (Atlantic Salmon)
├── Ring A: 4,800g avg - Ready for 5kg contract ✓
├── Ring B: 5,200g avg - Already over 5kg! Needs immediate harvest
├── Ring C: 4,200g avg - 3 weeks to 5kg
└── Ring D: 4,500g avg - 2 weeks to 5kg

Sales Contract: 150,000 fish at 5.0kg ± 0.2kg
Action: Harvest Ring A first, then D, then C. 
        Ring B needs separate buyer (premium size) or discount.
```

### Commercial Weight Matching

```python
class ContractMatcher:
    """
    Matches container forecasts to sales contracts.
    Helps operations decide harvest sequence.
    """
    
    def find_containers_for_contract(
        self, 
        target_weight_kg: float,
        tolerance_kg: float,
        target_date: date,
        min_fish_count: int
    ) -> List[dict]:
        """
        Find containers that will be at target weight ± tolerance 
        around the target date.
        """
        min_weight = (target_weight_kg - tolerance_kg) * 1000  # to grams
        max_weight = (target_weight_kg + tolerance_kg) * 1000
        
        # Find containers projected to be in range
        matches = LiveForwardProjection.objects.filter(
            computed_date=date.today(),
            projection_date__range=(
                target_date - timedelta(days=7),
                target_date + timedelta(days=7)
            ),
            projected_weight_g__gte=min_weight,
            projected_weight_g__lte=max_weight,
        ).select_related(
            'assignment__batch',
            'container'
        ).order_by('projection_date')
        
        # Group by container and find best date for each
        container_matches = {}
        for proj in matches:
            key = proj.assignment_id
            if key not in container_matches:
                container_matches[key] = {
                    'container': proj.container,
                    'batch': proj.assignment.batch,
                    'best_date': proj.projection_date,
                    'weight_at_date': proj.projected_weight_g,
                    'population': proj.projected_population,
                }
        
        return list(container_matches.values())
```

---

## Growth Chart Enhancement (4th Line)

### Frontend Changes

Add "Live Forward Projection" as a 4th data series:

```typescript
// In BatchGrowthChart.tsx
interface GrowthDataSeries {
  growthSamples: DataPoint[];        // Actual measurements (dots)
  scenarioProjection: DataPoint[];   // Original plan (green dashed)
  actualDailyState: DataPoint[];     // Reality to date (orange solid)
  liveForwardProjection: DataPoint[]; // NEW: Projection from today (blue dotted)
}

// Fetch live forward projection
const { data: liveProjection } = useQuery({
  queryKey: ['live-forward-projection', assignmentId],
  queryFn: () => ApiService.getLiveForwardProjection(assignmentId),
});
```

### Visual Design

```
Legend:
  ● Growth Samples (measured weights)
  ─ ─ Scenario Projection (original plan)  
  ─── Actual Daily State (reality to date)
  ····· Live Forward Projection (revised forecast)
```

Color scheme:
- Growth Samples: Blue dots
- Scenario Projection: Green dashed
- Actual Daily State: Orange solid
- Live Forward Projection: Purple dotted

---

## Implementation Phases

### Phase 1: Data Model & Computation Engine
- [ ] Create `LiveForwardProjection` model with TimescaleDB hypertable
- [ ] Create `ContainerForecastSummary` model
- [ ] Implement `LiveProjectionEngine` 
- [ ] Create daily Celery task
- [ ] Add retention policy migration

### Phase 2: Executive Dashboard Integration
- [ ] Refactor harvest forecast endpoint to use 3-tier approach
- [ ] Refactor sea-transfer forecast endpoint similarly
- [ ] Add PlannedActivity as primary data source
- [ ] Update frontend to show tier badges (PLANNED, PROJECTED, NEEDS_ATTENTION)

### Phase 3: Growth Chart Enhancement
- [ ] Add API endpoint for live forward projection data
- [ ] Add 4th line to growth chart
- [ ] Add toggle controls for each data series

### Phase 4: Contract Matching (Future)
- [ ] Sales contract model integration
- [ ] Container recommendation for contracts
- [ ] Weight-at-date queries

---

## Success Criteria

1. **Accuracy**: Live forward projections should be within ±10% of actual harvest weight when compared retrospectively
2. **Timeliness**: Daily projection refresh completed before 6am
3. **Visibility**: Executives can see:
   - All planned harvests/transfers with dates
   - Projected dates for batches without plans
   - Variance from original plan (ahead/behind)
4. **Commercial Value**: Operations can identify which containers match upcoming contracts

---

## Open Questions

1. **Temperature Source**: Should live projections use actual sensor temps (more accurate) or scenario profile temps (more predictable)?
2. **Mortality Model**: Use fixed scenario model or adapt based on actual mortality trends?
3. **Batch vs Container Aggregation**: Should executive summary show batch-level (simpler) or container-level (more accurate)?
4. **Projection Horizon**: How far forward to project? Until scenario end? Fixed days? Until weight threshold?

---

## Related Documents

- [Batch Growth Assimilation - Phase Documentation](../batch_growth_assimilation/)
- [Planning and Workflows Primer](../../user_guides/planning_and_workflows_primer.md)
- [Executive Forecast Dashboard - Original Plan](./executive_forecast_dashboard_plan.md)

