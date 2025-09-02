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

## 📊 **PRODUCTION SCALE & DATA VOLUME REQUIREMENTS**

### **Annual Production Targets**
- **Faroe Islands:** 60,000 tonnes filleted salmon/year
- **Scotland:** 40,000 tonnes filleted salmon/year
- **Average Salmon Weight:** 6kg at harvest
- **Total Annual Production:** ~16.7 million salmon
- **Batch Size:** ~3.5 million eggs (initial)
- **Survival Rate:** ~80% at harvest (~900 days)
- **Total Lifecycle:** 900 days (2.5 years)

### **Infrastructure Scale**
- **Freshwater Stations:** 15 (Faroe) + 10 (Scotland) = 30 total
- **Sea Areas:** 30 (Faroe) + 30 (Scotland) = 60 total
- **Rings per Area:** 20 rings × 60 areas = 1,200 sea rings
- **Containers per Freshwater Hall:** 12 containers
- **Halls per Station:** 5 halls (Egg/Alevin, Fry, Parr, Smolt, Post-Smolt)
- **Total Freshwater Containers:** 30 stations × 5 halls × 12 containers = 1,800

### **Container Progression & Lifecycle**
- **Egg & Alevin:** Incubation trays in hatchery (85-95 days, yolk sack fed)
- **Fry:** Fry tanks (85-95 days, feed starts)
- **Parr:** Parr tanks (85-95 days)
- **Smolt:** Smolt tanks (85-95 days)
- **Post-Smolt:** Post-Smolt tanks (85-95 days)
- **Adult:** Sea rings/cages (400-500 days)

### **Data Collection Frequencies**
- **Environmental Readings:**
  - O₂, CO₂, Temperature, Salinity: 4× daily
  - pH, NO₂, NO₃, NH₄: 1× daily
  - Salinity: Rings only (4× daily)
- **Health Records:** Every 20 days per BCA
- **Mortality:** Daily per container
- **Growth Samples:** Weekly per BCA
- **Feeding Events:** 4× daily per BCA (feed required)

### **Growth Characteristics**
- **Curve Shape:** Sigmoid (slow start, rapid growth in rings, flattening after 350-400 days)
- **Stage-Specific Parameters:**
  - FCR varies by lifecycle stage
  - TGC varies by lifecycle stage
  - Mortality rates vary by stage
- **Environmental Factors:** Temperature, oxygen, salinity impact growth rates

## 🎯 **BCA-Centric Data Generation Architecture**

### **Assignment-Driven Generation Pattern**
```python
def generate_for_active_assignments(date):
    """
    Generate data ONLY for active batch-container assignments on given date
    Scale: ~1,800 freshwater containers + 1,200 sea rings = ~3,000 active BCAs
    """
    active_assignments = BatchContainerAssignment.objects.filter(
        assignment_date__lte=date,
        departure_date__gte=date  # or departure_date__isnull=True
    )

    for assignment in active_assignments:
        # Generate ALL data for this specific assignment
        generate_environmental_readings(assignment, date)  # 4-8 readings/day
        generate_feeding_events(assignment, date)         # 4 events/day (if feeding)
        generate_health_monitoring(assignment, date)      # Every 20 days
        generate_growth_samples(assignment, date)         # Weekly
        generate_mortality_events(assignment, date)       # Daily
        # Every data point links to this assignment
```

### **Temporal Precision Requirements**
```python
# CRITICAL: All timestamps must align with BCA periods
# Scale Impact: 3,000 BCAs × multiple daily readings = 10,000+ data points/day
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

### **Scale Validation**
```python
def validate_production_scale():
    """Validate system can handle real-world production scale"""

    # Infrastructure scale
    freshwater_containers = Container.objects.filter(
        area__geography__type='freshwater'
    ).count()
    sea_rings = Container.objects.filter(
        area__geography__type='sea'
    ).count()

    assert freshwater_containers >= 1800, f"Need 1,800+ freshwater containers, got {freshwater_containers}"
    assert sea_rings >= 1200, f"Need 1,200+ sea rings, got {sea_rings}"

    # Active BCA count (steady state)
    active_bcas = BatchContainerAssignment.objects.filter(
        departure_date__isnull=True
    ).count()
    assert 2500 <= active_bcas <= 3500, f"Active BCAs should be 2,500-3,500, got {active_bcas}"
