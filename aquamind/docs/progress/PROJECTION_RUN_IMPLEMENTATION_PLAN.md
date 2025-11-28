# ProjectionRun Implementation Plan

**Created**: 2025-11-28  
**Status**: Ready for Implementation  
**Issue**: Decouple projection data from scenario configuration

---

## Problem Statement

When re-running projections on a scenario, all existing projection data is deleted and replaced. Batches that have `pinned_scenario` pointing to this scenario automatically see the new projections without user consent - causing unexpected side effects when multiple batches share a scenario.

### Current Architecture

```
Batch.pinned_scenario → Scenario → ScenarioProjection[]
```

**Current behavior when re-running projections:**
1. `run_projection(save_results=True)` **deletes** all existing `ScenarioProjection` records
2. Creates new projection records with the same `scenario_id`
3. Batches that have `pinned_scenario` pointing to this scenario **automatically see the new projections** (no re-pinning needed)

### Design Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A: Mutable Projections** (current) | Simple, batches stay in sync | Unexpected side effects, no history |
| **B: Immutable Scenarios** | History preserved, explicit updates | Scenario proliferation, more manual work |
| **C: Versioned Projections** | Compare versions, same scenario ID | More complex model |
| **D: ProjectionRun** (chosen) | History preserved, no proliferation, clear semantics | Medium complexity |

---

## Solution: ProjectionRun Abstraction (Option D)

Introduce a `ProjectionRun` model that captures a specific execution of projections. Batches pin to a `ProjectionRun` (not a `Scenario`), giving explicit control over which projection data they consume.

### New Architecture

```
Scenario (configuration - "the recipe")
    │
    ├── ProjectionRun #1 (2024-11-15, "Initial baseline")
    │       ├── ScenarioProjection (day 1)
    │       ├── ScenarioProjection (day 2)
    │       └── ...
    │
    └── ProjectionRun #2 (2024-11-28, "Updated TGC model")
            ├── ScenarioProjection (day 1)
            ├── ScenarioProjection (day 2)
            └── ...

Batch A ──────► pinned to ProjectionRun #1
Batch B ──────► pinned to ProjectionRun #2
```

### Key Benefits

- **History preserved**: Each projection calculation creates a new run
- **Explicit control**: Users choose when to update a batch's pinned run
- **No proliferation**: Scenarios don't multiply; runs do (and that's expected)
- **Clear semantics**: "Batch B is pinned to projections generated on 2024-11-15"
- **Comparison capability**: Compare Run #1 vs Run #2 for same scenario


---

## Phase 1: Backend Model Changes

### 1.1 New ProjectionRun Model

**File**: `apps/scenario/models.py`

```python
class ProjectionRun(models.Model):
    """
    Represents a single execution of projections for a scenario.
    
    Batches pin to a ProjectionRun (not directly to Scenario) so that
    re-running projections creates a new run without affecting existing
    batch references.
    """
    run_id = models.BigAutoField(primary_key=True)
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='projection_runs'
    )
    run_date = models.DateTimeField(auto_now_add=True)
    run_number = models.PositiveIntegerField(
        help_text="Sequential run number for this scenario (1, 2, 3...)"
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional label (e.g., 'Baseline', 'Updated TGC')"
    )
    
    # Snapshot of key parameters used (for comparison/audit)
    parameters_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of TGC, FCR, mortality values used"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='projection_runs'
    )
    notes = models.TextField(blank=True)
    
    # Denormalized summary for quick access
    total_projections = models.PositiveIntegerField(default=0)
    final_weight_g = models.FloatField(null=True, blank=True)
    final_biomass_kg = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = 'scenario_projection_run'
        ordering = ['scenario', '-run_number']
        unique_together = ['scenario', 'run_number']
        indexes = [
            models.Index(fields=['scenario', '-run_date']),
        ]
    
    def __str__(self):
        label_str = f" ({self.label})" if self.label else ""
        return f"{self.scenario.name} - Run #{self.run_number}{label_str}"
```

### 1.2 Modify ScenarioProjection

**File**: `apps/scenario/models.py`

Change FK from `scenario` to `projection_run`:

```python
class ScenarioProjection(models.Model):
    projection_id = models.BigAutoField(primary_key=True)
    projection_run = models.ForeignKey(
        ProjectionRun,
        on_delete=models.CASCADE,
        related_name='projections'
    )
    # ... rest unchanged (projection_date, day_number, average_weight, etc.)
```

### 1.3 Modify Batch Model

