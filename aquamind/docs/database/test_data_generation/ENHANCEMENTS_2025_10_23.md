# Test Data Generation Enhancements

**Date:** 2025-10-23  
**Script:** `scripts/data_generation/03_event_engine_core.py`  
**Status:** ✅ Ready for testing (DO NOT RUN until after demo)

---

## 🎯 **What Was Added**

### **1. Finance Harvest Fact Generation** ✅

**Purpose:** Populate `finance_factharvest` table for financial reporting and BI integration

**Implementation:**
```python
# Location: Lines 768-805
def _generate_finance_harvest_facts(self):
    """Generate finance fact table entries from harvest events."""
    
    # For each harvest event and lot:
    # - Create FactHarvest record
    # - Link to finance dimensions (DimCompany, DimSite)
    # - Capture quantity, unit count, batch, grade
    # - Enable BI views (vw_fact_harvest)
```

**What Gets Created:**
- ✅ Finance fact records for each harvest lot (5 grades per container)
- ✅ Company dimensions (auto-created per geography)
- ✅ Site dimensions (freshwater stations + sea areas)
- ✅ Linkage to harvest events, lots, and product grades

**Expected Data Volume:**
```
Per Batch:
  - 10 containers harvested
  - 5 lots per container (5 grades)
  - = 50 finance facts per batch

For 54 batches (if all harvest):
  - ~2,700 finance facts
  - Enables revenue analysis by geography, site, grade
```

---

### **2. Sea Transition Scenario Generation** ✅

**Purpose:** Create realistic "From Batch" scenarios at Post-Smolt → Adult transition

**Implementation:**
```python
# Location: Lines 807-847
def _create_sea_transition_scenario(self, transition_date):
    """
    Create growth forecast scenario when batch transitions to sea.
    Uses shared models to avoid duplication.
    """
    
    # Creates scenario with:
    # - Current batch population and weight as starting point
    # - 450-day forecast (Adult stage duration)
    # - Linked to shared TGC/FCR/Mortality models
    # - Geography-specific temperature profile
```

**What Gets Created:**
```
One scenario per batch at sea transition (Post-Smolt → Adult)

Scenario includes:
  - Name: "Sea Growth Forecast - {batch_number}"
  - Initial conditions from current batch state
  - 450-day duration (Adult stage)
  - Link to batch for traceability
  - Shared models (no duplication)
```

**Expected Data Volume:**
```
For 54 batches:
  - 54 scenarios (one per batch at sea transition)
  - 2 TGC models (Faroe Islands, Scotland)
  - 2 Temperature profiles (different sea temps)
  - 1 FCR model (shared, with 6 stage-specific values)
  - 1 Mortality model (shared)
  - ~900 temperature readings (450 days × 2 profiles)
```

---

### **3. Shared Scenario Models (Reused Across Batches)** ✅

**Purpose:** Avoid creating duplicate models for every batch

**Implementation:**
```python
# Location: Lines 124-235
def _init_scenario_models(self):
    """Initialize shared models reused across all batches."""
    
    # Creates/gets:
    # 1. TGC Model (geography-specific)
    # 2. FCR Model (shared, with stage values)
    # 3. Mortality Model (shared)
    # 4. Temperature Profile (geography-specific)
```

**Key Features:**
- ✅ One TGC model per geography (Faroe vs Scotland)
- ✅ One FCR model (shared across all batches)
- ✅ Stage-specific FCR values (Fry: 1.0, Parr: 1.1, Smolt: 1.0, etc.)
- ✅ One Mortality model (shared)
- ✅ Geography-specific temperature profiles

**Temperature Profile Details:**

**Faroe Islands:**
```python
# Gulf Stream influence = stable temps
Base: 9.5°C
Seasonal variation: ±1.0°C
Daily variation: ±0.3°C
Range: 8-11°C (narrow, stable)
Pattern: Subtle seasonal sine wave
```

**Scotland:**
```python
# More variable coastal temps
Base: 10.0°C
Seasonal variation: ±3.0°C
Daily variation: ±0.5°C
Range: 6-14°C (wider variation)
Pattern: Strong summer peak, colder winters
```

---

### **4. Finance Dimension Auto-Creation** ✅

**Implementation:**
```python
# Location: Lines 80-122
def _init_finance_dimensions(self):
    """Initialize finance company and site dimensions."""
    
    # Creates:
    # - DimCompany (one per geography, FARMING subsidiary)
    # - DimSite for freshwater station
    # - DimSite for sea area
```

**What Gets Created:**
```
Per Geography:
  - 1 DimCompany (Faroe Islands Farming / Scotland Farming)
  - Currency: EUR (Faroe) / GBP (Scotland)
  - Multiple DimSites (one per station + area)
```

---

## 📊 **Expected Coverage Improvement**

