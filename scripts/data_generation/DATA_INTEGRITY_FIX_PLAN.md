# AquaMind Data Integrity Remediation Plan

## Executive Summary

The comprehensive data integrity verification has identified **3 critical issues** requiring immediate attention:

1. **🚨 FUTURE ASSIGNMENT DATES** (1,601 errors) - Fundamental temporal logic flaw
2. **⚠️ FEED MASS BALANCE** (201M kg discrepancy) - Unrealistic feeding calculations
3. **⚠️ SENSOR COVERAGE GAPS** (1,582 containers) - Incomplete environmental monitoring

**RECOMMENDATION: Session 4 requires complete regeneration** due to the fundamental date calculation issues. However, targeted fixes can salvage portions of the existing infrastructure.

---

## Issue Analysis & Root Cause Assessment

### 1. 🚨 Future Assignment Dates (Critical - 1,601 instances)

#### Root Cause Analysis
```sql
-- Example of problematic assignments
SELECT batch_number, assignment_date, departure_date
FROM batch_batchcontainerassignment
WHERE assignment_date > CURRENT_DATE
ORDER BY assignment_date DESC
LIMIT 5;
```

**Likely Causes:**
- **Date Arithmetic Bug**: Incorrect date calculations in `BatchManager._create_container_assignment()`
- **Timezone Issues**: UTC vs local timezone confusion in date handling
- **Session Date Range**: Session 4 (2024) generating dates beyond intended scope
- **Lifecycle Progression**: Stage transition dates calculated incorrectly

#### Impact Assessment
- **Data Usability**: ❌ **CRITICAL** - Temporal relationships are meaningless
- **Analytics**: ❌ **BROKEN** - Time-series analysis impossible
- **Business Logic**: ❌ **INVALID** - Growth calculations based on wrong timelines
- **Regulatory Compliance**: ❌ **NON-COMPLIANT** - Historical data appears future-dated

**VERDICT: Existing Session 4 data is NOT SALVAGEABLE**

### 2. ⚠️ Feed Mass Balance Discrepancy (Warning - 201M kg)

#### Root Cause Analysis
```sql
-- Feed balance calculation
SELECT
    SUM(quantity_kg) as total_purchased,
    SUM(amount_kg) as total_consumed
FROM inventory_feedpurchase p
CROSS JOIN inventory_feedingevent f;
```

**Likely Causes:**
- **Unrealistic FCR Values**: Feed Conversion Ratio too low (< 0.5)
- **Population Overestimation**: Batch populations inflated
- **Feeding Frequency**: Too many feeding events per day
- **Growth Rate Mismatch**: Biomass calculations not matching feed consumption

#### Impact Assessment
- **Data Usability**: ⚠️ **DEGRADED** - Financial calculations inaccurate
- **Analytics**: ⚠️ **IMPAIRED** - Feed efficiency metrics unreliable
- **Business Logic**: ⚠️ **QUESTIONABLE** - Economic projections flawed
- **Regulatory Compliance**: ⚠️ **CONCERNS** - Feed usage reporting suspect

**VERDICT: Fixable without full regeneration**

### 3. ⚠️ Sensor Coverage Gaps (Minor - 1,582 containers)

#### Root Cause Analysis
```sql
-- Containers without sensors
SELECT c.name, c.container_type, a.name as area
FROM infrastructure_container c
LEFT JOIN infrastructure_sensor s ON c.id = s.container_id
LEFT JOIN infrastructure_area a ON c.area_id = a.id
WHERE s.id IS NULL AND c.area_id IS NOT NULL;
```

**Likely Causes:**
- **Generation Order**: Sensors created before all containers existed
- **Container Filtering**: Some container types excluded from sensor assignment
- **Batch Processing**: Sensor generation not synchronized with container creation

#### Impact Assessment
- **Data Usability**: ⚠️ **INCOMPLETE** - Environmental monitoring gaps
- **Analytics**: ⚠️ **LIMITED** - Spatial coverage incomplete
- **Business Logic**: ✅ **ACCEPTABLE** - Core operations unaffected
- **Regulatory Compliance**: ⚠️ **MINOR CONCERNS** - Environmental reporting incomplete

**VERDICT: Easily fixable with targeted regeneration**

---

## Remediation Strategy

### Phase 1: Data Assessment & Backup (2-4 hours)

#### Objectives
- Create complete data backup before any changes
- Assess scope of each issue
- Identify salvageable vs unsalvageable data segments

