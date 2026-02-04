# Deprecated: FishTalk to AquaMind Migration Plan

> **Deprecated:** This document is out of date. See `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`.

**Version:** 1.0  
**Date:** December 2024  
**Status:** Draft  

## Executive Summary

This document outlines the comprehensive migration plan for transitioning from the legacy FishTalk system to AquaMind. The migration focuses on active batches and all related operational data, excluding scenarios and historical/closed batches to minimize complexity and risk during the initial migration phase.

## 1. Migration Scope

### 1.1 In Scope
- **Active Batches Only**: All currently active fish batches and their complete lifecycle data
- **Infrastructure Data**: All facilities, containers, sensors, and geographical locations
- **Inventory & Feed**: Current feed stock, feeding events, and FCR calculations
- **Health Records**: Medical journal entries, treatments, vaccinations, mortality records
- **Environmental Data**: Recent sensor readings, weather data (last 12 months)
- **Broodstock Data**: Active broodstock populations, breeding records, egg production
- **User & Access Control**: User accounts, roles, permissions, and organizational structure
- **Financial Data**: Recent harvest events, intercompany transactions (last fiscal year)
- **Audit History**: Critical audit trails for compliance requirements

### 1.2 Out of Scope
- Historical/closed batches (older than 24 months)
- Scenario planning data
- Archived environmental data (older than 12 months)
- Deprecated/inactive infrastructure records
- Legacy reporting configurations

### 1.3 Migration Constraints
- **Downtime Window**: Maximum 48 hours for complete cutover
- **Data Integrity**: Zero tolerance for data loss in active batches
- **AVEVA Historian Runtime**: The Historian backup now runs in the `aveva-sql` container (host port `1435`). Infrastructure extracts can shift to the `aveva_readonly` profile as soon as schema validation completes; keep FishTalk data in sync until we declare AVEVA canonical.
- **Historian Bridge Tables**: All AVEVA metadata must flow through the new `historian_tag`, `historian_tag_history`, and `historian_tag_link` tables before landing in AquaMind domain tables. Refresh with `python manage.py load_historian_tags --profile aveva_readonly --using <db>`.
- **Regulatory Compliance**: Must maintain audit trail continuity
- **Business Continuity**: Phased approach to minimize operational disruption

## 2. Migration Strategy

### 2.1 Migration Approach
**Hybrid ETL (Extract, Transform, Load) with Phased Cutover**

1. **Phase 1 - Foundation (Week 1-2)**
   - Infrastructure and reference data
   - User accounts and permissions
   - Container types and lifecycle stages

2. **Phase 2 - Core Operations (Week 3-4)**
   - Active batches and assignments
   - Inventory and feed data
   - Health records

3. **Phase 3 - Time-Series & Financial (Week 5)**
   - Environmental readings (TimescaleDB)
   - Financial transactions
   - Harvest records

4. **Phase 4 - Validation & Cutover (Week 6)**
   - Data validation and reconciliation
   - User acceptance testing
   - Final cutover

### 2.2 Technical Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    FishTalk     │────▶│   ETL Pipeline   │────▶│    AquaMind     │
│   SQL Server    │     │  Python/Django   │     │   PostgreSQL    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         │                       │                         │
         ▼                       ▼                         ▼
  [Extract Scripts]     [Transform Rules]        [Load & Validate]
  - SQL Queries        - Data Mapping            - Django Models
  - CSV Export         - Type Conversion         - TimescaleDB
  - API Calls          - Validation Rules        - Audit Logging
```

### 2.3 Migration Tools & Scripts

#### Core Migration Framework
```python
# Location: /scripts/migration/
fishtalk_migration/
├── __init__.py
├── config.py              # Connection settings, mapping rules
├── extractors/            # FishTalk data extraction
│   ├── batch_extractor.py
│   ├── infrastructure_extractor.py
│   └── health_extractor.py
├── transformers/          # Data transformation logic
│   ├── batch_transformer.py
│   ├── date_transformer.py
│   └── reference_transformer.py
├── loaders/              # AquaMind data loading
│   ├── batch_loader.py
│   ├── timescale_loader.py
│   └── validation.py
└── migrate.py            # Main orchestration script
```

## 3. Data Mapping Specifications

### 3.1 Entity Mapping Overview

| FishTalk Entity | AquaMind Entity | Mapping Complexity | Priority |
|-----------------|-----------------|-------------------|----------|
| Project/Batch | batch_batch | Complex | Critical |
| Unit/Container | infrastructure_container | Moderate | Critical |
| Individual Fish | batch_batchcontainerassignment | Complex | Critical |
| Feed Events | inventory_feedingevent | Moderate | High |
| Health Records | health_journalentry | Complex | High |
| Environmental | environmental_environmentalreading | Simple | High |
| Users | auth_user + users_userprofile | Moderate | Critical |
| Mortality | batch_mortalityevent | Simple | High |
| Treatments | health_treatment | Moderate | High |

### 3.2 Critical Field Mappings

#### Batch Migration
```sql
-- FishTalk to AquaMind mapping
FishTalk.Project => batch_batch
  ProjectID => external_id (store for reference)
  ProjectName => batch_number (with prefix "FT-")
  Species => species_id (lookup)
  Stage => lifecycle_stage_id (map via reference table)
  StartDate => start_date
  Status => status (map: Active=>ACTIVE, etc.)
  YearClass => notes (preserved in structured format)
  
