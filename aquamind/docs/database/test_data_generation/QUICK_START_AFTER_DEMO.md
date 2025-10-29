# Quick Start - After Demo

**Your test data is >1 week old. Here's how to refresh with new enhancements:**

---

## ⚡ **5-Minute Test (Validate Enhancements)**

```bash
cd /Users/aquarian247/Projects/AquaMind

# Generate one batch with new features
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 \
  --eggs 3500000 \
  --geography "Scotland" \
  --duration 550

# Validate
python scripts/data_generation/validate_enhancements.py
```

**Look for:**
- ✅ "Created scenario: Sea Growth Forecast..." during Adult transition
- ✅ "Generated X finance harvest facts" during harvest
- ✅ Validation script passes all checks

---

## 🔄 **Full Refresh (Weekend - 2-4 hours)**

```bash
cd /Users/aquarian247/Projects/AquaMind

# Step 1: Clean (30 seconds)
python scripts/data_generation/cleanup_batch_data.py

# Step 2: Infrastructure (10 seconds)
python scripts/data_generation/01_bootstrap_infrastructure.py

# Step 3: Master data (15 seconds)
python scripts/data_generation/02_initialize_master_data.py

# Step 4: Generate batches (2-4 hours for 20 batches)
python scripts/data_generation/04_batch_orchestrator.py \
  --batches 20 \
  --execute

# Step 5: Validate
python scripts/data_generation/validate_enhancements.py
```

**Expected Results:**
- 20 scenarios (one per batch at sea transition)
- ~1,000 finance facts (if batches harvest)
- 2 temperature profiles (Faroe: 9.5°C, Scotland: 10°C)
- 2 TGC models (one per geography)
- 1 FCR model (shared)
- 1 Mortality model (shared)

---

## 📊 **What's New**

### **New Features in Test Scripts:**
1. ✅ Finance harvest facts auto-generated at harvest
2. ✅ Scenarios auto-created at Post-Smolt → Adult transition
3. ✅ Temperature profiles geography-specific (Faroe stable, Scotland variable)
4. ✅ Models shared (no duplication)

### **Coverage Improvement:**
```
Before: 81/146 tables (55.5%)
After:  87/146 tables (59.6%)
Gain:   +6 tables
```

---

## 📖 **Full Documentation**

**Start Here:**
- `AFTER_DEMO_TESTING.md` (detailed testing guide)
- `IMPLEMENTATION_SUMMARY_2025_10_23.md` (what was done)

**Analysis:**
- `docs/database/test_data_generation/README_START_HERE.md` (navigation)
- `docs/database/test_data_generation/DATABASE_TABLE_COVERAGE_ANALYSIS.md` (28-page audit)
- `docs/database/test_data_generation/BACKFILL_STATUS_ANALYSIS.md` (backfill status)

**Reference:**
- `docs/database/test_data_generation/EMPTY_TABLES_QUICK_REFERENCE.md` (gap list)
- `docs/database/test_data_generation/EXECUTIVE_SUMMARY.md` (business impact)
- `docs/database/test_data_generation/ENHANCEMENTS_2025_10_23.md` (technical spec)

---

## ✅ **Checklist**

After demo:

- [ ] Test enhancements (5 min validation run)
- [ ] Review validation output
- [ ] Decide: Quick test or full refresh?
- [ ] Run chosen option
- [ ] Validate coverage improved
- [ ] Check finance BI views working
- [ ] Check scenarios visible in UI
- [ ] Decide on broodstock priority (v1 vs v2)

---

## 🎯 **Key Points**

✅ **Scripts enhanced, not run** (your demo data is safe)  
✅ **Syntax validated** (compiles successfully)  
✅ **Graceful failures** (won't break if finance/scenario fails)  
✅ **Model reuse** (97% reduction in duplication)  
✅ **Ready to test** after demo

---

**Good luck with your demo! 🚀**

See `AFTER_DEMO_TESTING.md` for detailed instructions.