#### Tasks
```bash
# 1. Create comprehensive backup
pg_dump aquamind > pre_remediation_backup.sql

# 2. Data quality assessment
python scripts/data_generation/verify_data_integrity.py --session 4 --detailed

# 3. Isolate affected records
python -c "
from apps.batch.models import BatchContainerAssignment
future_assignments = BatchContainerAssignment.objects.filter(assignment_date__gt='2024-12-31')
print(f'Future assignments to remove: {future_assignments.count()}')
"
```

#### Deliverables
- ✅ Full database backup
- ✅ Detailed issue assessment report
- ✅ List of records to preserve vs remove

### Phase 2: Targeted Fixes (4-6 hours)

#### 2A: Fix Sensor Coverage Gaps
```python
# scripts/data_generation/fixes/sensor_coverage_fix.py
from apps.infrastructure.models import Container, Sensor
from scripts.data_generation.generators.infrastructure import InfrastructureGenerator

def fix_sensor_coverage():
    """Add sensors to containers missing them"""
    containers_without_sensors = Container.objects.filter(
        sensors__isnull=True,
        active=True
    )

    sensor_types = ['TEMPERATURE', 'OXYGEN', 'PH', 'SALINITY']
    created_sensors = 0

    for container in containers_without_sensors:
        for sensor_type in sensor_types:
            Sensor.objects.create(
                name=f"{container.name} {sensor_type.title()} Sensor",
                sensor_type=sensor_type,
                container=container,
                serial_number=f"SENSOR_{container.id}_{sensor_type}",
                manufacturer="Auto-Generated",
                active=True
            )
            created_sensors += 1

    print(f"Created {created_sensors} sensors for {containers_without_sensors.count()} containers")
```

#### 2B: Fix Feed Mass Balance
```python
# scripts/data_generation/fixes/feed_balance_fix.py
from apps.inventory.models import FeedingEvent, FeedStock
from decimal import Decimal

def recalculate_feed_balance():
    """Recalculate feeding events to achieve mass balance"""
    # 1. Get realistic FCR values (1.0 - 1.5 for salmon)
    # 2. Recalculate feeding amounts based on actual biomass
    # 3. Update feed stock levels accordingly

    feeding_events = FeedingEvent.objects.select_related('batch_assignment')

    for event in feeding_events:
        if event.batch_assignment:
            # Calculate realistic feed amount
            biomass = event.batch_assignment.biomass_kg or 0
            realistic_fcr = Decimal('1.2')  # Industry standard
            realistic_feed = biomass * realistic_fcr / Decimal('100')  # Daily percentage

            # Update feeding event
            event.amount_kg = realistic_feed
            event.save()
```

### Phase 3: Session 4 Regeneration (8-12 hours)

#### Prerequisites
- ✅ Phase 1 & 2 complete
- ✅ Infrastructure data preserved
- ✅ Critical date calculation bugs identified and fixed

#### Regeneration Strategy
```python
# scripts/data_generation/session4_regeneration.py
from scripts.data_generation.orchestrator.session_manager import DataGenerationSessionManager

def regenerate_session4():
    """Regenerate Session 4 with fixed date calculations"""

    # 1. Clear existing Session 4 data (preserve infrastructure)
    clear_session4_data()

    # 2. Fix date calculation bugs in BatchManager
    fix_date_calculation_bugs()

    # 3. Regenerate with corrected logic
    session_manager = DataGenerationSessionManager()
    session_manager.run_session('session_4', resume=False)

def clear_session4_data():
    """Remove Session 4 data while preserving infrastructure"""
    from django.db import transaction

    with transaction.atomic():
        # Remove batch assignments (keep batches themselves)
        BatchContainerAssignment.objects.filter(
            assignment_date__year=2024
        ).delete()

        # Remove feeding events for 2024
        FeedingEvent.objects.filter(
            feeding_date__year=2024
        ).delete()

        # Remove health records for 2024 batches
        # (Keep infrastructure: containers, sensors, areas)
```

#### Key Fixes Required
1. **Date Calculation Fix** in `BatchManager._calculate_realistic_weight()`
2. **Assignment Date Logic** in `BatchManager._create_container_assignment()`
3. **Lifecycle Progression** timing corrections
4. **Feed Consumption** realism adjustments

### Phase 4: Validation & Testing (2-4 hours)

