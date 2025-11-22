# Test Data Generation

**Single Source of Truth:** [test_data_generation_guide_v2.md](./test_data_generation_guide_v2.md)

All other documentation has been archived to `aquamind/docs/deprecated/test_data_2025_11_12/`

---

## Quick Commands

**Reset & Test (15 min):**
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/data_generation/00_complete_reset.py
python scripts/data_generation/03_event_engine_core.py --start-date 2025-01-01 --eggs 3500000 --geography "Faroe Islands" --duration 200
```

**Full Generation (6-12 hours):**
```bash
python scripts/data_generation/04_batch_orchestrator.py --execute --batches 20
```

---

**Status:** ✅ All systems verified working (2025-11-12)











