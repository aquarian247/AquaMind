# Backend Issue: Implement Growth Sample Recording with Individual Fish Tracking

**Priority:** Medium  
**Complexity:** Medium  
**Estimated Effort:** 4-6 hours

---

## Overview

Create a growth sampling system that records individual fish measurements and calculates aggregated batch-level growth metrics, similar to the health sampling event pattern.

---

## Requirements

### 1. Create `batch_individualgrowthobservation` Model

```python
class IndividualGrowthObservation(models.Model):
    """Records measurements for a single fish in a growth sample."""
    growth_sample = models.ForeignKey(
        GrowthSample, 
        on_delete=models.CASCADE, 
        related_name='individual_observations',
        help_text="The growth sample this observation belongs to."
    )
    fish_identifier = models.CharField(
        max_length=50,
        help_text="Identifier for the fish (e.g., sequential number)."
    )
    weight_g = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Weight in grams."
    )
    length_cm = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Length in centimeters."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        unique_together = [['growth_sample', 'fish_identifier']]
        ordering = ['growth_sample', 'fish_identifier']
```

### 2. Update `batch_growthsample` Model

Add `calculate_aggregates()` method:

```python
def calculate_aggregates(self):
    """Calculate aggregate metrics from individual fish observations."""
    observations = self.individual_observations.all()
    
    if not observations.exists():
        self.sample_size = 0
        self.save()
        return
    
    # Calculate statistics
    weight_stats = observations.aggregate(
        avg=Avg('weight_g'),
        std=StdDev('weight_g'),
        min=Min('weight_g'),
        max=Max('weight_g'),
        count=Count('id')
    )
    
    length_stats = observations.aggregate(
        avg=Avg('length_cm'),
        std=StdDev('length_cm')
    )
    
    self.sample_size = weight_stats['count']
    self.avg_weight_g = weight_stats['avg']
    self.std_deviation_weight = weight_stats['std']
    self.min_weight_g = weight_stats['min']
    self.max_weight_g = weight_stats['max']
    self.avg_length_cm = length_stats['avg']
    self.std_deviation_length = length_stats['std']
    
    # Calculate K-factor: K = 100 * (weight_g / length_cm³)
    if self.avg_weight_g and self.avg_length_cm and self.avg_length_cm > 0:
        self.condition_factor = (self.avg_weight_g / (self.avg_length_cm ** 3)) * 100
    
    self.save()
```

### 3. Create Nested Serializers

```python
class IndividualGrowthObservationInputSerializer(serializers.Serializer):
    """Input serializer for nested growth observations."""
    fish_identifier = serializers.CharField(max_length=50)
    weight_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    length_cm = serializers.DecimalField(max_digits=10, decimal_places=2)

class IndividualGrowthObservationSerializer(serializers.ModelSerializer):
    """Serializer for displaying growth observations."""
    calculated_k_factor = serializers.SerializerMethodField()
    
    class Meta:
        model = IndividualGrowthObservation
        fields = ['id', 'fish_identifier', 'weight_g', 'length_cm', 'calculated_k_factor']
    
    def get_calculated_k_factor(self, obj):
        if obj.weight_g and obj.length_cm and obj.length_cm > 0:
            return (obj.weight_g / (obj.length_cm ** 3)) * 100
        return None

class GrowthSampleSerializer(serializers.ModelSerializer):
    # Write-only for creating
    individual_observations = IndividualGrowthObservationInputSerializer(
        many=True,
        required=False,
        write_only=True
    )
    
    # Read-only for displaying  
    fish_observations = IndividualGrowthObservationSerializer(
        source='individual_observations',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = GrowthSample
        fields = [
            'id', 'assignment', 'sample_date', 'sample_size',
            'avg_weight_g', 'avg_length_cm', 'std_deviation_weight', 'std_deviation_length',
            'min_weight_g', 'max_weight_g', 'condition_factor',
            'individual_observations',  # write-only
            'fish_observations',  # read-only
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sample_size', 'avg_weight_g', 'avg_length_cm',
            'std_deviation_weight', 'std_deviation_length',
            'min_weight_g', 'max_weight_g', 'condition_factor',
            'fish_observations', 'created_at', 'updated_at'
        ]
```

### 4. Update Create Logic

```python
@transaction.atomic
def create(self, validated_data):
    individual_observations_data = validated_data.pop('individual_observations', [])
    
    growth_sample = GrowthSample.objects.create(**validated_data)
    
    for obs_data in individual_observations_data:
        IndividualGrowthObservation.objects.create(
            growth_sample=growth_sample,
            **obs_data
        )
    
    growth_sample.calculate_aggregates()
    return growth_sample
```

---

## Reference Implementation

✅ **Pattern to follow:** `apps/health/models/health_observation.py`
- `HealthSamplingEvent.calculate_aggregate_metrics()` method
- Nested observation handling

✅ **Serializer pattern:** `apps/health/api/serializers/health_observation.py`  
- Dual fields: write-only input + read-only output
- Nested creation with transaction

---

## Tests Required

```python
def test_growth_sample_with_individual_observations(self):
    # Create sample with 10 fish
    # Verify aggregates calculated correctly
    # Verify K-factor accurate
    
def test_aggregate_recalculation_on_update(self):
    # Update observations
    # Verify aggregates recalculate
```

---

## Migration

```bash
python manage.py makemigrations batch --name add_individual_growth_observations
```

---

## Success Criteria

- ✅ Can create growth sample with 75 individual fish observations
- ✅ Aggregates match manual calculations
- ✅ API returns nested fish observations in GET
- ✅ All batch tests pass
- ✅ K-factor accurate to 2 decimal places