FishTalk.Individual => batch_batchcontainerassignment
  IndividualID => (generate new, store mapping)
  ProjectID => batch_id (via lookup)
  UnitID => container_id (via lookup)
  Count => population_count
  AvgWeight => avg_weight_g
  Biomass => biomass_kg
  Stage => lifecycle_stage_id
```

### 3.3 Data Transformation Rules

#### Date/Time Handling
- All timestamps convert from FishTalk local time to UTC
- Preserve original timezone in metadata for audit
- Handle null dates with business logic defaults

#### Weight/Measurement Conversions
- FishTalk weights (kg) → AquaMind (g for individual, kg for biomass)
- Temperature: Maintain Celsius throughout
- Volumes: Convert to standard m³ for containers

#### Status Mappings
```python
STATUS_MAP = {
    'FishTalk': 'AquaMind',
    'Active': 'ACTIVE',
    'Inactive': 'INACTIVE', 
    'Terminated': 'CLOSED',
    'OnHold': 'INACTIVE'
}
```

## 4. Validation & Quality Assurance

### 4.1 Pre-Migration Validation
- [ ] Row count verification for all entities
- [ ] Referential integrity checks
- [ ] Duplicate detection and resolution
- [ ] Data type compatibility verification
- [ ] Required field completeness

### 4.2 Post-Migration Validation
- [ ] Record count reconciliation (±0% tolerance for critical data)
- [ ] Checksum validation for numerical data
- [ ] Business rule validation
- [ ] Relationship integrity verification
- [ ] Audit trail continuity check

### 4.3 Validation Queries
```sql
-- Example: Validate batch migration
SELECT 
    'FishTalk' as source,
    COUNT(*) as batch_count,
    SUM(TotalBiomass) as total_biomass,
    COUNT(DISTINCT Species) as species_count
FROM FishTalk.dbo.Projects
WHERE Status = 'Active'

UNION ALL

SELECT 
    'AquaMind' as source,
    COUNT(*) as batch_count,
    SUM(biomass_kg) as total_biomass,
    COUNT(DISTINCT species_id) as species_count
FROM batch_batch b
JOIN batch_batchcontainerassignment bca ON b.id = bca.batch_id
WHERE b.status = 'ACTIVE' 
  AND b.batch_number LIKE 'FT-%'
  AND bca.is_active = true;
```

## 5. Risk Management

### 5.1 Identified Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| Data corruption during transfer | Critical | Low | Checksums, transaction rollback capability |
| Extended downtime | High | Medium | Parallel run capability, rollback plan |
| Incomplete mapping coverage | High | Medium | Iterative validation, UAT feedback |
| Performance degradation | Medium | Low | Index optimization, batch processing |
| User adoption issues | Medium | High | Training, parallel run period |

### 5.2 Rollback Strategy
1. **Database Snapshots**: Create full backups before each phase
2. **Dual Running**: Maintain FishTalk read-only for 30 days post-migration
3. **Reverse ETL**: Prepared scripts to migrate back if critical issues
4. **Incremental Rollback**: Ability to rollback specific data domains

## 6. Execution Timeline

### Week 1-2: Preparation
- Environment setup and access configuration
- ETL pipeline development
- Reference data mapping completion
- Test environment preparation

### Week 3-4: Test Migration
- Execute full test migration
- Validate data integrity
- Performance testing
- Issue resolution and script refinement

### Week 5: UAT Preparation
- Load UAT environment
- User training materials
- Validation script execution
- Business user verification

### Week 6: Production Migration
- **Friday Evening**: Begin infrastructure migration
- **Saturday**: Core data migration
- **Sunday**: Validation and testing
- **Monday**: Go-live with monitoring

## 7. Success Criteria

### Quantitative Metrics
- 100% of active batches migrated successfully
- Zero data loss for financial transactions
- <2% variance in calculated metrics (FCR, biomass)
- All critical business processes operational

### Qualitative Metrics
- User acceptance of data accuracy
- Regulatory compliance maintained
- Audit trail integrity preserved
- System performance meets or exceeds baseline

## 8. Post-Migration Activities

### Immediate (Week 1)
- Performance monitoring and optimization
- User support and issue resolution
- Data reconciliation reports
- Audit trail verification

### Short-term (Month 1)
- Historical data migration assessment
- Process optimization
- Advanced feature enablement
- Training completion

### Long-term (Quarter 1)
- FishTalk decommissioning plan
- Data archival strategy
- Process improvement implementation
- ROI measurement

## Appendices

### A. Emergency Contacts
- Migration Lead: [Contact]
- Database Administrator: [Contact]
- Business Owner: [Contact]
- On-call Support: [Contact]

### B. Critical Queries Inventory
[To be populated with specific validation queries]

### C. Data Dictionary Cross-Reference
[Detailed field-by-field mapping table]

### D. Migration Checklist
[Comprehensive task checklist for execution]

---
**Document Control**
- Author: AquaMind Migration Team
- Review: Pending
- Approval: Pending
- Next Review: [Date]

