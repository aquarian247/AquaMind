# AquaMind Database Table Coverage Analysis

**Generated:** 2025-10-23  
**Database Tables:** 146 base tables + 2 views  
**Test Data Coverage:** 81/146 (55.5%)

---

## Executive Summary

### 🎯 **Critical Finding: 44.5% of Database Tables Are EMPTY**

The test data generation scripts populate only **81 out of 146 tables** (55.5% coverage), leaving **65 tables completely empty**. This represents a significant gap in:

1. **Application Logic Validation** - Empty tables suggest untested code paths
2. **Integration Testing** - Missing test data prevents full system validation  
3. **Feature Completeness** - Some modules appear to be unused or incomplete
4. **Data Model Accuracy** - Schema vs. actual usage misalignment

---

## 📊 Coverage by App

### ✅ **FULLY COVERED APPS (100%)**

#### Infrastructure App (16/16 tables) ✓
```
All tables populated via: 01_bootstrap_infrastructure.py
```
- ✓ infrastructure_geography (2 records)
- ✓ infrastructure_area (43 records)
- ✓ infrastructure_freshwaterstation (23 records)
- ✓ infrastructure_hall (115 records)
- ✓ infrastructure_container (2,010 records)
- ✓ infrastructure_containertype (13 records)
- ✓ infrastructure_sensor (11,060 records)
- ✓ infrastructure_feedcontainer (238 records)
- ✓ All 8 corresponding historical tables

**Status:** ✅ **EXCELLENT** - Complete infrastructure simulation

---

#### Inventory App (12/12 tables) ✓
```
Populated via: 02_initialize_master_data.py + 03_event_engine_core.py
```
- ✓ inventory_feed (9 types)
- ✓ inventory_feedpurchase (94,975 purchases - FIFO system working)
- ✓ inventory_feedcontainerstock (94,498 stock entries)
- ✓ inventory_feedingevent (691,920 feeding events)
- ✓ inventory_batchfeedingsummary (14 summaries)
- ✓ inventory_containerfeedingsummary (138 summaries)
- ✓ All 6 corresponding historical tables (1.8M+ history records)

**Status:** ✅ **EXCELLENT** - Complete feed management lifecycle

---

### ⚠️ **PARTIALLY COVERED APPS**

#### Batch App (15/17 tables - 88%)
```
Populated via: 03_event_engine_core.py
```

**POPULATED:**
- ✓ batch_batch (54 batches)
- ✓ batch_batchcontainerassignment (2,942 assignments)
- ✓ batch_batchtransferworkflow (242 workflows)
- ✓ batch_transferaction (2,402 actions)
- ✓ batch_growthsample (49,580 samples)
- ✓ batch_mortalityevent (393,400 events)
- ✓ batch_species (1 species)
- ✓ batch_lifecyclestage (6 stages)
- ✓ All historical tables (1.5M+ history records)

**EMPTY:**
- ✗ batch_batchcomposition (0 records)
- ✗ batch_historicalbatchcomposition (0 records)

**Gap Impact:** **MEDIUM**  
**Reason:** Batch composition is for mixed batches - appears unused or planned feature  
**Recommendation:** Either populate with test data or deprecate if unused

---

#### Health App (7/23 tables - 30%)
```
Populated via: 02_initialize_master_data.py + 03_event_engine_core.py
```

**POPULATED:**
- ✓ health_healthparameter (9 parameters)
- ✓ health_journalentry (1,330 entries)
- ✓ health_licecount (100,068 counts)
- ✓ health_licetype (15 types)
- ✓ health_mortalityreason (8 reasons)
- ✓ health_sampletype (5 types)
- ✓ health_vaccinationtype (3 types)
- ✓ Corresponding historical tables (265K+ history records)

**EMPTY (Critical Gap):**
- ✗ health_healthsamplingevent (0 records)
- ✗ health_individualfishobservation (0 records)
- ✗ health_fishparameterscore (0 records)
- ✗ health_healthlabsample (0 records)
- ✗ health_mortalityrecord (0 records) **← Different from batch_mortalityevent**
- ✗ health_treatment (0 records)
- ✗ All corresponding historical tables (16 empty tables)

**Gap Impact:** **HIGH**  
**Reason:** Advanced health monitoring features completely untested  
**Missing Validation:**
- Individual fish health observations
- Lab sample tracking
- Treatment administration
- Detailed health scoring

**Recommendation:** **CRITICAL** - Add health sampling and treatment simulation to event engine

---

#### Environmental App (3/8 tables - 38%)
```
Populated via: 02_initialize_master_data.py + 03_event_engine_core.py
```

**POPULATED:**
- ✓ environmental_environmentalparameter (7 parameters)
- ✓ environmental_environmentalreading (12.3M readings) **← Hypertable**
- ✓ Corresponding historical tables

