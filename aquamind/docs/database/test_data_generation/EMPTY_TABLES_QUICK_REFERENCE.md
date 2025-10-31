# Empty Tables Quick Reference

**Generated:** 2025-10-23  
**Empty Tables:** 65/146 (44.5%)

This document lists all empty tables grouped by priority for test data generation.

---

## 🚨 **CRITICAL - BLOCKING FEATURES (36 tables)**

### Broodstock App (21 tables) - **ENTIRE MODULE UNTESTED**
```
Status: 0% coverage
Impact: Broodstock management completely unusable
Priority: P0 - URGENT
```

**Core Tables:**
- ❌ `broodstock_maintenancetask` - Container maintenance tracking
- ❌ `broodstock_broodstockfish` - Individual fish records
- ❌ `broodstock_fishmovement` - Fish movements between containers
- ❌ `broodstock_breedingplan` - Breeding strategy definitions
- ❌ `broodstock_breedingtraitpriority` - Trait prioritization
- ❌ `broodstock_breedingpair` - Male/female pair assignments
- ❌ `broodstock_eggproduction` - Internal egg production
- ❌ `broodstock_eggsupplier` - External supplier info
- ❌ `broodstock_externaleggbatch` - External egg acquisition
- ❌ `broodstock_batchparentage` - Egg-to-batch lineage

**Historical Tables (11):**
- ❌ `broodstock_historical*` (all 10 corresponding tables)

**Recommended Script:** `scripts/data_generation/05_broodstock_lifecycle.py`

---

### Scenario Planning (13 tables) - **FEATURE UNUSABLE**
```
Status: 19% coverage (only templates)
Impact: Strategic planning impossible
Priority: P0 - URGENT
```

**Core Models:**
- ❌ `scenario` - Main scenario definitions
- ❌ `scenario_tgcmodel` - Growth models
- ❌ `scenario_fcrmodel` - Feed conversion models
- ❌ `scenario_mortalitymodel` - Mortality projections
- ❌ `scenario_biological_constraints` - Constraint sets
- ❌ `scenario_scenarioprojection` - Daily projections
- ❌ `scenario_scenariomodelchange` - Mid-scenario adjustments
- ❌ `scenario_tgc_model_stage` - Stage-specific TGC
- ❌ `scenario_fcr_model_stage_override` - Weight-based FCR
- ❌ `scenario_fcrmodelstage` - FCR by lifecycle stage
- ❌ `scenario_mortality_model_stage` - Stage-specific mortality
- ❌ `scenario_stage_constraint` - Biological limits per stage

**Historical Tables (1):**
- ❌ `scenario_historicalbiologicalconstraints`

**Recommended Script:** `scripts/data_generation/06_scenario_planning.py`

---

### Batch Composition (2 tables) - **MIXED BATCHES UNTESTED**
```
Status: Not implemented
Impact: Cannot test mixed batch scenarios
Priority: P2 - MEDIUM (if feature needed)
```

- ❌ `batch_batchcomposition` - Mixed batch tracking
- ❌ `batch_historicalbatchcomposition` - History

**Decision Required:** Is this feature needed or should tables be deprecated?

---

## ⚠️ **HIGH PRIORITY - IMPORTANT GAPS (23 tables)**

### Health App Advanced Features (16 tables)
```
Status: 30% coverage (basic only)
Impact: Advanced health monitoring untested
Priority: P1 - HIGH
```

**Detailed Health Sampling:**
- ❌ `health_healthsamplingevent` - Sampling sessions
- ❌ `health_individualfishobservation` - Per-fish data
- ❌ `health_fishparameterscore` - Individual fish scores
- ❌ `health_historicalhealthsamplingevent`
- ❌ `health_historicalindividualfishobservation`

**Lab Testing:**
- ❌ `health_healthlabsample` - Lab sample tracking
- ❌ `health_historicalhealthlabsample`

**Treatments:**
- ❌ `health_treatment` - Treatment administration
- ❌ `health_mortalityrecord` - Detailed mortality (vs batch_mortalityevent)
- ❌ `health_historicaltreatment`
- ❌ `health_historicalmortalityrecord`

**Lice System:**
- ❌ `health_historicallicetype` - Lice type changes

**Note:** `health_licetype` has 15 records but its historical table is empty

**Recommended:** Extend `03_event_engine_core.py` to add health sampling logic

---

### Environmental App (5 tables)
```
Status: 38% coverage
Impact: Weather integration untested, hypertable unused
Priority: P1 - HIGH
```