**File**: `apps/batch/models/batch.py`

Replace `pinned_scenario` with `pinned_projection_run`:

```python
# REMOVE this:
pinned_scenario = models.ForeignKey(
    'scenario.Scenario',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='pinned_batches',
    verbose_name="Pinned Scenario",
    help_text="Pinned scenario used for daily actual state calculations."
)

# ADD this:
pinned_projection_run = models.ForeignKey(
    'scenario.ProjectionRun',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='pinned_batches',
    verbose_name="Pinned Projection Run",
    help_text="Specific projection run used for growth analysis."
)
```

### 1.4 Migration Strategy

Create a data migration that:

1. **Create** `scenario_projection_run` table
2. **For each Scenario with projections**, create a ProjectionRun (run_number=1)
3. **Update** all ScenarioProjection records to point to the new ProjectionRun
4. **For each Batch with `pinned_scenario`**, set `pinned_projection_run` to that scenario's latest run
5. **Drop** the `pinned_scenario` column and the old FK

**Migration file structure**:
```
apps/scenario/migrations/
  - XXXX_add_projection_run_model.py          # Schema: create ProjectionRun table
  - XXXX_migrate_projections_to_runs.py       # Data: create runs, move projections
  
apps/batch/migrations/
  - XXXX_add_pinned_projection_run.py         # Add new field
  - XXXX_migrate_pinned_scenario_to_run.py    # Data: copy FK values
  - XXXX_remove_pinned_scenario.py            # Remove old field
```

---

## Phase 2: Backend Service Layer Changes

### 2.1 Update ProjectionEngine

**File**: `apps/scenario/services/calculations/projection_engine.py`

```python
@transaction.atomic
def run_projection(
    self,
    save_results: bool = True,
    label: str = "",
    current_user: Optional[User] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, any]:
    """
    Run projection and create a new ProjectionRun.
    
    Does NOT delete existing projections - creates new run instead.
    """
    if self.errors:
        return {'success': False, 'errors': self.errors, 'warnings': self.warnings}
    
    # Create new ProjectionRun (instead of deleting existing)
    if save_results:
        latest_run = self.scenario.projection_runs.order_by('-run_number').first()
        next_run_number = (latest_run.run_number + 1) if latest_run else 1
        
        projection_run = ProjectionRun.objects.create(
            scenario=self.scenario,
            run_number=next_run_number,
            label=label,
            parameters_snapshot=self._capture_parameters_snapshot(),
            created_by=current_user,
        )
    
    # ... run daily calculations (unchanged logic)
    
    # Save projections to new run
    if save_results and projections:
        projection_objs = [
            ScenarioProjection(
                projection_run=projection_run,  # Changed from scenario=
                **p
            ) for p in projections
        ]
        ScenarioProjection.objects.bulk_create(projection_objs)
        
        # Update run summary
        projection_run.total_projections = len(projection_objs)
        projection_run.final_weight_g = projections[-1]['average_weight']
        projection_run.final_biomass_kg = projections[-1]['biomass']
        projection_run.save()
    
    return {
        'success': True,
        'projection_run_id': projection_run.run_id if save_results else None,
        'run_number': projection_run.run_number if save_results else None,
        'summary': result['summary'],
        'warnings': self.warnings,
    }
```

### 2.2 Add Parameter Snapshot Helper

```python
def _capture_parameters_snapshot(self) -> dict:
    """Capture key parameters for audit trail and comparison."""
    return {
        'tgc_model': {
            'id': self.tgc_model.model_id,
            'name': self.tgc_model.name,
            'tgc_value': self.tgc_model.tgc_value,
            'exponent_n': self.tgc_model.exponent_n,
            'exponent_m': self.tgc_model.exponent_m,
        },
        'fcr_model': {
            'id': self.fcr_model.model_id,
            'name': self.fcr_model.name,
        },
        'mortality_model': {
            'id': self.mortality_model.model_id,
            'name': self.mortality_model.name,
            'rate': self.mortality_model.rate,
            'frequency': self.mortality_model.frequency,
        },
        'scenario': {
            'initial_weight': self.scenario.initial_weight,
            'initial_count': self.scenario.initial_count,
            'duration_days': self.scenario.duration_days,
        },
        'captured_at': timezone.now().isoformat(),
    }
```

### 2.3 Update Growth Assimilation Service

**File**: `apps/batch/services/growth_assimilation.py`

Update to use `pinned_projection_run` instead of `pinned_scenario`:

```python
def _get_scenario(self) -> Optional['Scenario']:
    """Get scenario for TGC model lookup."""
    # NEW: Get scenario via projection run
    if self.batch.pinned_projection_run:
        return self.batch.pinned_projection_run.scenario
    
    # Fallback: Find any scenario linked to this batch
    return self.batch.scenarios.first()
```

---

## Phase 3: API Layer Changes

### 3.1 New ProjectionRun Serializers

**File**: `apps/scenario/api/serializers.py`

```python
class ProjectionRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing projection runs."""
    scenario_name = serializers.CharField(source='scenario.name', read_only=True)
    pinned_batch_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectionRun
        fields = [
            'run_id', 'scenario', 'scenario_name', 'run_number', 
            'label', 'run_date', 'total_projections',
            'final_weight_g', 'final_biomass_kg', 'pinned_batch_count'
        ]
    
    def get_pinned_batch_count(self, obj):
        return obj.pinned_batches.count()


class ProjectionRunDetailSerializer(ProjectionRunListSerializer):
    """Full serializer with parameters snapshot."""
    parameters_snapshot = serializers.JSONField(read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.username', 
        read_only=True,
        allow_null=True
    )
    
    class Meta(ProjectionRunListSerializer.Meta):
        fields = ProjectionRunListSerializer.Meta.fields + [
            'parameters_snapshot', 'notes', 'created_by_name'
        ]
```

### 3.2 Update ScenarioViewSet

**File**: `apps/scenario/api/viewsets.py`

```python
@action(detail=True, methods=['post'])
def run_projection(self, request, pk=None):
    """
    Run projection - creates NEW ProjectionRun.
    
    Request body (optional):
    {
        "label": "Updated TGC model"  // Optional label for this run
    }
    
    Returns:
    {
        "success": true,
        "projection_run_id": 123,
        "run_number": 2,
        "message": "Projection run #2 created."
    }
    """
    scenario = self.get_object()
    
    # Check permissions
    if scenario.created_by != request.user and not request.user.is_superuser:
        return Response(
            {'error': 'You do not have permission to run projections for this scenario'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    label = request.data.get('label', '')
    
    engine = ProjectionEngine(scenario)
    result = engine.run_projection(
        save_results=True,
        label=label,
        current_user=request.user
    )
    
    if result['success']:
        return Response({
            'success': True,
            'projection_run_id': result['projection_run_id'],
            'run_number': result['run_number'],
            'message': f"Projection run #{result['run_number']} created.",
            'warnings': result.get('warnings', []),
        })
    else:
        return Response({
            'success': False,
            'errors': result['errors'],
            'warnings': result.get('warnings', []),
        }, status=status.HTTP_400_BAD_REQUEST)


@action(detail=True, methods=['get'])
def projection_runs(self, request, pk=None):
    """List all projection runs for a scenario."""
    scenario = self.get_object()
    runs = scenario.projection_runs.select_related('created_by').order_by('-run_number')
    serializer = ProjectionRunListSerializer(runs, many=True)
    return Response(serializer.data)
```

### 3.3 New ProjectionRunViewSet

**File**: `apps/scenario/api/viewsets.py`

```python
class ProjectionRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for ProjectionRun.
    
    Creating runs is done via Scenario.run_projection action.
    Deleting runs requires Manager+ role.
    """
    queryset = ProjectionRun.objects.select_related('scenario', 'created_by')
    serializer_class = ProjectionRunDetailSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['scenario']
    
    @action(detail=True, methods=['get'])
    def projections(self, request, pk=None):
        """Get all projection data for this run."""
        projection_run = self.get_object()
        
        # Support aggregation parameter
        aggregation = request.query_params.get('aggregation', 'daily')
        projections = projection_run.projections.select_related('current_stage')
        
        if aggregation == 'weekly':
            projections = projections.annotate(
                mod_result=Mod(F('day_number'), 7)
            ).filter(mod_result=0)
        elif aggregation == 'monthly':
            projections = projections.annotate(
                mod_result=Mod(F('day_number'), 30)
            ).filter(mod_result=0)
        
        serializer = ScenarioProjectionSerializer(projections, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """
        Compare this run with another.
        
        Query params:
            ?with=<run_id>  - The other run to compare against
        """
        run_a = self.get_object()
        run_b_id = request.query_params.get('with')
        
        if not run_b_id:
            return Response(
                {'error': 'Specify ?with=<run_id> to compare'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        run_b = get_object_or_404(ProjectionRun, pk=run_b_id)
        
        return Response({
            'run_a': ProjectionRunDetailSerializer(run_a).data,
            'run_b': ProjectionRunDetailSerializer(run_b).data,
            'parameter_diff': self._compute_param_diff(run_a, run_b),
        })
    
    def _compute_param_diff(self, run_a, run_b):
        """Compute differences between parameter snapshots."""
        diff = {}
        snap_a = run_a.parameters_snapshot or {}
        snap_b = run_b.parameters_snapshot or {}
        
        # Compare TGC values
        if snap_a.get('tgc_model', {}).get('tgc_value') != snap_b.get('tgc_model', {}).get('tgc_value'):
            diff['tgc_value'] = {
                'run_a': snap_a.get('tgc_model', {}).get('tgc_value'),
                'run_b': snap_b.get('tgc_model', {}).get('tgc_value'),
            }
        
        # Compare mortality rates
        if snap_a.get('mortality_model', {}).get('rate') != snap_b.get('mortality_model', {}).get('rate'):
            diff['mortality_rate'] = {
                'run_a': snap_a.get('mortality_model', {}).get('rate'),
                'run_b': snap_b.get('mortality_model', {}).get('rate'),
            }
        
        return diff
```

