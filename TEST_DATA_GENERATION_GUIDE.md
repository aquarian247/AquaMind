# AquaMind Test Data Generation

**Status:** ✅ **PRODUCTION READY** (verified 2025-11-12)

---

## 🚀 FULL GENERATION COMMAND

```bash
cd /Users/aquarian247/Projects/AquaMind

# Reset & Full Generation (6-12 hours)
python scripts/data_generation/00_complete_reset.py
python scripts/data_generation/04_batch_orchestrator.py --execute --batches 10
```

**Creates:** 20 batches (10 per geography) balanced across all 6 lifecycle stages

---

## ✅ WHAT IT CREATES (Verified Working)

### Complete Audit Trail:
- ✅ **Creation Workflows** - Tracks batch origin, supplier, egg deliveries
- ✅ **Creation Actions** - Documents each egg delivery to containers
- ✅ **Transfer Workflows** - Tracks all stage transitions
- ✅ **Transfer Actions** - Documents container-to-container movements

### Full Operational Data:
- ✅ **200,000+ feeding events** (FIFO consumption, auto-reordering)
- ✅ **1,000,000+ environmental readings** (6/day × 7 sensors)
- ✅ **10,000+ mortality events** (realistic probabilistic rates)
- ✅ **4,000+ growth samples** with 120,000+ individual fish observations
- ✅ **2,000+ lice counts** (weekly monitoring in Adult stage)
- ✅ **1,000+ feed purchases** (auto-reorder when stock < 20%)

### Stage Distribution (Balanced):
```
Egg&Alevin: 4 batches (early lifecycle)
Fry: 3 batches
Parr: 3 batches
Smolt: 3 batches
Post-Smolt: 3 batches
Adult: 4 batches (approaching harvest)
```

---

## 🎯 WHY THIS MATTERS

**Not just test data - simulates 6+ years of farm operations chronologically:**

1. **Regulatory Compliance** - Complete audit trail from egg to harvest
2. **UI Testing** - All tabs populated with realistic data
3. **Migration Preparation** - Scripts prototype legacy data migration
4. **Feature Validation** - Every AquaMind feature tested end-to-end
5. **Training** - Realistic scenarios for user demonstrations

**Audit Trail Example:**
```
Batch FI-2025-002:
  ├─ CRT-2025-002: 3.5M eggs from AquaGen Norway
  │   └─ 10 delivery actions (350K eggs each)
  ├─ TRF-2025-001: Egg&Alevin → Fry transition
  │   └─ 10 transfer actions (container movements)
  └─ TRF-2025-002: Fry → Parr transition
      └─ 10 transfer actions with mortality tracking
```

---

## 📊 INFRASTRUCTURE DISTRIBUTION

**Round-Robin Station Selection:**
- 14 Faroe stations (FI-FW-01 through FI-FW-14)
- 10 Scotland stations (S-FW-01 through S-FW-10)
- Each batch uses different station
- Prevents container contention
- Realistic multi-site operation simulation

---

## ⚠️ NOTES

**FCR Summary Warnings:**
```
⚠️ Batch FCR summary not created (insufficient data)
```
- **Expected behavior** - Django signals calculating 30-day FCR summaries
- Warnings appear in early stages (not enough feeding history yet)
- **Not an error** - summaries auto-calculate when data available
- **Ignore these warnings** during generation

---

## 🔧 MONITORING

```bash
# Check progress (run in another terminal)
watch -n 60 'python manage.py shell -c "
from apps.batch.models import Batch
print(f\"Batches: {Batch.objects.count()}/20\")
"'

# Check log file
tail -f /tmp/full_batch_generation.log
```

---

**Detailed Technical Guide:** `aquamind/docs/database/test_data_generation/test_data_generation_guide_v2.md`

**Ready for full 20-batch generation!** 🚀