**EMPTY (Critical Gap):**
- ✗ environmental_weatherdata (0 records) **← Hypertable - unused!**
- ✗ environmental_photoperioddata (0 records)
- ✗ environmental_stagetransitionenvironmental (0 records)
- ✗ Corresponding historical tables

**Gap Impact:** **HIGH**  
**Reason:** Weather data hypertable is created but never populated  
**Missing Validation:**
- External weather API integration (OpenWeatherMap)
- Photoperiod data for growth correlation
- Stage transition environmental conditions

**Recommendation:** **CRITICAL** - Add weather data generation to validate hypertable functionality

---

#### Harvest App (5/9 tables - 56%)
```
Populated via: 03_event_engine_core.py (harvest logic)
```

**POPULATED:**
- ✓ harvest_harvestevent (380 events)
- ✓ harvest_harvestlot (1,900 lots)
- ✓ harvest_productgrade (5 grades)
- ✓ Corresponding historical tables (7.2K history records)

**EMPTY:**
- ✗ harvest_harvestwaste (0 records)
- ✗ harvest_historicalharvestwaste (0 records)

**Gap Impact:** **MEDIUM**  
**Reason:** Waste tracking is a planned feature but not implemented  
**Recommendation:** Add waste generation to harvest events or deprecate if not needed

---

#### Finance App (6/12 tables - 50%)
```
Populated via: Automatic intercompany detection in transfer workflows
```

**POPULATED:**
- ✓ finance_dimcompany (4 companies)
- ✓ finance_dimsite (66 sites)
- ✓ finance_intercompanypolicy (6 policies)
- ✓ finance_intercompanytransaction (89 transactions)
- ✓ Corresponding historical tables

**EMPTY (Critical Gap):**
- ✗ finance_factharvest (0 records)
- ✗ finance_navexportbatch (0 records)
- ✗ finance_navexportline (0 records)
- ✗ Corresponding historical tables (3 empty tables)

**Gap Impact:** **HIGH**  
**Reason:** Harvest fact table and NAV export system completely untested  
**Missing Validation:**
- Harvest financial fact aggregation
- ERP export functionality
- Revenue recognition logic

**Recommendation:** **HIGH PRIORITY** - Add harvest fact generation and NAV export simulation

---

### ❌ **ZERO COVERAGE APPS (Critical Gaps)**

#### Broodstock App (0/21 tables - 0%) ❌
```
NO TEST DATA GENERATION
```

**ALL TABLES EMPTY:**
- ✗ broodstock_maintenancetask
- ✗ broodstock_broodstockfish
- ✗ broodstock_fishmovement
- ✗ broodstock_breedingplan
- ✗ broodstock_breedingtraitpriority
- ✗ broodstock_breedingpair
- ✗ broodstock_eggproduction
- ✗ broodstock_eggsupplier
- ✗ broodstock_externaleggbatch
- ✗ broodstock_batchparentage
- ✗ All 10 corresponding historical tables

**Gap Impact:** 🚨 **CRITICAL - ENTIRE MODULE UNTESTED**  
**Missing Validation:**
- Container maintenance tracking
- Broodstock fish lifecycle
- Breeding operations
- Egg production (internal)
- External egg acquisition
- Batch parentage/lineage
- Complete audit trail

**Business Impact:**  
The PRD states broodstock management is a "core component" for:
- Genetic improvement programs
- Breeding optimization
- Egg traceability (internal + external)
- Quality control for regulatory compliance

**Recommendation:** 🚨 **URGENT** - Create dedicated broodstock test data generation script:
```python
scripts/data_generation/05_broodstock_lifecycle.py
```

**Suggested Content:**
1. Create broodstock containers in existing infrastructure
2. Populate with broodstock fish (male/female)
3. Create breeding plans with trait priorities
4. Generate breeding pairs
5. Simulate egg production (internal)
6. Add external egg supplier data
7. Link eggs to batches via BatchParentage
8. Add maintenance tasks
9. Simulate fish movements between containers

---

#### Scenario App (3/16 tables - 19%, but core models 0%)
```
Partial data from historical scenario runs
```

**POPULATED (Templates Only):**
- ✓ scenario_temperatureprofile (4 profiles)
- ✓ scenario_temperaturereading (535 readings)
- ✓ scenario_historicaltemperatureprofile (4 historical)

**EMPTY (All Core Models):**
- ✗ scenario (0 scenarios)
- ✗ scenario_tgcmodel (0 models)
- ✗ scenario_fcrmodel (0 models)
- ✗ scenario_mortalitymodel (0 models)
- ✗ scenario_biological_constraints (0 constraints)
- ✗ scenario_scenarioprojection (0 projections)
- ✗ scenario_scenariomodelchange (0 changes)
- ✗ All stage override tables (0 records)