### 3.4 Update Router Registration

**File**: `apps/scenario/api/routers.py`

```python
from apps.scenario.api.viewsets import (
    # ... existing imports
    ProjectionRunViewSet,
)

# Add this registration
router.register(r'projection-runs', ProjectionRunViewSet, basename='projection-runs')

# Resulting endpoints:
# - GET  /api/v1/scenario/projection-runs/           - List all runs (filterable by ?scenario=)
# - GET  /api/v1/scenario/projection-runs/{id}/      - Get run details
# - GET  /api/v1/scenario/projection-runs/{id}/projections/  - Get projection data
# - GET  /api/v1/scenario/projection-runs/{id}/compare/?with=<id>  - Compare runs
```

### 3.5 Update Batch Pin Endpoint

**File**: `apps/batch/api/viewsets/growth_assimilation_mixin.py`

```python
@action(detail=True, methods=['post'])
def pin_projection_run(self, request, pk=None):
    """
    Pin a specific projection run to this batch.
    
    Request body:
    {
        "projection_run_id": 123
    }
    """
    batch = self.get_object()
    projection_run_id = request.data.get('projection_run_id')
    
    if not projection_run_id:
        return Response(
            {'error': 'projection_run_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    projection_run = get_object_or_404(ProjectionRun, pk=projection_run_id)
    
    batch.pinned_projection_run = projection_run
    batch.save(update_fields=['pinned_projection_run'])
    
    return Response({
        'success': True,
        'pinned_projection_run_id': projection_run.run_id,
        'scenario_name': projection_run.scenario.name,
        'run_number': projection_run.run_number,
        'run_label': projection_run.label,
    })


# DEPRECATE the old pin_scenario endpoint (keep for backward compatibility temporarily)
@action(detail=True, methods=['post'])
def pin_scenario(self, request, pk=None):
    """
    DEPRECATED: Use pin_projection_run instead.
    
    This endpoint pins the LATEST projection run for the given scenario.
    """
    batch = self.get_object()
    scenario_id = request.data.get('scenario_id')
    
    if not scenario_id:
        return Response({'error': 'scenario_id required'}, status=400)
    
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    latest_run = scenario.projection_runs.order_by('-run_number').first()
    
    if not latest_run:
        return Response(
            {'error': 'Scenario has no projection runs. Run projections first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    batch.pinned_projection_run = latest_run
    batch.save(update_fields=['pinned_projection_run'])
    
    return Response({
        'success': True,
        'pinned_projection_run_id': latest_run.run_id,
        'message': 'DEPRECATED: Use pin_projection_run endpoint. Pinned to latest run.',
    })
```

---

## Phase 4: Frontend Changes

### 4.1 Update API Types

**File**: `client/src/features/scenario/api/api.ts`