### **Before Enhancement:**

| App | Empty Tables | Coverage |
|-----|-------------|----------|
| **Finance** | 6/12 | 50% |
| **Scenario** | 13/16 | 19% |

### **After Enhancement:**

| App | Empty Tables | Coverage |
|-----|-------------|----------|
| **Finance** | 2/12 | 83% ✅ (+33%) |
| **Scenario** | 7/16 | 56% ✅ (+37%) |

**Tables Now Populated:**
```
Finance:
  ✅ finance_factharvest (was empty, now ~2,700 records)
  ✅ All DimCompany/DimSite auto-created

Scenario:
  ✅ scenario (was empty, now ~54 scenarios)
  ✅ scenario_tgcmodel (2 models)
  ✅ scenario_fcrmodel (1 model)
  ✅ scenario_fcrmodelstage (6 stage values)
  ✅ scenario_mortalitymodel (1 model)
  ✅ scenario_temperatureprofile (2 profiles)
  ✅ scenario_temperaturereading (900 readings)
```

**Still Empty (Not Needed for Basic Scenarios):**
```
Scenario (Advanced Features):
  - scenario_biological_constraints (future)
  - scenario_stage_constraint (future)
  - scenario_scenarioprojection (requires running scenarios)
  - scenario_scenariomodelchange (mid-scenario adjustments)
  - scenario_tgc_model_stage (stage-specific TGC overrides)
  - scenario_fcr_model_stage_override (weight-based FCR overrides)
  - scenario_mortality_model_stage (stage-specific mortality)

Finance (Not Harvest Related):
  - finance_navexportbatch (ERP export feature)
  - finance_navexportline (ERP export feature)
```

---

## 🚀 **How to Test (After Demo)**

### **Option 1: Fresh Start (Recommended)**
```bash
cd /Users/aquarian247/Projects/AquaMind

# Clean existing data
python scripts/data_generation/cleanup_batch_data.py

# Rebuild infrastructure and master data
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py

# Generate one test batch to validate enhancements
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2024-01-03 \
  --eggs 3500000 \
  --geography "Faroe Islands" \
  --duration 650

# Expected new output:
# ✓ Scenario models ready: TGC=0.00245, FCR=Standard, Mortality=0.03%
# ✓ Finance dimensions ready: Faroe Islands Farming
# ...
# → Stage Transition: Post-Smolt → Adult
#   ✓ Created scenario: Sea Growth Forecast - FI-2024-001
#     Initial: 3,200,000 fish @ 450g
#     Duration: 450 days (Adult stage)
#     Models: Faroe Islands Standard TGC, Standard Atlantic Salmon FCR
# ...
# ✓ Generated 50 finance harvest facts
```

### **Option 2: Add to Existing Data**
```bash
# Generate new batches (will use shared models)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 \
  --eggs 3200000 \
  --geography "Scotland" \
  --duration 550

# This will:
# - Reuse existing TGC/FCR/Mortality models
# - Create Scotland temperature profile (if not exists)
# - Generate scenario at sea transition
# - Generate finance facts at harvest
```

---

## ✅ **Validation Queries**

### **Check Finance Facts Created:**
```sql
SELECT 
    fh.fact_id,
    fh.event_date,
    b.batch_number,
    pg.code as grade,
    fh.quantity_kg,
    fh.unit_count,
    dc.display_name as company,
    ds.site_name as site
FROM finance_factharvest fh
JOIN batch_batch b ON fh.dim_batch_id = b.id
JOIN harvest_productgrade pg ON fh.product_grade_id = pg.id
JOIN finance_dimcompany dc ON fh.dim_company_id = dc.company_id
JOIN finance_dimsite ds ON fh.dim_site_id = ds.site_id
ORDER BY fh.event_date DESC, b.batch_number
LIMIT 20;

-- Expected: 5 rows per batch (one per grade)
```

### **Check Scenarios Created:**
```sql
SELECT 
    s.scenario_id,
    s.name,
    s.start_date,
    s.duration_days,
    s.initial_count,
    s.initial_weight,
    b.batch_number,
    tm.name as tgc_model,
    fm.name as fcr_model,
    tp.name as temp_profile
FROM scenario s
JOIN batch_batch b ON s.batch_id = b.id
JOIN scenario_tgcmodel tm ON s.tgc_model_id = tm.model_id
JOIN scenario_fcrmodel fm ON s.fcr_model_id = fm.model_id
JOIN scenario_temperatureprofile tp ON tm.profile_id = tp.profile_id
ORDER BY s.start_date;

-- Expected: 1 row per batch at Adult stage transition
```

