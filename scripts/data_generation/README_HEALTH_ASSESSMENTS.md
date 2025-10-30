# Health Assessment Data Generation

## Overview

Health assessment test data uses the normalized parameter scoring system with configurable score ranges.

## Prerequisites

1. **Health parameters must exist** (run `populate_parameter_scores` first)
2. **Active batch assignments must exist**
3. **Django user must exist** (for user attribution)

---

## Generation Scripts

### 1. Populate Health Parameters (Required First)

```bash
python manage.py populate_parameter_scores
```

**Creates:**
- 9 standard health parameters (Gill, Eye, Wounds, Fin, Body, Swimming, Appetite, Mucous, Color)
- 36 score definitions (4 per parameter, 0-3 scale)

**Verify:**
```bash
python manage.py shell -c "
from apps.health.models import HealthParameter, ParameterScoreDefinition
print(f'Parameters: {HealthParameter.objects.count()}')
print(f'Score Definitions: {ParameterScoreDefinition.objects.count()}')
"
```

Expected output:
```
Parameters: 9
Score Definitions: 36
```

---

### 2. Generate Health Assessments

```bash
# Generate 40 assessment events
python manage.py generate_health_assessments --count=40

# With biometric data included (30% of assessments)
python manage.py generate_health_assessments --count=40 --include-biometrics

# Fewer fish per event
python manage.py generate_health_assessments --count=50 --fish-per-event=5

# Clear existing data first
python manage.py generate_health_assessments --count=40 --clear-existing
```

**Creates:**
- `HealthSamplingEvent` records (linked to batch assignments)
- `IndividualFishObservation` records (fish being assessed)
- `FishParameterScore` records (scores for each parameter per fish)
- Realistic distribution: 70% healthy, 20% moderate, 10% stressed

---

## Data Characteristics

### Health Profiles:

**Healthy (70% of batches):**
- Scores mostly 0-1 (excellent to good)
- Weight distribution: [0.70, 0.25, 0.04, 0.01] for scores [0, 1, 2, 3]
- Represents batches in good condition with minimal issues

**Moderate (20% of batches):**
- Scores distributed 0-2 (some fair conditions)
- Weight distribution: [0.40, 0.40, 0.15, 0.05]
- Represents batches with some minor health concerns

**Stressed (10% of batches):**
- Scores skewed toward 2-3 (fair to poor)
- Weight distribution: [0.10, 0.30, 0.40, 0.20]
- Represents batches with significant health issues

### Fish Sample Sizes:

- **Typical:** 10 fish per assessment
- **Range:** 5-20 fish (varied for realism)
- **Distribution:** 
  - 60% use 10 fish
  - 20% use 15 fish
  - 10% use 5 fish
  - 10% use 20 fish

### Biometric Inclusion:

- **30%** of assessments include weight/length measurements
- **70%** are pure health assessments (vet-only, no biometrics)
- This reflects real workflow: operators measure growth, vets assess health

### Date Distribution:

- Assessments created for past 1-60 days
- Random distribution within assignment active periods
- Ensures realistic temporal spread

---

## Validation

After generation, verify data integrity:

```bash
python manage.py shell -c "
from apps.health.models import HealthSamplingEvent, IndividualFishObservation, FishParameterScore
events = HealthSamplingEvent.objects.count()
fish = IndividualFishObservation.objects.count()
scores = FishParameterScore.objects.count()
params = 9  # Standard parameter count

print(f'Events: {events}')
print(f'Fish observed: {fish}')
print(f'Parameter scores: {scores}')
print(f'Expected scores: {fish * params}')
print(f'Match: {scores == fish * params}')
"
```

**Expected output:**
```
Events: 40
Fish observed: 400 (40 events × avg 10 fish)
Parameter scores: 3,600 (400 fish × 9 parameters)
Expected scores: 3,600
Match: True ✓
```

---

## Integration with Event Engine

For integration with the chronological event engine (`03_chronological_event_engine.py`):

```python
# In event engine, add health assessment generation
def generate_health_data_for_assignment(assignment, current_date):
    """Generate health assessments for an assignment on a given date."""
    
    # Generate assessment every 20 days (approximate)
    if should_generate_health_assessment(assignment, current_date):
        from apps.health.models import HealthParameter
        parameters = list(HealthParameter.objects.filter(is_active=True))
        
        if parameters:
            profile = determine_health_profile(assignment)  # Based on batch status
            num_fish = 10  # Standard sample size
            include_biometrics = random.random() < 0.3
            
            generate_assessment_event(
                assignment=assignment,
                assessment_date=current_date,
                num_fish=num_fish,
                parameters=parameters,
                profile=profile,
                include_biometrics=include_biometrics
            )
```

---

## Usage Examples

### Example 1: Quick Test Data

```bash
# Setup
python manage.py populate_parameter_scores

# Generate minimal test set
python manage.py generate_health_assessments --count=10 --fish-per-event=5
```

### Example 2: Production-Scale Data

```bash
# Generate comprehensive dataset
python manage.py generate_health_assessments \
    --count=100 \
    --fish-per-event=10 \
    --include-biometrics \
    --clear-existing
```

### Example 3: Different Sample Sizes

```bash
# Small samples (rapid screening)
python manage.py generate_health_assessments --count=20 --fish-per-event=5

# Large samples (detailed assessment)
python manage.py generate_health_assessments --count=20 --fish-per-event=15
```

---

## Data Model Overview

### Relationships:
```
HealthParameter (1) ← (N) ParameterScoreDefinition
    ↓ (1)
    ↓
    ↓ (N)
FishParameterScore → (1) IndividualFishObservation → (1) HealthSamplingEvent → (1) BatchContainerAssignment
```

### Data Flow:
1. **HealthParameter** - Configured by veterinarians (name, min/max score)
2. **ParameterScoreDefinition** - Defines what each score means (0: Excellent, 1: Good, etc.)
3. **HealthSamplingEvent** - Assessment session for a batch/container
4. **IndividualFishObservation** - Individual fish being assessed
5. **FishParameterScore** - Specific score for a parameter on a fish

---

## Troubleshooting

### Error: No health parameters found

**Problem:** Parameters not created  
**Solution:**
```bash
python manage.py populate_parameter_scores
```

### Error: No active batch assignments

**Problem:** No batches in system  
**Solution:**
```bash
# Run infrastructure and batch generation first
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py
```

### Warning: Scores don't match expected count

**Problem:** Parameter scoring failed for some fish  
**Solution:** Check parameter min/max ranges are valid (max > min)

---

## Performance Notes

- **Batch Size:** Creates events in batches of 100
- **Performance:** ~100 events/second (with nested observations and scores)
- **Database Impact:** Moderate (creates 3 tables worth of data)
- **Recommended:** Run during off-hours for large datasets (>1000 events)

---

## Future Enhancements

1. **Temporal Patterns** - Generate assessments based on batch lifecycle stage
2. **Health Deterioration** - Simulate declining health over time
3. **Seasonal Patterns** - Different health profiles by season
4. **Treatment Correlation** - Link assessments to treatment events
5. **Predictive Patterns** - Generate data suitable for ML training

---

**Last Updated:** October 30, 2025  
**Status:** ✅ Complete and ready for use