```typescript
// New interface for ProjectionRun
export interface ProjectionRun {
  run_id: number;
  scenario: number;
  scenario_name: string;
  run_number: number;
  label: string;
  run_date: string;
  total_projections: number;
  final_weight_g: number | null;
  final_biomass_kg: number | null;
  pinned_batch_count: number;
  parameters_snapshot?: Record<string, any>;
  notes?: string;
  created_by_name?: string;
}

// Hook to fetch projection runs for a scenario
export function useScenarioProjectionRuns(scenarioId: number | undefined) {
  return useQuery({
    queryKey: ['scenario', scenarioId, 'projection-runs'],
    queryFn: async () => {
      if (!scenarioId) throw new Error('Scenario ID required');
      return await ApiService.apiV1ScenarioScenariosProjectionRunsRetrieve(scenarioId);
    },
    enabled: !!scenarioId,
    staleTime: 5 * 60 * 1000,
  });
}

// Hook to fetch a single projection run
export function useProjectionRun(runId: number | undefined) {
  return useQuery({
    queryKey: ['projection-run', runId],
    queryFn: async () => {
      if (!runId) throw new Error('Run ID required');
      return await ApiService.apiV1ScenarioProjectionRunsRetrieve(runId);
    },
    enabled: !!runId,
  });
}

// Hook to run projections (creates new run)
export function useRunProjection(scenarioId: number) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (label?: string) => {
      return await ApiService.apiV1ScenarioScenariosRunProjectionCreate(
        scenarioId,
        { label: label || '' }
      );
    },
    onSuccess: () => {
      // Invalidate projection runs list
      queryClient.invalidateQueries({
        queryKey: ['scenario', scenarioId, 'projection-runs'],
      });
      toast.success('Projection run created successfully');
    },
    onError: (error: any) => {
      toast.error(error?.body?.detail || 'Failed to run projection');
    },
  });
}
```

### 4.2 Update Growth Assimilation API

**File**: `client/src/features/batch-management/api/growth-assimilation.ts`

```typescript
// Update ScenarioInfo to include projection run
export interface ScenarioInfo {
  id: number;
  name: string;
  start_date: string;
  duration_days: number;
  initial_count: number;
  initial_weight: number;
  // NEW: Projection run info
  projection_run: {
    run_id: number;
    run_number: number;
    label: string;
    run_date: string;
  } | null;
}

// New request interface
export interface PinProjectionRunRequest {
  projection_run_id: number;
}

// New mutation hook
export function usePinProjectionRun(batchId: number) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (request: PinProjectionRunRequest) => {
      return await ApiService.batchPinProjectionRun(batchId, request);
    },
    onSuccess: () => {
      // Invalidate all batch-related queries
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ 
        queryKey: ['batch', batchId, 'combined-growth-data'] 
      });
      toast.success('Projection run pinned successfully');
    },
    onError: (error: any) => {
      toast.error(error?.body?.error || 'Failed to pin projection run');
    },
  });
}
```

### 4.3 Projection Run Selector Component

**File**: `client/src/features/batch-management/components/growth-analysis/ProjectionRunSelector.tsx`

```tsx
import React from 'react';
import { Info } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useScenarioProjectionRuns } from '@/features/scenario/api/api';
import { usePinProjectionRun } from '../../api/growth-assimilation';
import { formatDistanceToNow } from 'date-fns';

interface ProjectionRunSelectorProps {
  batchId: number;
  currentRunId?: number;
  scenarioId: number;
  onRunChange?: (runId: number) => void;
}

export function ProjectionRunSelector({
  batchId,
  currentRunId,
  scenarioId,
  onRunChange,
}: ProjectionRunSelectorProps) {
  const { data: runs, isLoading } = useScenarioProjectionRuns(scenarioId);
  const pinMutation = usePinProjectionRun(batchId);
  
  const handleSelect = (runIdStr: string) => {
    const runId = parseInt(runIdStr, 10);
    pinMutation.mutate(
      { projection_run_id: runId },
      { 
        onSuccess: () => {
          onRunChange?.(runId);
        }
      }
    );
  };
  
  if (isLoading) {
    return <div className="animate-pulse h-10 bg-muted rounded" />;
  }
  
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label htmlFor="projection-run">Projection Run</Label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-4 w-4 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Each time projections are calculated, a new "run" is created.
                Switch between runs to compare how projections have changed,
                or use an older baseline for variance analysis.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      
      <Select
        value={currentRunId?.toString()}
        onValueChange={handleSelect}
        disabled={pinMutation.isPending}
      >
        <SelectTrigger id="projection-run" className="w-full">
          <SelectValue placeholder="Select projection run" />
        </SelectTrigger>
        <SelectContent>
          {runs?.map((run) => (
            <SelectItem key={run.run_id} value={run.run_id.toString()}>
              <div className="flex items-center gap-2 w-full">
                <span className="font-medium">Run #{run.run_number}</span>
                {run.label && (
                  <Badge variant="outline" className="text-xs">
                    {run.label}
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground ml-auto">
                  {formatDistanceToNow(new Date(run.run_date), { addSuffix: true })}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      {currentRunId && runs && (
        <p className="text-xs text-muted-foreground">
          {runs.find(r => r.run_id === currentRunId)?.pinned_batch_count || 0} batch(es) 
          using this run
        </p>
      )}
    </div>
  );
}
```

