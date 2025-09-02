# AquaMind Data Generation Technical Specification

**Version:** 2.0 - BCA-Centric Architecture  
**Date:** September 2, 2025

## 🚨 **CRITICAL: BCA-Centric Design for Salmon CV Generation**

### **Core Architectural Principle**
**Everything revolves around `BatchContainerAssignment` (BCA)** - the central object that enables temporal traceability for individual salmon lifecycles.

```python
# BCA: The heart of salmon CV generation
class BatchContainerAssignment(models.Model):
    batch = models.ForeignKey(Batch)
    container = models.ForeignKey(Container)
    lifecycle_stage = models.ForeignKey(LifecycleStage)
    assignment_date = models.DateField()      # When fish arrived
    departure_date = models.DateField(null=True)  # When they left
    population_count = models.IntegerField()  # How many fish
    biomass_kg = models.DecimalField()        # Total weight
```

### **Salmon CV Requirements**
Every generated data point must contribute to reconstructing individual fish lifecycles:
- **Complete Environmental History**: All water conditions experienced by each fish
- **Health Timeline**: Diseases, treatments, and mortality events
- **Feed Records**: Every feeding event and feed type consumed
- **Movement History**: Container transfers with precise timestamps
- **Growth Trajectory**: Weight and length progression over time

## 🎯 **BCA-Centric Data Generation Architecture**

### **Assignment-Driven Generation Pattern**
```python
def generate_for_active_assignments(date):
    """
    Generate data ONLY for active batch-container assignments on given date
    """
    active_assignments = BatchContainerAssignment.objects.filter(
        assignment_date__lte=date,
        departure_date__gte=date  # or departure_date__isnull=True
    )

    for assignment in active_assignments:
        # Generate ALL data for this specific assignment
        generate_environmental_readings(assignment, date)
        generate_feeding_events(assignment, date)
        generate_health_monitoring(assignment, date)
        generate_growth_samples(assignment, date)
        # Every data point links to this assignment
```

### **Temporal Precision Requirements**
```python
# CRITICAL: All timestamps must align with BCA periods
class TemporalValidator:
    @staticmethod
    def validate_data_temporal_alignment(assignment, data_timestamp):
        """Ensure data timestamp falls within assignment active period"""
        if data_timestamp.date() < assignment.assignment_date:
            raise ValueError("Data predates assignment start")

        if (assignment.departure_date and
            data_timestamp.date() > assignment.departure_date):
            raise ValueError("Data postdates assignment end")

        return True
```

## 📋 **Core Data Relationships (BCA-Centric)**

### **Environmental Readings → BCA**
```python
class EnvironmentalReading(models.Model):
    # Direct BCA linkage for salmon CV
    batch_container_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.SET_NULL,  # Preserve historical data
        null=True,
        related_name='environmental_readings'
    )
    container = models.ForeignKey(Container, on_delete=models.SET_NULL, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True)
    parameter = models.ForeignKey(EnvironmentalParameter)
    reading_time = models.DateTimeField()
    value = models.DecimalField(max_digits=10, decimal_places=4)

    # Ensure temporal alignment
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(reading_time__date__gte=F('batch_container_assignment__assignment_date')),
                name='reading_after_assignment_start'
            )
        ]
```

### **Feeding Events → BCA**
```python
class FeedingEvent(models.Model):
    # Direct BCA linkage
    batch_container_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.CASCADE,
        related_name='feeding_events'
    )
    feed_type = models.ForeignKey(FeedType)
    quantity_kg = models.DecimalField()
    feeding_time = models.DateTimeField()
    # Temporal validation ensures feeding_time within BCA period
```

### **Health Events → BCA**
```python
class HealthEvent(models.Model):
    # Direct BCA linkage for individual fish tracking
    batch_container_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.CASCADE,
        related_name='health_events'
    )
    event_type = models.CharField()  # mortality, disease, treatment
    fish_count = models.IntegerField()
    event_time = models.DateTimeField()
    # Enables reconstruction of individual fish health history
```

## 🔄 **Lifecycle Stage Transitions**