#### Comprehensive Testing
```python
# scripts/data_generation/validation/test_regenerated_data.py
def run_comprehensive_tests():
    """Test all aspects of regenerated data"""

    tests = [
        test_date_validity(),
        test_feed_balance(),
        test_sensor_coverage(),
        test_lifecycle_progression(),
        test_business_logic_integrity()
    ]

    passed = sum(1 for test in tests if test['passed'])
    total = len(tests)

    print(f"Tests Passed: {passed}/{total}")
    return passed == total
```

#### Performance Validation
- ✅ Date ranges: All within 2024
- ✅ Feed balance: < 5% discrepancy
- ✅ Sensor coverage: > 95% containers
- ✅ Lifecycle progression: All batches advance correctly
- ✅ Business metrics: Realistic aquaculture KPIs

---

## Implementation Timeline

### Week 1: Assessment & Preparation
- **Day 1-2**: Phase 1 (Data assessment & backup)
- **Day 3-4**: Phase 2A (Sensor coverage fixes)
- **Day 5**: Phase 2B (Feed balance fixes)

### Week 2: Regeneration & Validation
- **Day 6-8**: Phase 3 (Session 4 regeneration)
- **Day 9-10**: Phase 4 (Comprehensive testing)
- **Day 10**: Final validation & deployment

### Key Milestones
- ✅ **End Day 2**: Data backup complete, issues scoped
- ✅ **End Day 5**: Targeted fixes implemented
- ✅ **End Day 8**: Session 4 fully regenerated
- ✅ **End Day 10**: Production-ready data validated

---

## Risk Assessment & Mitigation

### High Risk Issues
1. **Data Loss**: Mitigated by comprehensive backups
2. **Regression**: Mitigated by phased approach
3. **Performance Impact**: Mitigated by targeted regeneration

### Medium Risk Issues
1. **Business Logic Changes**: Thorough testing required
2. **Integration Issues**: Comprehensive validation planned
3. **Timeline Slippage**: Buffer time included

### Low Risk Issues
1. **Sensor Coverage**: Simple addition, no complex logic
2. **Feed Balance**: Mathematical corrections only

---

## Success Criteria

### Data Quality Metrics
- ✅ **Date Validity**: 100% assignments within 2024
- ✅ **Feed Balance**: < 5% mass discrepancy
- ✅ **Sensor Coverage**: > 95% containers monitored
- ✅ **Lifecycle Integrity**: All batches progress correctly
- ✅ **Business Logic**: Realistic aquaculture metrics

### System Performance
- ✅ **Query Performance**: < 2x degradation from baseline
- ✅ **Storage Efficiency**: < 10% increase from optimal
- ✅ **Backup Recovery**: < 4 hours restoration time

### Compliance & Documentation
- ✅ **Audit Trail**: Complete remediation documentation
- ✅ **Data Lineage**: Clear provenance tracking
- ✅ **Validation Reports**: Automated integrity checking

---

## Post-Remediation Monitoring

### Automated Checks
```python
# scripts/data_generation/monitoring/continuous_validation.py
def schedule_continuous_validation():
    """Set up automated daily integrity checks"""
    # Schedule daily validation runs
    # Alert on any new integrity issues
    # Generate weekly summary reports
    pass
```

### Key Metrics to Monitor
1. **Date Distribution**: Ensure no future dates creep in
2. **Feed Balance**: Monitor for mass balance drift
3. **Sensor Coverage**: Track coverage completeness
4. **Performance**: Query response times and resource usage

---

## Conclusion & Recommendations

### Primary Recommendation
**PROCEED WITH SESSION 4 REGENERATION** - The future date issue is fundamental and affects all temporal relationships in the aquaculture data model.

### Alternative Approaches Considered
1. **Date Correction Only**: Attempted but deemed too risky for data integrity
2. **Partial Regeneration**: Considered but future dates affect all downstream calculations
3. **Data Masking**: Rejected as it would hide underlying logic flaws

### Long-term Prevention
1. **Enhanced Date Validation**: Add comprehensive date sanity checks
2. **Automated Testing**: Implement continuous integration validation
3. **Code Review Process**: Require date logic peer review
4. **Monitoring Dashboard**: Real-time data quality metrics

**This remediation plan ensures AquaMind will have production-quality, temporally accurate aquaculture simulation data.** 🐟✨

---

*Document Version: 1.0*
*Last Updated: $(date)*
*Prepared by: AquaMind Data Integrity Team*