### 4.4 Tooltips Reference

Add these tooltips throughout the UI:

| UI Element | Tooltip Text |
|------------|--------------|
| **"Projection Run" label** | "Each time projections are calculated, a new 'run' is created. Switch between runs to compare how projections have changed, or use an older baseline for variance analysis." |
| **"Run #X" badge** | "Sequential number of this projection calculation for this scenario." |
| **"Pinned Run" indicator** | "The projection run currently used for this batch's Growth Analysis. Changing models and re-running creates a new run without affecting your current analysis." |
| **"Run Projections" button** (when runs exist) | "Creates a new projection run. Existing runs and batches pinned to them are not affected." |
| **Parameter Snapshot** | "The exact TGC, FCR, and mortality model values that were used when this projection run was calculated." |
| **"X batches using this run"** | "Number of batches currently pinned to this projection run for their Growth Analysis." |

### 4.5 Update DataVisualizationControls

**File**: `client/src/features/batch-management/components/growth-analysis/DataVisualizationControls.tsx`

Add the ProjectionRunSelector to the controls panel:

```tsx
import { ProjectionRunSelector } from './ProjectionRunSelector';

// In the component:
{scenario && (
  <div className="border-t pt-4 mt-4">
    <ProjectionRunSelector
      batchId={batchId}
      currentRunId={scenario.projection_run?.run_id}
      scenarioId={scenario.id}
    />
  </div>
)}
```

---

## Phase 5: Testing

### 5.1 Backend Model Tests

**File**: `apps/scenario/tests/models/test_projection_run.py`

```python
class ProjectionRunModelTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scenario = ScenarioFactory(created_by=self.user)
    
    def test_run_creates_projection_run(self):
        """Running projection creates a new ProjectionRun."""
        engine = ProjectionEngine(self.scenario)
        result = engine.run_projection(save_results=True, current_user=self.user)
        
        self.assertTrue(result['success'])
        self.assertEqual(self.scenario.projection_runs.count(), 1)
        
        run = self.scenario.projection_runs.first()
        self.assertEqual(run.run_number, 1)
        self.assertEqual(run.created_by, self.user)
        self.assertEqual(run.projections.count(), self.scenario.duration_days)
    
    def test_rerun_creates_new_run_preserves_old(self):
        """Re-running projection creates run #2, preserves run #1."""
        engine = ProjectionEngine(self.scenario)
        
        # First run
        result1 = engine.run_projection(save_results=True, label="Baseline")
        run1_id = result1['projection_run_id']
        
        # Second run
        result2 = engine.run_projection(save_results=True, label="Updated TGC")
        run2_id = result2['projection_run_id']
        
        # Both runs exist
        self.assertEqual(self.scenario.projection_runs.count(), 2)
        
        # Run 1 still has its projections
        run1 = ProjectionRun.objects.get(pk=run1_id)
        self.assertEqual(run1.run_number, 1)
        self.assertEqual(run1.label, "Baseline")
        self.assertEqual(run1.projections.count(), self.scenario.duration_days)
        
        # Run 2 has its own projections
        run2 = ProjectionRun.objects.get(pk=run2_id)
        self.assertEqual(run2.run_number, 2)
        self.assertEqual(run2.label, "Updated TGC")
    
    def test_batch_pin_to_specific_run(self):
        """Batch can be pinned to specific projection run."""
        batch = BatchFactory()
        engine = ProjectionEngine(self.scenario)
        
        # Create two runs
        result1 = engine.run_projection(save_results=True)
        result2 = engine.run_projection(save_results=True)
        
        # Pin to run 1
        run1 = ProjectionRun.objects.get(pk=result1['projection_run_id'])
        batch.pinned_projection_run = run1
        batch.save()
        
        self.assertEqual(batch.pinned_projection_run, run1)
        self.assertIn(batch, run1.pinned_batches.all())
        
        # Rerun doesn't affect batch's pinned run
        result3 = engine.run_projection(save_results=True)
        batch.refresh_from_db()
        self.assertEqual(batch.pinned_projection_run, run1)  # Still run 1
    
    def test_parameters_snapshot_captured(self):
        """Parameters snapshot is captured when run is created."""
        engine = ProjectionEngine(self.scenario)
        result = engine.run_projection(save_results=True)
        
        run = ProjectionRun.objects.get(pk=result['projection_run_id'])
        snapshot = run.parameters_snapshot
        
        self.assertIn('tgc_model', snapshot)
        self.assertIn('fcr_model', snapshot)
        self.assertIn('mortality_model', snapshot)
        self.assertEqual(
            snapshot['tgc_model']['tgc_value'],
            self.scenario.tgc_model.tgc_value
        )
```

