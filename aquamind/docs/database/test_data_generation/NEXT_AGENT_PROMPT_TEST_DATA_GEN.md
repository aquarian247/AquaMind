# Agent Prompt: Test Data Generation - Full Refresh

**Task**: Regenerate comprehensive test data with batch creation workflows  
**Estimated Time**: 30 min setup + 8-12 hours generation (can run overnight)  
**Prerequisites**: Part B implementation complete, all migrations applied  
**Status**: Backend ready, just need to run scripts

---

## 🎯 Goal

Generate comprehensive test data including:
- 20+ ACTIVE batches with full lifecycle (900 days)
- 5-10 batch creation workflows (various statuses)
- Infrastructure saturation (85% container utilization)
- Realistic occupancy for timeline-aware container selection testing

---

## 📋 Step-by-Step Execution

### Step 1: Purge Non-Foundational Data (2 minutes)

**Script**: Already exists - `scripts/data_generation/cleanup_batch_data.py`

```bash
cd /Users/aquarian247/Projects/AquaMind

# Verify script exists
ls -la scripts/data_generation/cleanup_batch_data.py

# Run cleanup (keeps infrastructure, removes batches/events)
python scripts/data_generation/cleanup_batch_data.py

# Confirm: Should see 0 batches, 0 workflows
python manage.py shell -c "
from apps.batch.models import Batch, BatchCreationWorkflow
print(f'Batches: {Batch.objects.count()}')
print(f'Creation Workflows: {BatchCreationWorkflow.objects.count()}')
"
```

**What It Keeps**:
- ✅ Infrastructure (2,010 containers, sensors)
- ✅ Master data (species, lifecycle stages, feed types)
- ✅ Users and permissions

**What It Removes**:
- ❌ All batches
- ❌ All workflows (transfer + creation)
- ❌ All events (feeding, environmental, mortality, growth)
- ❌ All assignments and history

---

### Step 2: Bootstrap Foundation (3 minutes)

**Only if cleanup removed too much**:

```bash
# Check if infrastructure exists
python manage.py shell -c "
from apps.infrastructure.models import Container
print(f'Containers: {Container.objects.count()}')
"

# If 0, run bootstrap
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py
```

**Expected**: 2,010 containers, 11,060 sensors, species/stages/feed types

---

### Step 3: Generate Batch Creation Workflows (30 seconds)

**Script**: NEW - Created in Part B implementation

```bash
python scripts/data_generation/05_quick_create_test_creation_workflows.py
```

**Output**:
- 5 workflows (DRAFT, PLANNED, IN_PROGRESS, COMPLETED, CANCELLED)
- 24 creation actions
- 1 external egg supplier (AquaGen Norway)

**Verify**:
```bash
python manage.py shell -c "
from apps.batch.models import BatchCreationWorkflow, CreationAction
print(f'Workflows: {BatchCreationWorkflow.objects.count()}')
print(f'Actions: {CreationAction.objects.count()}')
"
```

---

### Step 4: Generate Active Batches (8-12 hours - Run Overnight)

**Script**: Existing batch orchestrator

```bash
# Recommended: 20 batches for good testing (8-10 hours)
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --batches 20

# Alternative: 10 batches for quick testing (4-5 hours)
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --batches 10
```

**What It Creates**:
- 20 ACTIVE batches with full 900-day lifecycle
- ~1M environmental readings
- ~200K feeding events
- ~20K growth samples
- ~2K mortality events
- Harvest events for completed batches
- Finance facts for harvest
- Scenarios for sea transitions

**Progress Monitoring**:
```bash
# Watch progress in another terminal
tail -f logs/batch_generation.log  # If script logs to file

# Or monitor database
watch -n 30 'python manage.py shell -c "
from apps.batch.models import Batch
print(f\"Batches: {Batch.objects.count()}\")
"'
```

---

### Step 5: Verify Results (2 minutes)

```bash
python manage.py shell -c "
from apps.batch.models import Batch, BatchCreationWorkflow, BatchContainerAssignment
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading

print('='*60)
print('TEST DATA GENERATION SUMMARY')
print('='*60)
print(f'Batches (ACTIVE): {Batch.objects.filter(status=\"ACTIVE\").count()}')
print(f'Batches (PLANNED/RECEIVING): {Batch.objects.filter(status__in=[\"PLANNED\", \"RECEIVING\"]).count()}')
print(f'Creation Workflows: {BatchCreationWorkflow.objects.count()}')
print(f'Active Assignments: {BatchContainerAssignment.objects.filter(is_active=True).count()}')
print(f'Feeding Events: {FeedingEvent.objects.count():,}')
print(f'Environmental Readings: {EnvironmentalReading.objects.count():,}')
print('='*60)
"
```