```

### **Data Volume Validation**
```python
def validate_daily_data_volume(date):
    """Validate realistic daily data generation volume"""

    # Environmental readings (4-8 per BCA per day)
    env_readings = EnvironmentalReading.objects.filter(
        reading_time__date=date
    ).count()

    expected_min = 2500 * 4  # 2,500 BCAs × 4 readings minimum
    expected_max = 3500 * 8  # 3,500 BCAs × 8 readings maximum

    assert expected_min <= env_readings <= expected_max, \
        f"Daily environmental readings should be {expected_min}-{expected_max}, got {env_readings}"

    # Feeding events (4 per feeding BCA per day)
    feeding_bcas = BatchContainerAssignment.objects.filter(
        assignment_date__lte=date,
        departure_date__gte=date,
        lifecycle_stage__name__in=['Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']
    ).count()

    feed_events = FeedingEvent.objects.filter(feeding_time__date=date).count()
    expected_feed = feeding_bcas * 4  # 4 feeding events per feeding BCA

    assert abs(feed_events - expected_feed) < (expected_feed * 0.1), \
        f"Daily feeding events should be ~{expected_feed}, got {feed_events}"
```

### **BCA Linkage Validation**
```python
def validate_bca_completeness():
    """Ensure 100% of data is linked to BCAs"""

    # Environmental readings (critical - no orphans allowed)
    orphaned_env = EnvironmentalReading.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_env == 0, f"CRITICAL: {orphaned_env} environmental readings not linked to BCAs"

    # Feeding events
    orphaned_feed = FeedingEvent.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_feed == 0, f"{orphaned_feed} feeding events not linked to BCAs"

    # Health events
    orphaned_health = HealthEvent.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_health == 0, f"{orphaned_health} health events not linked to BCAs"

    # Mortality events
    orphaned_mortality = MortalityEvent.objects.filter(
        batch_container_assignment__isnull=True
    ).count()
    assert orphaned_mortality == 0, f"{orphaned_mortality} mortality events not linked to BCAs"
```

### **Temporal Alignment Validation**
```python
def validate_temporal_alignment():
    """Ensure all data timestamps align with BCA periods"""

    # Sample validation (run on subset for performance)
    sample_readings = EnvironmentalReading.objects.all()[:1000]

    for reading in sample_readings:
        bca = reading.batch_container_assignment
        assert bca.assignment_date <= reading.reading_time.date(), \
            f"Reading {reading.id} predates BCA {bca.id} assignment"

        if bca.departure_date:
            assert reading.reading_time.date() <= bca.departure_date, \
                f"Reading {reading.id} postdates BCA {bca.id} departure"

    # Validate no data exists for non-existent BCAs
    orphaned_dates = EnvironmentalReading.objects.filter(
        batch_container_assignment__isnull=True
    ).values_list('reading_time__date', flat=True).distinct()

    assert len(orphaned_dates) == 0, f"Orphaned data exists for dates: {list(orphaned_dates)}"