### 5.2 Backend API Tests

**File**: `apps/scenario/tests/api/test_projection_run_endpoints.py`

```python
class ProjectionRunAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(self.user)
        self.scenario = ScenarioFactory(created_by=self.user)
    
    def test_run_projection_returns_run_id(self):
        """POST run_projection returns new run ID."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.pk}/run_projection/'
        
        response = self.client.post(url, {'label': 'Test run'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('projection_run_id', response.data)
        self.assertEqual(response.data['run_number'], 1)
    
    def test_list_projection_runs(self):
        """GET projection_runs lists all runs for scenario."""
        # Create some runs
        engine = ProjectionEngine(self.scenario)
        for i in range(3):
            engine.run_projection(save_results=True, label=f"Run {i+1}")
        
        url = f'/api/v1/scenario/scenarios/{self.scenario.pk}/projection_runs/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
    
    def test_get_projection_run_detail(self):
        """GET projection-runs/{id}/ returns run details."""
        engine = ProjectionEngine(self.scenario)
        result = engine.run_projection(save_results=True, label="Detail test")
        
        url = f'/api/v1/scenario/projection-runs/{result["projection_run_id"]}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['label'], "Detail test")
        self.assertIn('parameters_snapshot', response.data)
    
    def test_batch_pin_projection_run(self):
        """POST batch pin_projection_run pins specific run."""
        batch = BatchFactory()
        engine = ProjectionEngine(self.scenario)
        result = engine.run_projection(save_results=True)
        
        url = f'/api/v1/batch/batches/{batch.pk}/pin_projection_run/'
        response = self.client.post(url, {
            'projection_run_id': result['projection_run_id']
        })
        
        self.assertEqual(response.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(
            batch.pinned_projection_run_id,
            result['projection_run_id']
        )
```

### 5.3 Frontend Tests

**File**: `client/src/features/batch-management/components/growth-analysis/ProjectionRunSelector.test.tsx`

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProjectionRunSelector } from './ProjectionRunSelector';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the API
vi.mock('@/api/generated', () => ({
  ApiService: {
    apiV1ScenarioScenariosProjectionRunsRetrieve: vi.fn().mockResolvedValue([
      { run_id: 1, run_number: 1, label: 'Baseline', run_date: '2024-11-15T00:00:00Z', pinned_batch_count: 2 },
      { run_id: 2, run_number: 2, label: 'Updated', run_date: '2024-11-28T00:00:00Z', pinned_batch_count: 0 },
    ]),
    batchPinProjectionRun: vi.fn().mockResolvedValue({ success: true }),
  },
}));