**Expected Results**:
```
Batches (ACTIVE): 20
Batches (PLANNED/RECEIVING): 3-4
Creation Workflows: 5
Active Assignments: 200-250
Feeding Events: 150,000+
Environmental Readings: 800,000+
```

---

## 🧪 Test the Features

### Container Availability (Timeline-Aware)

```bash
# Should show mix of EMPTY, AVAILABLE, CONFLICT containers
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['access'])")

curl -s "http://localhost:8000/api/v1/batch/containers/availability/?geography=1&delivery_date=2026-02-01" \
  -H "Authorization: Bearer $TOKEN" | \
  python -m json.tool | head -100
```

**Look For**:
- Some containers with `current_status: "OCCUPIED"`
- Mix of `availability_status`: EMPTY, AVAILABLE, CONFLICT
- `expected_departure_date` calculated from typical_duration_days

### Frontend UI

```bash
# Start servers if not running
cd /Users/aquarian247/Projects/AquaMind && python manage.py runserver &
cd /Users/aquarian247/Projects/AquaMind-Frontend && npm run dev &

# Navigate to:
http://localhost:5001/batch-creation-workflows

# Should see 5 workflows with different statuses
```

---

## ⚠️ Important Notes

### Script Performance

| Batches | Sequential Time | Parallel Time (14 workers) |
|---------|----------------|---------------------------|
| 10      | ~4-5 hours     | ~30-40 minutes            |
| 20      | ~8-10 hours    | ~60-75 minutes            |
| 50      | ~20-25 hours   | ~2-3 hours                |

**Recommendation**: Run overnight with 20 batches (sequential is safer)

### Disk Space

- 10 batches: ~15-20 GB
- 20 batches: ~30-40 GB  
- 50 batches: ~80-100 GB

Check available space: `df -h`

### Database Performance

```bash
# If script slows down, run during generation:
python manage.py dbshell -c "VACUUM ANALYZE;"

# Check active connections:
python manage.py dbshell -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"
```

---

## 🔧 Troubleshooting

### Script Fails Mid-Run

**Resume from last successful batch**:
```bash
# Find last created batch
python manage.py shell -c "
from apps.batch.models import Batch
last = Batch.objects.latest('created_at')
print(f'Last: {last.batch_number} at {last.created_at}')
"

# Continue with remaining count
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --batches 10  # Adjust based on how many left
```

### Out of Memory

Reduce batch count or run in smaller chunks:
```bash
# Generate 5 at a time
for i in {1..4}; do
  python scripts/data_generation/04_batch_orchestrator.py --execute --batches 5
  sleep 60  # Let DB catch up
done
```

---

## ✅ Success Criteria

- [ ] Cleanup completed (0 batches before generation)
- [ ] 5 creation workflows generated (30 seconds)
- [ ] 20+ active batches generated (8-12 hours)
- [ ] Container utilization ~60-80%
- [ ] No script errors
- [ ] Frontend shows realistic data
- [ ] Container availability shows occupied containers with timelines

---

## 📚 Reference

**Scripts Location**: `/Users/aquarian247/Projects/AquaMind/scripts/data_generation/`

**Key Scripts**:
1. `cleanup_batch_data.py` - Purge non-foundational data
2. `05_quick_create_test_creation_workflows.py` - NEW (Part B)
3. `04_batch_orchestrator.py` - Generate active batches

**Documentation**:
- `aquamind/docs/database/test_data_generation/README_START_HERE.md`
- `aquamind/docs/database/test_data_generation/batch_saturation_guide.md`
- `aquamind/docs/database/test_data_generation/PART_B_TEST_DATA_GAPS.md` - NEW

---

**Estimated Total Time**: 30 min (your work) + 8-12 hours (script runtime)  
**Can Run Unattended**: Yes (run overnight)  
**Risk**: Low (tested scripts, can cleanup and retry)

Ready to generate! 🚀