### **BCA Chain Management**
```python
def handle_lifecycle_transition(batch, old_stage, new_stage, transition_date):
    """
    Create new BCA and close old one for stage transitions
    """
    # Close old assignment
    old_assignment = BatchContainerAssignment.objects.filter(
        batch=batch,
        lifecycle_stage=old_stage,
        departure_date__isnull=True
    ).first()

    if old_assignment:
        old_assignment.departure_date = transition_date
        old_assignment.save()

    # Create new assignment for next stage
    new_assignment = BatchContainerAssignment.objects.create(
        batch=batch,
        container=find_available_container(new_stage),
        lifecycle_stage=new_stage,
        assignment_date=transition_date,
        population_count=batch.current_population
    )

    return new_assignment
```

## 📊 **Data Generation Orchestration**

### **Daily Cycle Pattern**
```python
class BCACentricDataGenerator:
    def generate_daily_cycle(self, date):
        """Generate all data for active assignments on given date"""

        # Get all active assignments for this date
        active_assignments = self.get_active_assignments(date)

        for assignment in active_assignments:
            # Generate environmental data for this specific assignment
            self.generate_environmental_for_assignment(assignment, date)

            # Generate feeding events for this assignment
            self.generate_feeding_for_assignment(assignment, date)

            # Generate health monitoring for this assignment
            self.generate_health_for_assignment(assignment, date)

            # Generate growth samples for this assignment
            self.generate_growth_for_assignment(assignment, date)

        # Handle lifecycle transitions
        self.process_stage_transitions(date)

        # Update batch metrics
        self.update_batch_metrics(date)

    def get_active_assignments(self, date):
        """Get all assignments active on given date"""
        return BatchContainerAssignment.objects.filter(
            assignment_date__lte=date,
            models.Q(departure_date__isnull=True) |
            models.Q(departure_date__gte=date)
        ).select_related('batch', 'container', 'lifecycle_stage')
```

## 🎯 **Success Criteria**

### **BCA Linkage Validation**
```python
def validate_bca_completeness():
    """Ensure 100% of data is linked to BCAs"""

    # Environmental readings
    orphaned_env = EnvironmentalReading.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_env == 0, f"{orphaned_env} environmental readings not linked"

    # Feeding events
    orphaned_feed = FeedingEvent.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_feed == 0, f"{orphaned_feed} feeding events not linked"

    # Health events
    orphaned_health = HealthEvent.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_health == 0, f"{orphaned_health} health events not linked"
```

### **Temporal Alignment Validation**
```python
def validate_temporal_alignment():
    """Ensure all data timestamps align with BCA periods"""

    for reading in EnvironmentalReading.objects.all():
        bca = reading.batch_container_assignment
        assert bca.assignment_date <= reading.reading_time.date()
        if bca.departure_date:
            assert reading.reading_time.date() <= bca.departure_date

    for event in FeedingEvent.objects.all():
        bca = event.batch_container_assignment
        assert bca.assignment_date <= event.feeding_time.date()
        if bca.departure_date:
            assert event.feeding_time.date() <= bca.departure_date
```

## 🏗️ **Implementation Roadmap**

### **Phase 1: BCA Infrastructure**
- ✅ Clean directory structure
- ⏳ Create BCA manager module
- ⏳ Implement temporal validation
- ⏳ Design assignment lifecycle management

### **Phase 2: Core Generators**
- ⏳ **Environmental Generator**: BCA-linked readings only
- ⏳ **Feed Manager**: Assignment-aware feeding events
- ⏳ **Health Generator**: BCA-specific monitoring
- ⏳ **Growth Calculator**: TGC-based with BCA context

### **Phase 3: Orchestration**
- ⏳ **Daily Cycle Coordinator**: Manage all generators per date
- ⏳ **Stage Transition Handler**: BCA chain management
- ⏳ **Validation Framework**: Ensure temporal and linkage integrity

### **Phase 4: Testing & Optimization**
- ⏳ **Salmon CV Reconstruction**: End-to-end validation
- ⏳ **Performance Optimization**: Efficient bulk operations
- ⏳ **Data Quality Assurance**: Comprehensive validation suite

## 🎯 **Key Architectural Principles**

1. **BCA Centrality**: Everything revolves around active assignments
2. **Temporal Precision**: All timestamps must align with BCA periods
3. **Data Preservation**: Never delete historical data (SET_NULL constraints)
4. **Linkage Integrity**: 100% of data points must link to BCAs
5. **Salmon CV Focus**: Every data point contributes to individual fish lifecycle reconstruction

This BCA-centric approach ensures that every environmental reading, feeding event, health record, and growth sample can be traced back to the specific batch-container assignment where the fish existed, enabling complete salmon CV generation with temporal accuracy.