describe('ProjectionRunSelector', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  
  it('displays available runs for scenario', async () => {
    render(
      <ProjectionRunSelector batchId={1} scenarioId={1} currentRunId={1} />,
      { wrapper }
    );
    
    await waitFor(() => {
      expect(screen.getByText('Run #1')).toBeInTheDocument();
    });
  });
  
  it('shows tooltip on info icon hover', async () => {
    render(
      <ProjectionRunSelector batchId={1} scenarioId={1} />,
      { wrapper }
    );
    
    const infoIcon = screen.getByRole('button', { name: /info/i });
    await userEvent.hover(infoIcon);
    
    await waitFor(() => {
      expect(screen.getByText(/each time projections are calculated/i)).toBeInTheDocument();
    });
  });
  
  it('calls onRunChange when run is selected', async () => {
    const onRunChange = vi.fn();
    
    render(
      <ProjectionRunSelector
        batchId={1}
        scenarioId={1}
        currentRunId={1}
        onRunChange={onRunChange}
      />,
      { wrapper }
    );
    
    // Open select
    await userEvent.click(screen.getByRole('combobox'));
    
    // Select run #2
    await userEvent.click(screen.getByText('Run #2'));
    
    await waitFor(() => {
      expect(onRunChange).toHaveBeenCalledWith(2);
    });
  });
});
```

---

## Implementation Order

| Step | Phase | Task | Dependencies |
|------|-------|------|--------------|
| 1 | 1.1 | Add ProjectionRun model | None |
| 2 | 1.2 | Modify ScenarioProjection FK | Step 1 |
| 3 | 1.4 | Create schema migration | Steps 1-2 |
| 4 | 1.4 | Create data migration | Step 3 |
| 5 | 1.3 | Add Batch.pinned_projection_run | Step 4 |
| 6 | 1.4 | Migrate pinned_scenario data | Step 5 |
| 7 | 2.1-2.2 | Update ProjectionEngine | Step 4 |
| 8 | 2.3 | Update GrowthAssimilationService | Steps 5-6 |
| 9 | 3.1-3.3 | Add API serializers and viewsets | Steps 1-8 |
| 10 | 3.4 | Register router endpoints | Step 9 |
| 11 | 3.5 | Update batch pin endpoint | Steps 5-6, 9 |
| 12 | - | Regenerate OpenAPI schema | Steps 9-11 |
| 13 | 4.1-4.2 | Frontend API hooks and types | Step 12 |
| 14 | 4.3 | ProjectionRunSelector component | Step 13 |
| 15 | 4.4-4.5 | Add tooltips, update controls | Step 14 |
| 16 | 5.1-5.2 | Backend tests | Steps 1-11 |
| 17 | 5.3 | Frontend tests | Steps 13-15 |
| 18 | - | Update data generation scripts | Step 11 |

---

## Key Files Summary

### Backend Files to Modify/Create

| File | Action | Description |
|------|--------|-------------|
| `apps/scenario/models.py` | Modify | Add ProjectionRun, change ScenarioProjection FK |
| `apps/batch/models/batch.py` | Modify | Replace pinned_scenario with pinned_projection_run |
| `apps/scenario/services/calculations/projection_engine.py` | Modify | Create runs instead of deleting |
| `apps/batch/services/growth_assimilation.py` | Modify | Use pinned_projection_run |
| `apps/scenario/api/serializers.py` | Modify | Add ProjectionRun serializers |
| `apps/scenario/api/viewsets.py` | Modify | Add ProjectionRunViewSet, update actions |
| `apps/scenario/api/routers.py` | Modify | Register projection-runs |
| `apps/batch/api/viewsets/growth_assimilation_mixin.py` | Modify | Update pin endpoint |
| `apps/scenario/migrations/` | Create | Schema + data migrations |
| `apps/batch/migrations/` | Create | Field change migrations |

### Frontend Files to Modify/Create

| File | Action | Description |
|------|--------|-------------|
| `client/src/features/scenario/api/api.ts` | Modify | Add projection run hooks |
| `client/src/features/batch-management/api/growth-assimilation.ts` | Modify | Update types, add pin hook |
| `client/src/features/batch-management/components/growth-analysis/ProjectionRunSelector.tsx` | Create | New component |
| `client/src/features/batch-management/components/growth-analysis/DataVisualizationControls.tsx` | Modify | Add selector |

---

## Post-Implementation Checklist

- [ ] Run `python manage.py makemigrations` and review generated migrations
- [ ] Run `python manage.py migrate` on dev database
- [ ] Run `python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`
- [ ] Run `cd AquaMind-Frontend && npm run sync:openapi`
- [ ] Run backend tests: `python manage.py test apps.scenario apps.batch --settings=aquamind.settings_ci`
- [ ] Run frontend tests: `cd AquaMind-Frontend/client && npm run test`
- [ ] Update data generation scripts to use new model
- [ ] Test end-to-end flow in browser
- [ ] Update data_model.md documentation

---

## Rollback Plan

If issues are discovered:

1. **Before data migration**: Simply delete new migration files
2. **After data migration**: 
   - Create reverse migration that:
     - Re-adds `pinned_scenario` field
     - Copies `pinned_projection_run.scenario_id` back to `pinned_scenario`
     - Re-adds `scenario_id` to ScenarioProjection
     - Copies from `projection_run.scenario_id`
   - Drop ProjectionRun table

---

## Future Enhancements (Out of Scope)

- **Auto-pin latest run**: Option to automatically pin batches to newest run
- **Run comparison UI**: Side-by-side charts comparing two runs
- **Run retention policy**: Auto-archive runs older than X days
- **Run scheduling**: Schedule periodic projection recalculations