**Weather & Environmental:**
- ❌ `environmental_weatherdata` **← HYPERTABLE UNUSED!**
- ❌ `environmental_photoperioddata` - Light cycle data
- ❌ `environmental_stagetransitionenvironmental` - Transition conditions
- ❌ `environmental_historicalphotoperioddata`
- ❌ `environmental_historicalstagetransitionenvironmental`

**Critical Issue:** Weather data hypertable is created but never populated - wastes DB resources

**Recommended:** Add weather data generation to `03_event_engine_core.py`

---

### Finance App (6 tables)
```
Status: 50% coverage
Impact: Harvest financials and ERP export untested
Priority: P1 - HIGH
```

**Harvest Financials:**
- ❌ `finance_factharvest` - Harvest fact aggregation
- ❌ `finance_historicalfactharvest`

**NAV ERP Export:**
- ❌ `finance_navexportbatch` - Export batches
- ❌ `finance_navexportline` - Export line items
- ❌ `finance_historicalnavexportbatch`
- ❌ `finance_historicalnavexportline`

**Recommended:** Add harvest fact generation after harvest events in event engine

---

### Harvest App (4 tables)
```
Status: 56% coverage
Impact: Waste tracking not implemented
Priority: P2 - MEDIUM
```

- ❌ `harvest_harvestwaste` - Waste categorization
- ❌ `harvest_historicalharvestwaste`

**Decision Required:** Is waste tracking needed or planned feature?

---

## 📋 **LOW PRIORITY - ADMINISTRATIVE (6 tables)**

### Auth/User Management (5 tables)
```
Status: 44% coverage
Impact: RBAC system not configured
Priority: P2 - MEDIUM
```

- ❌ `auth_group` - User groups/roles
- ❌ `auth_group_permissions` - Group permissions
- ❌ `auth_user_groups` - User-group assignments
- ❌ `auth_user_user_permissions` - Direct user permissions

**Note:** Users exist (5 records) but not assigned to groups

**Recommended:** Add group/permission setup to `02_initialize_master_data.py`

---

### Django Admin (1 table)
```
Status: Low priority
Impact: Minimal - admin activity log
Priority: P3 - LOW
```

- ❌ `django_admin_log` - Admin interface action log

**Note:** Would only populate if admins use Django admin interface

---

## 📊 **Summary by Priority**

| Priority | Empty Tables | Apps Affected |
|----------|-------------|---------------|
| **P0 - CRITICAL** | 36 | Broodstock (21), Scenario (13), Batch Composition (2) |
| **P1 - HIGH** | 27 | Health (16), Environmental (5), Finance (6) |
| **P2 - MEDIUM** | 4 | Harvest (2), Auth (2) |
| **P3 - LOW** | 1 | Django (1) |
| **TOTAL** | **68** | **8 apps** |

**Note:** Total is 68 vs 65 because some historical tables counted separately

---

## ✅ **Recommended Action Plan**

### **Week 1-2: Critical Gaps**
```bash
# Priority 0 - Required for feature completeness
./scripts/data_generation/05_broodstock_lifecycle.py    # Populate 21 tables
./scripts/data_generation/06_scenario_planning.py        # Populate 13 tables
```

**Expected Impact:** +34 tables (23% → 78% coverage)

---

### **Week 3-4: High Priority**
```bash
# Priority 1 - Important for validation
# Extend existing event engine:
# - Add health sampling events
# - Add weather data generation
# - Add harvest fact generation
```

**Expected Impact:** +27 tables (78% → 97% coverage)

---

### **Week 5: Cleanup**
```bash
# Priority 2-3 - Nice to have
# - Configure user groups/permissions
# - Decide on batch composition
# - Decide on harvest waste
```

**Expected Impact:** +6 tables (97% → 100% coverage for base tables)

---

## 🔍 **Validation Queries**

Check which tables are still empty:

```sql
-- Get all empty tables
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename NOT LIKE 'django_%'
    AND tablename NOT LIKE 'auth_%'
ORDER BY tablename;

-- Then for each table:
SELECT COUNT(*) FROM <table_name>;
```

Or use Python:

```python
from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")

for table in cursor.fetchall():
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    if count == 0:
        print(f"❌ EMPTY: {table_name}")
```

---

## 📖 **Cross-References**

- **Full Analysis:** `DATABASE_TABLE_COVERAGE_ANALYSIS.md`
- **PRD:** `/docs/prd.md` - See sections 3.1.8 (Broodstock), 3.3.1 (Scenarios)
- **Data Model:** `/docs/database/data_model.md` - Schema definitions
- **Test Scripts:** `/scripts/data_generation/` - Current implementation

---

**End of Reference**