### **Check Temperature Profiles:**
```sql
SELECT 
    tp.name,
    COUNT(tr.reading_id) as reading_count,
    ROUND(AVG(tr.temperature), 2) as avg_temp,
    ROUND(MIN(tr.temperature), 2) as min_temp,
    ROUND(MAX(tr.temperature), 2) as max_temp
FROM scenario_temperatureprofile tp
LEFT JOIN scenario_temperaturereading tr ON tr.profile_id = tp.profile_id
GROUP BY tp.profile_id, tp.name
ORDER BY tp.name;

-- Expected:
-- Faroe Islands Sea Temperature: 450 readings, avg ~9.5°C, range 8-11°C
-- Scotland Sea Temperature: 450 readings, avg ~10.0°C, range 6-14°C
```

### **Check Model Reuse:**
```sql
-- Should see shared models across batches
SELECT 
    'TGC Models' as model_type,
    COUNT(DISTINCT tgc_model_id) as unique_models,
    COUNT(DISTINCT s.scenario_id) as scenarios_using
FROM scenario s
GROUP BY 1

UNION ALL

SELECT 
    'FCR Models',
    COUNT(DISTINCT fcr_model_id),
    COUNT(DISTINCT s.scenario_id)
FROM scenario s
GROUP BY 1

UNION ALL

SELECT 
    'Mortality Models',
    COUNT(DISTINCT mortality_model_id),
    COUNT(DISTINCT s.scenario_id)
FROM scenario s
GROUP BY 1;

-- Expected:
-- TGC Models: 2 unique (Faroe, Scotland), 54 scenarios
-- FCR Models: 1 unique (shared), 54 scenarios
-- Mortality Models: 1 unique (shared), 54 scenarios
```

---

## 📋 **Code Changes Summary**

### **New Imports:**
```python
from apps.finance.models import FactHarvest, DimCompany, DimSite
from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, MortalityModel, 
    TemperatureProfile, TemperatureReading, FCRModelStage
)
```

### **New Methods:**
```python
1. _init_finance_dimensions()          # Lines 80-122
2. _init_scenario_models()             # Lines 124-184
3. _get_or_create_temperature_profile() # Lines 186-235
4. _generate_finance_harvest_facts()   # Lines 768-805
5. _create_sea_transition_scenario()   # Lines 807-847
```

### **Integration Points:**
```python
1. init() → Calls _init_finance_dimensions() and _init_scenario_models()
2. check_stage_transition() → Calls _create_sea_transition_scenario() when Adult stage
3. harvest_batch() → Calls _generate_finance_harvest_facts() after harvest
```

### **Stats Tracking:**
```python
Added:
  - 'scenarios': Count of scenarios created
  - 'finance_facts': Count of finance facts generated
  
Output includes these counts in final summary
```

---

## 🔍 **What Happens During Execution**

### **Initialization (Once Per Batch):**
```
1. Geography detected (Faroe Islands or Scotland)
2. Finance company/sites created or retrieved
3. TGC model created/retrieved (geography-specific)
4. FCR model created/retrieved (shared, with stages)
5. Mortality model created/retrieved (shared)
6. Temperature profile created if new (geography-specific)
   - Faroe: 9.5°C avg, stable (8-11°C)
   - Scotland: 10°C avg, variable (6-14°C)
```

### **During Lifecycle (Day ~360):**
```
Post-Smolt → Adult Transition:
  1. Move fish to sea cages
  2. Create scenario "Sea Growth Forecast - {batch_number}"
     - Initial: Current population @ current weight
     - Duration: 450 days
     - Models: Shared TGC/FCR/Mortality + Geography temp profile
  3. Print scenario details
```

### **At Harvest (Day ~650-900):**
```
When batch reaches 4kg+ in Adult stage:
  1. Create harvest events (one per container)
  2. Create harvest lots (5 grades per event)
  3. Generate finance facts (one per lot)
     - Link to DimCompany (geography + FARMING)
     - Link to DimSite (sea area)
     - Include quantity, grade, batch
  4. Print fact count
```

---

## 📊 **Sample Output**

### **Initialization:**
```
================================================================================
Initializing Event Engine
================================================================================

✓ Geography: Faroe Islands
✓ Station: FI-FW-01
✓ Sea Area: FI-Sea-01
✓ Created temperature profile: Faroe Islands Sea Temperature (avg: 9.5°C)
✓ Scenario models ready: TGC=0.00245, FCR=Standard, Mortality=0.03%
✓ Finance dimensions ready: Faroe Islands Farming
✓ Duration: 650 days
```

### **Sea Transition (Day ~360):**
```
  → Stage Transition: Post-Smolt → Adult
  → Moved to Sea Cages in Faroe Islands (10 containers across 3 areas)
  ✓ Created scenario: Sea Growth Forecast - FI-2024-001
    Initial: 3,200,000 fish @ 450g
    Duration: 450 days (Adult stage)
    Models: Faroe Islands Standard TGC, Standard Atlantic Salmon FCR
```