```

## 🏗️ **Implementation Roadmap**

### **Phase 1: BCA Infrastructure & Core Models**
- ✅ Clean directory structure
- ⏳ **BCA Manager Module**: Core BCA lifecycle management
- ⏳ **Temporal Validation Framework**: Ensure all data aligns with BCA periods
- ⏳ **Infrastructure Setup**: Create 1,800 freshwater containers + 1,200 sea rings
- ⏳ **Batch Lifecycle Management**: BCA chain creation/closure for stage transitions

### **Phase 2: Environmental Data Generation**
- ⏳ **Sensor Infrastructure**: Create sensors for each container (O₂, CO₂, Temp, pH, NO₂, NO₃, NH₄, Salinity)
- ⏳ **Environmental Reading Generator**: BCA-linked readings with correct frequencies
  - 4× daily: O₂, CO₂, Temperature, Salinity (rings only)
  - 1× daily: pH, NO₂, NO₃, NH₄
- ⏳ **Environmental Parameter Validation**: Realistic ranges by geography and season

### **Phase 3: Health & Mortality Systems**
- ⏳ **Mortality Generator**: Daily mortality per BCA with stage-specific rates
- ⏳ **Health Monitoring Generator**: Every 20 days per BCA
- ⏳ **Disease Simulation**: Stage-appropriate disease outbreaks
- ⏳ **Treatment Integration**: Medication and intervention tracking

### **Phase 4: Feed Management & Supply Chain**
- ⏳ **Feed Inventory Integration**: Purchase orders, container refills, barge management
- ⏳ **Feeding Event Generator**: 4× daily for feeding BCAs with FCR calculations
- ⏳ **Feed Consumption Tracking**: Real-time inventory updates
- ⏳ **Supply Chain Orchestration**: Procurement triggered by low inventory

### **Phase 5: Growth & Production Modeling**
- ⏳ **TGC Calculator**: Stage-specific thermal growth coefficients
- ⏳ **Sigmoid Growth Curves**: Slow start → rapid growth in rings → flattening
- ⏳ **Biomass Tracking**: Population × average weight calculations
- ⏳ **Production Forecasting**: Yield predictions based on growth curves

### **Phase 6: Orchestration & Performance**
- ⏳ **Daily Cycle Coordinator**: Coordinate all generators for ~3,000 active BCAs
- ⏳ **Performance Optimization**: Bulk operations for 10,000+ daily data points
- ⏳ **Memory Management**: Handle large datasets efficiently
- ⏳ **Progress Tracking**: Real-time generation monitoring

### **Phase 7: Validation & Quality Assurance**
- ⏳ **Scale Validation**: Verify 1,800 containers + 1,200 rings infrastructure
- ⏳ **Data Volume Validation**: Confirm realistic daily data generation
- ⏳ **BCA Linkage Validation**: 100% data-to-BCA linkage integrity
- ⏳ **Temporal Alignment**: All data within BCA active periods
- ⏳ **Salmon CV Reconstruction**: End-to-end lifecycle traceability

## ⚠️ **Critical Complexity Considerations**

### **Supply Chain Interconnectedness**
- **Feed Management**: Purchase → Storage → Distribution → Consumption → Reordering
- **Container Progression**: Egg trays → Fry tanks → Parr tanks → Smolt tanks → Rings
- **Batch-to-Area Assignment**: Entire batches assigned to single areas (20 rings)
- **Geographic Distribution**: 2 regions with different operational patterns

### **Performance Requirements**
- **Daily Data Volume**: 10,000+ environmental readings + 4,000+ feeding events
- **Active BCAs**: 2,500-3,500 simultaneously active
- **Memory Usage**: Efficient bulk operations for large datasets
- **Temporal Precision**: All data must align with BCA periods (no orphans)

### **Data Integrity Requirements**
- **Zero Orphaned Data**: Every data point must link to active BCA
- **Temporal Alignment**: No data outside BCA active periods
- **Realistic Ranges**: Environmental parameters within operational bounds
- **Supply Chain Continuity**: Feed inventory never goes negative

## 🎯 **Key Architectural Principles**

1. **BCA Centrality**: Everything revolves around active assignments (2,500-3,500 active)
2. **Temporal Precision**: All timestamps must align with BCA periods (critical for CV generation)
3. **Data Preservation**: Never delete historical data (SET_NULL constraints for decommissioned infrastructure)
4. **Linkage Integrity**: 100% of data points must link to BCAs (no orphaned environmental readings)
5. **Scale Readiness**: System must handle 1,800 freshwater containers + 1,200 sea rings
6. **Supply Chain Integration**: Full inventory management with realistic procurement cycles
7. **Geographic Realism**: Different operational patterns for Faroe Islands vs Scotland
8. **Salmon CV Focus**: Every data point contributes to individual fish lifecycle reconstruction

## 📈 **Success Metrics**

### **Production Scale Achievement**
- **Infrastructure**: 1,800+ freshwater containers, 1,200+ sea rings
- **Active BCAs**: 2,500-3,500 simultaneously active
- **Daily Data Volume**: 10,000+ environmental readings, 4,000+ feeding events
- **Annual Production**: 100,000 tonnes filleted salmon across 2 geographies

### **Data Quality Standards**
- **BCA Linkage**: 100% of data points linked to active BCAs
- **Temporal Alignment**: Zero data points outside BCA active periods
- **Environmental Realism**: All parameters within operational ranges
- **Supply Chain Continuity**: No negative inventory states

This BCA-centric approach ensures that every environmental reading, feeding event, health record, and growth sample can be traced back to the specific batch-container assignment where the fish existed, enabling complete salmon CV generation with temporal accuracy at production scale.
