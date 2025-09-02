# AquaMind Test Data Generation Scripts

## 🚨 **ARCHITECTURAL RESET - STARTING FRESH**

**Previous data generation system had fundamental architectural flaws** where environmental data was completely disconnected from batch lifecycles (0% of 62.9M readings linked to assignments).

**Starting clean with BCA-centric design** focused on temporal traceability for salmon CV generation.

## 🎯 **Core Principle: BCA-Centric Architecture**

**Everything revolves around `BatchContainerAssignment` (BCA)** - the central object that tracks which fish are where and when:

```python
# BCA is the heart of salmon CV generation
class BatchContainerAssignment(models.Model):
    batch = models.ForeignKey(Batch)
    container = models.ForeignKey(Container)
    lifecycle_stage = models.ForeignKey(LifecycleStage)
    assignment_date = models.DateField()      # When fish arrived
    departure_date = models.DateField(null=True)  # When they left
    population_count = models.IntegerField()  # How many fish
    biomass_kg = models.DecimalField()        # Total weight
```

**All data generation must link to active BCAs** to create traceable salmon CVs.

## 🏗️ **New BCA-Centric Architecture**

### **Core Principle: Assignment-Driven Generation**
```python
def generate_for_date(date):
    """Generate data only for active batch-container assignments"""

    active_assignments = BatchContainerAssignment.objects.filter(
        assignment_date__lte=date,
        departure_date__gte=date  # or departure_date__isnull=True
    )

    for assignment in active_assignments:
        # Generate ALL data for this specific assignment
        generate_environmental_data(assignment, date)
        generate_feeding_events(assignment, date)
        generate_health_monitoring(assignment, date)
        generate_growth_samples(assignment, date)
        # ... all other data types
```

### **Salmon CV Traceability**
Every piece of data must enable reconstruction of individual fish lifecycles:
- **Temporal Precision**: All timestamps must align with BCA periods
- **Assignment Linking**: Every record links to the specific BCA where fish existed
- **Lifecycle Continuity**: Data flows seamlessly as fish move between containers

## 📋 **Implementation Roadmap**

### **Phase 1: Clean Foundation (Current)**
- ✅ Cleaned directory structure
- ✅ Removed flawed legacy code
- ⏳ Create BCA-centric technical specification
- ⏳ Design modular generators

### **Phase 2: Core Generators**
- ⏳ **BCA Manager**: Create and manage active assignments
- ⏳ **Environmental Generator**: BCA-linked environmental readings
- ⏳ **Feed Manager**: Assignment-aware feeding events
- ⏳ **Health Generator**: BCA-specific health monitoring

### **Phase 3: Temporal Integration**
- ⏳ **Timestamp Validation**: Ensure all data aligns with BCA periods
- ⏳ **Lifecycle Transitions**: Handle fish movement between containers
- ⏳ **Historical Reconstruction**: Enable salmon CV generation

### **Phase 4: Orchestration & Testing**
- ⏳ **Daily Cycle Generator**: Coordinate all generators per date
- ⏳ **Data Validation**: Verify BCA linkages and temporal consistency
- ⏳ **Performance Optimization**: Efficient bulk operations

## 🎯 **Success Criteria**

### **BCA Linkage Validation**
```python
# Every environmental reading must link to active BCA
assert EnvironmentalReading.objects.filter(batch_container_assignment__isnull=True).count() == 0

# All readings must be within BCA date ranges
for reading in EnvironmentalReading.objects.all():
    bca = reading.batch_container_assignment
    assert bca.assignment_date <= reading.reading_time.date()
    assert reading.reading_time.date() <= (bca.departure_date or date.today())
```

### **Salmon CV Capability**
- ✅ **Complete Lifecycle Tracking**: From egg to harvest
- ✅ **Environmental History**: All conditions experienced by fish
- ✅ **Health Timeline**: Treatments, diseases, mortality events
- ✅ **Feed Records**: All feeding events and feed types
- ✅ **Movement History**: Container transfers with timestamps

## 📝 **Current Status**

**Clean slate established** - ready for BCA-centric implementation. Previous complex system removed to prevent architectural confusion.

**Next**: Create focused technical specification emphasizing BCA centrality and temporal traceability for salmon CV generation.