**Gap Impact:** 🚨 **CRITICAL - FEATURE UNUSABLE**  
**Reason:** Only temperature templates exist; no actual scenario planning possible  
**Missing Validation:**
- TGC/FCR/Mortality model creation
- Scenario simulation
- Projection calculations
- Biological constraint validation
- Multi-method data entry (CSV, date ranges, formulas)

**Business Impact:**  
The PRD dedicates an entire section (3.3.1) to Scenario Planning:
- "Cornerstone of salmon farming management"
- "Enables proactive optimization of harvest schedules"
- "Supports data-driven decision-making"

**Recommendation:** 🚨 **HIGH PRIORITY** - Create scenario test data generation:
```python
scripts/data_generation/06_scenario_planning.py
```

**Suggested Content:**
1. Create biological constraint sets (Bakkafrost Standard, Conservative)
2. Create TGC models for different locations/seasons
3. Create FCR models with stage-specific values
4. Create mortality models with stage overrides
5. Generate scenarios linking models + initial conditions
6. Run projections to populate projection table
7. Test model changes mid-scenario

---

## 🔍 Additional Findings

### 1. **Auth/User Tables Partially Used**
```
✗ auth_group (0 records) - Role-based access control not configured
✗ auth_group_permissions (0 records)
✗ auth_user_groups (0 records)
✗ auth_user_user_permissions (0 records)
```
**Impact:** MEDIUM - Permissions system untested  
**Recommendation:** Add user/group/permission setup to master data script

---

### 2. **Historical Tables Well-Populated**
```
Most populated tables have corresponding historical tables
Total historical records: ~6.5M
```
**Status:** ✅ EXCELLENT - django-simple-history working correctly

---

### 3. **Hypertables Status**
```
✓ environmental_environmentalreading: 12.3M records (WORKING)
✗ environmental_weatherdata: 0 records (UNUSED)
```
**Impact:** HIGH - One hypertable completely unused  
**Recommendation:** Either populate with weather data or remove if unnecessary

---

## 📋 Prioritized Recommendations

### 🚨 **CRITICAL (Required for Feature Completeness)**

#### 1. **Broodstock Module** (Estimated: 3-5 days)
```bash
Priority: P0 - BLOCKING
Impact: Entire module unusable
Effort: HIGH
```
**Action Items:**
- [ ] Create `05_broodstock_lifecycle.py` script
- [ ] Populate all 21 broodstock tables
- [ ] Link to existing batch data via BatchParentage
- [ ] Validate audit trail completeness

---

#### 2. **Scenario Planning** (Estimated: 2-3 days)
```bash
Priority: P0 - BLOCKING
Impact: Strategic planning feature unusable
Effort: MEDIUM
```
**Action Items:**
- [ ] Create `06_scenario_planning.py` script
- [ ] Populate TGC/FCR/Mortality models
- [ ] Generate test scenarios with projections
- [ ] Validate biological constraints

---

#### 3. **Weather Data Integration** (Estimated: 1-2 days)
```bash
Priority: P1 - HIGH
Impact: Hypertable unused, external API untested
Effort: MEDIUM
```
**Action Items:**
- [ ] Add weather data generation to event engine
- [ ] Validate hypertable compression
- [ ] Test OpenWeatherMap integration patterns

---

### ⚠️ **HIGH PRIORITY (Important for System Validation)**

#### 4. **Advanced Health Monitoring** (Estimated: 2-3 days)
```bash
Priority: P1 - HIGH
Impact: 16 empty health tables
Effort: MEDIUM
```
**Action Items:**
- [ ] Add health sampling events to event engine
- [ ] Generate individual fish observations
- [ ] Populate lab sample tracking
- [ ] Add treatment administration simulation

---

#### 5. **Finance Harvest Facts & NAV Export** (Estimated: 1-2 days)
```bash
Priority: P1 - HIGH
Impact: Financial reporting untested
Effort: MEDIUM
```
**Action Items:**
- [ ] Generate harvest fact table from harvest events
- [ ] Create NAV export batches
- [ ] Populate export lines
- [ ] Validate ERP export logic

---

### 📌 **MEDIUM PRIORITY (Nice to Have)**

#### 6. **Batch Composition** (Estimated: 1 day)
```bash
Priority: P2 - MEDIUM
Impact: Mixed batch feature untested
Effort: LOW
```
**Action Items:**
- [ ] Determine if feature is needed
- [ ] If yes: Add mixed batch scenarios
- [ ] If no: Deprecate tables via migration

---

#### 7. **Harvest Waste Tracking** (Estimated: 1 day)
```bash
Priority: P2 - MEDIUM
Impact: Waste reporting untested
Effort: LOW
```
**Action Items:**
- [ ] Add waste generation to harvest events
- [ ] Validate waste categorization

---