### **Harvest (Day 650):**
```
================================================================================
HARVESTING BATCH
================================================================================

✓ Harvested 10 containers
✓ Total fish harvested: 3,150,000
✓ Average weight: 5,200g
✓ Total biomass: 16,380,000kg
✓ Generated 50 finance harvest facts
```

### **Final Summary:**
```
Event Counts:
  Environmental: 273,000 (6 readings/day/sensor)
  Feeding: 13,000
  Mortality: 8,500
  Growth Samples: 780
  Lice Counts: 42 (Adult stage weekly)
  Feed Purchases: 195
  Scenarios: 1 (sea transition forecast)
  Finance Facts: 50 (harvest facts)
```

---

## 🎯 **Benefits**

### **Finance Harvest Facts:**
✅ Enables BI reporting on harvest revenue  
✅ Validates finance dimension system  
✅ Tests company/site linkage  
✅ Populates BI views (vw_fact_harvest)  
✅ No backfill needed for new batches

### **Scenario Generation:**
✅ Creates realistic "From Batch" scenarios  
✅ Validates scenario planning feature  
✅ Tests TGC/FCR/Mortality model system  
✅ Geography-specific temperature profiles  
✅ Model reuse prevents duplication  
✅ Automatic creation at key decision point (sea transition)

### **Model Efficiency:**
✅ **2 TGC models** instead of 54 (one per batch)  
✅ **1 FCR model** shared across all batches  
✅ **1 Mortality model** shared across all batches  
✅ **2 Temperature profiles** instead of 54  
✅ Reduces redundancy by ~95%

---

## ⚠️ **Known Limitations**

### **Scenario Projections Not Generated:**
```
Current: Creates scenario definition only
Not Yet: Running projection calculations

Reason: Projection calculation is complex (900 daily calculations per scenario)
Impact: Scenario exists but no projection data
Workaround: Run projections via API or frontend
Future: Could add projection generation to script
```

### **NAV Export Not Included:**
```
Tables Still Empty:
  - finance_navexportbatch
  - finance_navexportline

Reason: Feature needs more clarity on requirements
Decision: Defer until NAV export requirements finalized
```

### **Advanced Scenario Features:**
```
Not Included:
  - BiologicalConstraints (constraint sets)
  - ScenarioModelChange (mid-scenario adjustments)
  - Stage-specific TGC/FCR/Mortality overrides

Reason: Basic scenarios sufficient for testing
Future: Add if needed for advanced scenario validation
```

---

## 🔧 **Troubleshooting**

### **Issue: "Finance dimension setup failed"**
```
Cause: Missing DimCompany or DimSite data
Solution: Check if geography exists, verify ForeignKey constraints
Impact: Finance facts won't generate (but harvest still works)
```

### **Issue: "Scenario creation failed"**
```
Cause: Missing TGC/FCR/Mortality models
Solution: Check _init_scenario_models() output for errors
Impact: Scenarios won't generate (but lifecycle continues)
```

### **Issue: Temperature profile creation fails**
```
Cause: NumPy not available or database constraint violation
Solution: Ensure numpy installed, check for duplicate profiles
Impact: TGC model creation fails (scenarios won't work)
```

---

## 📖 **References**

- **PRD Finance Section:** `/docs/prd.md` Section 3.1.10 (Finance Management)
- **PRD Scenario Section:** `/docs/prd.md` Section 3.3.1 (Scenario Planning)
- **Data Model Finance:** `/docs/database/data_model.md` Section 4.6
- **Data Model Scenario:** `/docs/database/data_model.md` Section 4.10
- **Coverage Analysis:** `DATABASE_TABLE_COVERAGE_ANALYSIS.md`

---

## ✅ **Pre-Run Checklist**

Before running enhanced script:

- [ ] Backup current database (if preserving demo data)
- [ ] Verify migrations are current: `python manage.py migrate`
- [ ] Check ProductGrade exists: `python manage.py shell -c "from apps.harvest.models import ProductGrade; print(ProductGrade.objects.count())"`
- [ ] Confirm NumPy installed: `python -c "import numpy; print('OK')"`
- [ ] Review script changes (git diff if tracked)

---

## 🎯 **Success Criteria**

After running enhanced script:

✅ Finance harvest facts table populated (5 per container harvested)  
✅ Scenarios created (1 per batch at sea transition)  
✅ TGC models created (2: Faroe + Scotland)  
✅ Temperature profiles created (2: geography-specific)  
✅ FCR model created (1 shared with 6 stage values)  
✅ Mortality model created (1 shared)  
✅ No duplication (models reused across batches)  
✅ Stats summary shows scenario and finance fact counts

---

**Ready for testing after demo! 🚀**

---

**End of Enhancement Documentation**





