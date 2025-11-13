# Growth Sample Individual Tracking Update

**Date:** 2025-10-31  
**Issue:** #106 (Backend), #164 (Frontend)  
**Status:** ✅ Complete

---

## Overview

Updated test data generation to align with new individual fish tracking for growth samples. Growth samples now generate individual fish observations that automatically calculate aggregate statistics.

---

## Changes Made

### 1. Event Engine Updated (`03_event_engine_core.py`)

**Before:**
```python
if self.stats['days'] % 7 == 0:
    GrowthSample.objects.create(
        assignment=a, 
        sample_date=self.current_date, 
        sample_size=30,
        avg_weight_g=a.avg_weight_g,
        avg_length_cm=Decimal(str(round((new_w ** 0.33) * 5, 1)))
    )
```

**After:**
```python
if self.stats['days'] % 7 == 0:
    from apps.batch.models import IndividualGrowthObservation
    from random import uniform
    
    # Create growth sample (initially with placeholder values)
    growth_sample = GrowthSample.objects.create(
        assignment=a,
        sample_date=self.current_date,
        sample_size=0,  # Will be recalculated
        avg_weight_g=Decimal('0.0'),  # Will be recalculated
    )
    
    # Generate individual fish observations (30 fish sample)
    num_fish = 30
    base_weight = float(new_w)
    base_length = float((new_w ** 0.33) * 5)
    
    for fish_num in range(1, num_fish + 1):
        # Add realistic variation around batch average
        # Weight: ±15% variation
        fish_weight = base_weight * uniform(0.85, 1.15)
        # Length: ±10% variation
        fish_length = base_length * uniform(0.90, 1.10)
        
        IndividualGrowthObservation.objects.create(
            growth_sample=growth_sample,
            fish_identifier=str(fish_num),
            weight_g=Decimal(str(round(fish_weight, 2))),
            length_cm=Decimal(str(round(fish_length, 2)))
        )
    
    # Calculate aggregates from individual observations
    growth_sample.calculate_aggregates()
```

---

## Key Improvements

### ✅ Individual Fish Tracking
- Each growth sample now creates 30 `IndividualGrowthObservation` records
- Each observation has fish_identifier, weight_g, length_cm
- Realistic variation (±15% weight, ±10% length) around batch average

### ✅ Automatic Aggregate Calculation
- `sample_size`, `avg_weight_g`, `avg_length_cm` auto-calculated
- `std_deviation_weight`, `std_deviation_length` auto-calculated
- `min_weight_g`, `max_weight_g` auto-calculated
- `condition_factor` (K-factor) auto-calculated

### ✅ Pattern Consistency
- Matches `HealthSamplingEvent` → `IndividualFishObservation` pattern
- Follows same workflow: create parent → create children → calculate aggregates
- Maintains data generation best practices

---

## Testing

### Verify Individual Observations Generated

```bash
python manage.py shell -c "
from apps.batch.models import GrowthSample, IndividualGrowthObservation

samples = GrowthSample.objects.count()
observations = IndividualGrowthObservation.objects.count()
expected_obs = samples * 30  # 30 fish per sample

print(f'Growth Samples: {samples}')
print(f'Individual Observations: {observations}')
print(f'Expected Observations: {expected_obs}')
print(f'Match: {observations == expected_obs} ✓' if observations == expected_obs else f'Mismatch: {observations} vs {expected_obs} ✗')

# Check aggregates calculated correctly
sample = GrowthSample.objects.filter(sample_size__gt=0).first()
if sample:
    print(f'\nSample #{sample.id}:')
    print(f'  Sample Size: {sample.sample_size}')
    print(f'  Avg Weight: {sample.avg_weight_g}g')
    print(f'  Avg Length: {sample.avg_length_cm}cm')
    print(f'  Std Dev Weight: {sample.std_deviation_weight}g')
    print(f'  Std Dev Length: {sample.std_deviation_length}cm')
    print(f'  Min Weight: {sample.min_weight_g}g')
    print(f'  Max Weight: {sample.max_weight_g}g')
    print(f'  K-Factor: {sample.condition_factor}')
    print(f'  Individual Observations: {sample.individual_observations.count()}')
"
```

### Expected Output
```
Growth Samples: 54 (weekly samples × batches)
Individual Observations: 1,620 (54 samples × 30 fish)
Expected Observations: 1,620
Match: True ✓

Sample #12345:
  Sample Size: 30
  Avg Weight: 125.50g
  Avg Length: 22.30cm
  Std Dev Weight: 18.75g
  Std Dev Length: 2.10cm
  Min Weight: 95.20g
  Max Weight: 155.80g
  K-Factor: 1.13
  Individual Observations: 30
```

---

## Legacy Scripts (Not Updated)

The following scripts use outdated GrowthSample schema and are **not actively used**:

❌ `simulate_full_lifecycle.py` - Uses old `batch` FK (deprecated)  
❌ `diagnose_data_generation.py` - Uses old `batch` FK and `container` field (deprecated)

**These scripts should be archived or deleted** - they won't work with current schema.

---

## Regenerating Test Data

To generate fresh data with individual observations:

```bash
# Clean existing batch data
python scripts/data_generation/cleanup_batch_data.py

# Bootstrap infrastructure
python scripts/data_generation/01_bootstrap_infrastructure.py

# Initialize master data
python scripts/data_generation/02_initialize_master_data.py

# Generate batch with lifecycle (includes individual growth observations)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 \
  --eggs 3500000 \
  --geography "Scotland" \
  --duration 650
```

---

## Database Schema Changes

### New Table: `batch_individualgrowthobservation`
- `id`: Primary key
- `growth_sample_id`: FK to batch_growthsample
- `fish_identifier`: Unique within sample
- `weight_g`: Individual fish weight
- `length_cm`: Individual fish length
- Unique constraint: `(growth_sample_id, fish_identifier)`

### Updated Table: `batch_growthsample`
- Aggregate fields now **auto-calculated** from individual observations
- Fields: sample_size, avg_weight_g, avg_length_cm, std_deviation_weight, std_deviation_length, min_weight_g, max_weight_g, condition_factor
- All calculated via `GrowthSample.calculate_aggregates()` method

---

## Impact on Frontend

### Batch Management Page
- ✅ "Record Growth" button on container cards
- ✅ Form creates growth sample with individual fish observations
- ✅ Aggregates calculated automatically by backend

### Health Page (Read-Only View)
- ✅ Veterinarians can view growth samples
- ✅ See aggregate statistics
- ✅ See individual fish observations table
- ✅ Link to detail page for full data

---

## Success Criteria

- ✅ Event engine generates individual observations (30 per sample)
- ✅ Realistic variation in fish measurements (±15% weight, ±10% length)
- ✅ Aggregates auto-calculated correctly
- ✅ Weekly sampling frequency maintained (every 7 days)
- ✅ Pattern matches health assessment generation
- ✅ Frontend displays all statistics correctly

---

## Notes

- **Sample size:** 30 fish per growth sample (industry standard)
- **Frequency:** Weekly sampling (every 7 days)
- **Variation:** Realistic spread around batch average
- **K-factor:** Automatically calculated from avg weight and length
- **Historical tracking:** Both GrowthSample and IndividualGrowthObservation have history tables

---

**End of Document**











