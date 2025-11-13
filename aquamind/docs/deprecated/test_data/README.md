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

## 📊 **PRODUCTION SCALE OVERVIEW**

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

### **Daily Data Generation Scale**
- **Active BCAs:** 2,500-3,500 simultaneously active
- **Environmental Readings:** 10,000+ per day (4-8 per BCA)
- **Feeding Events:** 4,000+ per day (4 per feeding BCA)
- **Health Records:** ~125 per day (every 20 days per BCA)
- **Mortality Events:** Daily per BCA

## 📋 **Implementation Roadmap - CHRONOLOGICAL APPROACH**

### **Phase 1: Infrastructure & BCA Foundation** ✅ **START HERE**
- ✅ Cleaned directory structure
- ✅ Removed flawed legacy code
- ⏳ **BCA Manager Module**: Core BCA lifecycle management (create/close BCAs)
- ⏳ **Infrastructure Setup**: Create 1,800 freshwater containers + 1,200 sea rings
- ⏳ **Sensor Infrastructure**: Create sensors for environmental monitoring
- ⏳ **Temporal Validation Framework**: Ensure all data aligns with BCA periods

### **Phase 2: Daily Cycle Orchestration** ⭐ **MAIN GENERATION PHASE**
**Generate ALL data chronologically, day by day, with full temporal dependencies:**

- ⏳ **Daily Environmental Generation**: 4-8 readings per BCA (O₂, CO₂, Temp, pH, NO₂, NO₃, NH₄, Salinity)
- ⏳ **Health & Mortality Integration**: Daily mortality based on environmental conditions
- ✅ **Health Assessments**: Veterinary parameter scoring every 15-20 days (see README_HEALTH_ASSESSMENTS.md)
- ⏳ **Feed Management**: 4× daily feeding events with inventory tracking
- ⏳ **Growth Calculations**: TGC-based growth with environmental factors
- ⏳ **Biomass Updates**: Population × weight calculations for each BCA
- ⏳ **Supply Chain Events**: Purchase orders triggered by low inventory
- ⏳ **BCA Lifecycle Transitions**: Move fish between containers when stage complete

**Critical: All systems run together each day to maintain temporal dependencies!**

### **Phase 3: Optimization & Scaling**
- ⏳ **Performance Optimization**: Bulk operations for 10,000+ daily data points
- ⏳ **Memory Management**: Handle 3,000+ active BCAs efficiently
- ⏳ **Database Optimization**: Efficient queries for temporal data
- ⏳ **Progress Monitoring**: Real-time generation tracking

### **Phase 4: Validation & Quality Assurance**
- ⏳ **Temporal Integrity Validation**: All data within BCA active periods
- ⏳ **BCA Linkage Validation**: 100% data-to-BCA linkage integrity
- ⏳ **Production Scale Validation**: Verify infrastructure and data volumes
- ⏳ **Salmon CV Reconstruction**: End-to-end lifecycle traceability
- ⏳ **Supply Chain Continuity**: No negative inventory states

### **Phase 5: Advanced Features & Extensions**
- ⏳ **Disease Outbreak Simulation**: Stage-appropriate disease modeling
- ⏳ **Treatment Integration**: Medication and intervention tracking
- ⏳ **Environmental Anomaly Generation**: Storms, algae blooms, temperature spikes
- ⏳ **Geographic Variation**: Different patterns for Faroe vs Scotland
- ⏳ **Seasonal Effects**: Weather and production cycle variations

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