#### 8. **User/Group/Permission Setup** (Estimated: 1 day)
```bash
Priority: P2 - MEDIUM
Impact: RBAC system untested
Effort: LOW
```
**Action Items:**
- [ ] Create test users with different roles
- [ ] Configure permission groups
- [ ] Validate access control

---

## 🎯 **Testing Strategy Recommendations**

### **Current State:**
✅ Core operational loop (batch → container → feed → environmental → mortality) is **well-tested**  
❌ Advanced features (broodstock, scenarios, health sampling, finance) are **completely untested**

### **Target State:**
Achieve **90%+ table coverage** by adding:
1. Broodstock lifecycle simulation (+21 tables)
2. Scenario planning generation (+13 tables)
3. Advanced health monitoring (+16 tables)
4. Finance fact/export generation (+6 tables)

**Expected Coverage After Improvements:**
```
Current: 81/146 (55.5%)
Target:  137/146 (93.8%)
Remaining gaps: Mostly django/auth administrative tables
```

---

## 🔬 **Validation Methodology**

### **How to Validate Application Logic Usage:**

#### 1. **Code Path Analysis**
```python
# For each empty table, check if any code references it:
git grep -n "HealthSamplingEvent" apps/
git grep -n "Scenario.objects" apps/
```

**Finding:** If code exists but table is empty → **Test gap**  
**Finding:** If no code references table → **Unused schema**

---

#### 2. **API Endpoint Testing**
```bash
# Check if endpoints exist for empty tables:
python manage.py show_urls | grep scenario
python manage.py show_urls | grep broodstock
```

**Finding:** If endpoints exist but tables empty → **Untested endpoints**

---

#### 3. **Model Signal/Save Method Analysis**
```python
# Check for save() methods that should populate data:
grep -r "def save(" apps/broodstock/models.py
grep -r "def save(" apps/scenario/models.py
```

**Finding:** If save() has logic but table empty → **Logic untested**

---

## 📊 **Summary Statistics**

### **Table Coverage by Category:**

| Category | Total Tables | Populated | Empty | Coverage |
|----------|-------------|-----------|-------|----------|
| **Infrastructure** | 16 | 16 | 0 | 100% ✅ |
| **Inventory** | 12 | 12 | 0 | 100% ✅ |
| **Batch** | 17 | 15 | 2 | 88% ✅ |
| **Harvest** | 9 | 5 | 4 | 56% ⚠️ |
| **Finance** | 12 | 6 | 6 | 50% ⚠️ |
| **Environmental** | 8 | 3 | 5 | 38% ⚠️ |
| **Health** | 23 | 7 | 16 | 30% ⚠️ |
| **Scenario** | 16 | 3 | 13 | 19% ❌ |
| **Broodstock** | 21 | 0 | 21 | 0% ❌ |
| **Auth/Users** | 9 | 4 | 5 | 44% ⚠️ |
| **Django Admin** | 3 | 2 | 1 | 67% ✅ |
| **TOTAL** | **146** | **81** | **65** | **55.5%** |

---

### **Data Volume Statistics:**

| Data Type | Record Count |
|-----------|-------------|
| Environmental Readings | 12,342,000 |
| Historical Records (All) | ~6,500,000 |
| Feeding Events | 691,920 |
| Batch Container Assignments | 2,942 |
| Mortality Events | 393,400 |
| Growth Samples | 49,580 |
| Lice Counts | 100,068 |
| Feed Purchases | 94,975 |
| Sensors | 11,060 |
| Containers | 2,010 |
| Batches | 54 |

**Total DB Size Estimate:** ~80-100 GB (primarily environmental readings)

---

## ✅ **Action Plan Summary**

### **Phase 1: Critical Gaps (2-3 weeks)**
1. ✅ Review findings with team
2. ⬜ Create broodstock test data script
3. ⬜ Create scenario planning test data script
4. ⬜ Add weather data generation
5. ⬜ Add health sampling simulation

### **Phase 2: High Priority (1-2 weeks)**
6. ⬜ Add finance fact/NAV export generation
7. ⬜ Expand health monitoring (treatments, lab samples)
8. ⬜ User/group/permission configuration

### **Phase 3: Cleanup (1 week)**
9. ⬜ Decide on batch composition: implement or deprecate
10. ⬜ Decide on harvest waste: implement or deprecate
11. ⬜ Final validation sweep

### **Target: 90%+ Coverage by End of Phase 3**

---

## 🔗 **References**

- **PRD:** `/AquaMind/aquamind/docs/prd.md`
- **Data Model:** `/AquaMind/aquamind/docs/database/data_model.md`
- **Test Scripts:** `/AquaMind/scripts/data_generation/`
- **Test Guide:** `/AquaMind/aquamind/docs/database/test_data_generation/test_data_generation_guide.md`

---

**End of Analysis**









