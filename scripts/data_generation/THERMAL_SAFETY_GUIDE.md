# Thermal Safety Guide for Batch Generation

**M4 Max Thermal Management During Long-Running Data Generation**

---

## 🌡️ Quick Status Check

```bash
# Check CPU usage
python3 -c "import psutil; print(f'CPU: {psutil.cpu_percent(interval=1)}%')"

# Check active workers
ps aux | grep "03_event_engine" | grep -v grep | wc -l

# Monitor in real-time
watch -n 10 'ps aux | grep python | grep event_engine | wc -l'
```

---

## 🚨 Thermal Safety Levels

### ✅ SAFE (CPU < 70%)
- **Status:** Sustainable indefinitely
- **Action:** Continue as-is
- **Workers:** 14 workers OK

### ⚠️ MODERATE (CPU 70-85%)
- **Status:** Sustainable for 1-2 hours
- **Action:** Monitor every 15 minutes
- **Recommendation:** 
  - Ensure laptop is elevated (airflow underneath)
  - Keep in cool room (not in direct sunlight)
  - Consider reducing to 10 workers if running >2 hours

### 🔥 HIGH (CPU > 85%)
- **Status:** Risk of thermal throttling
- **Action:** Reduce load immediately
- **Steps:**
  1. Kill current job: `pkill -f execute_batch_schedule`
  2. Let cool for 5 minutes
  3. Restart with fewer workers (see options below)

---

## 🛠️ Thermal Mitigation Strategies

### Strategy 1: Reduce Worker Count (Immediate)

**Current:** 14 workers → 78% CPU (borderline)

**Option A: 10 Workers (Recommended)**
```bash
# Kill current job
pkill -f execute_batch_schedule

# Wait for cooldown
sleep 60

# Restart with 10 workers
cd /Users/aquarian247/Projects/AquaMind
SKIP_CELERY_SIGNALS=1 nohup python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_550_6day.yaml --workers 10 --use-partitions \
  > /tmp/batch_550_thermal_safe.log 2>&1 &
```
- **CPU:** ~55-65% (safe)
- **Time:** +40% longer (~1.7 hours total)
- **Thermal:** ✅ Safe for extended runs

**Option B: 8 Workers (Conservative)**
```bash
SKIP_CELERY_SIGNALS=1 nohup python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_550_6day.yaml --workers 8 --use-partitions \
  > /tmp/batch_550_thermal_safe.log 2>&1 &
```
- **CPU:** ~45-55% (very safe)
- **Time:** +75% longer (~2.2 hours total)
- **Thermal:** ✅ Safe indefinitely

### Strategy 2: Wave-Based Execution (Cooldown Periods)

**Use throttle_execution.py:**
```bash
# Process in waves of 50 batches with 30s cooldown
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/throttle_execution.py \
  config/batch_schedule_550_6day.yaml \
  --workers 10 \
  --wave-size 50 \
  --cooldown 30
```

**Benefits:**
- Gives CPU thermal breathing room between waves
- Prevents sustained high load
- Slightly longer total time but safer

**Wave Pattern:**
```
Wave 1: 50 batches (10 workers) → 30s cooldown
Wave 2: 50 batches (10 workers) → 30s cooldown
...
Wave 11: 50 batches (10 workers) → Done
```

### Strategy 3: Physical Cooling

**Immediate actions:**
1. **Elevate laptop** - Use laptop stand or books (airflow underneath)
2. **Cool room** - Turn on AC or open windows
3. **Clean vents** - Ensure no dust blocking airflow
4. **External cooling** - Use laptop cooling pad if available

### Strategy 4: Resume from Checkpoint

**If you need to stop and restart:**
```bash
# Check how many batches completed
DJANGO_SETTINGS_MODULE=aquamind.settings python3 -c "
import django; django.setup()
from apps.batch.models import Batch
print(f'Completed: {Batch.objects.count()}/550')
"

# The schedule executor doesn't have resume built-in yet
# But you can manually edit the YAML to remove completed batches
# Or just let it run - duplicate batch numbers will be caught
```

---

## 📊 Current Job Analysis

**Process ID:** 42656  
**Workers:** 14  
**Mode:** Partitioned (zero conflicts)  
**Current CPU:** ~78% (moderate, sustainable for 1-2 hours)

**Options:**

### Option A: Let It Run (Recommended if CPU stays < 80%)
- **Time:** ~1 hour remaining
- **Risk:** Low (78% is manageable)
- **Action:** Monitor every 15 minutes

### Option B: Throttle Now (Conservative)
```bash
# Kill current job
pkill -f execute_batch_schedule

# Check what completed
DJANGO_SETTINGS_MODULE=aquamind.settings python3 -c "
import django; django.setup()
from apps.batch.models import Batch
completed = Batch.objects.count()
print(f'Completed: {completed}/550')
print(f'Remaining: {550 - completed}')
"

# Wipe and restart with 8 workers (thermal-safe)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

SKIP_CELERY_SIGNALS=1 nohup python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_550_6day.yaml --workers 8 --use-partitions \
  > /tmp/batch_550_thermal_safe.log 2>&1 &
```

---

## 🎯 Recommended Action Plan

**For your current situation (78% CPU):**

1. **Monitor for next 15 minutes**
   ```bash
   watch -n 60 'python3 -c "import psutil; print(f\"CPU: {psutil.cpu_percent(interval=1)}%\")"'
   ```

2. **If CPU stays < 80%:** Let it run (1 hour to completion)

3. **If CPU exceeds 85%:** Kill and restart with 10 workers

4. **Physical cooling:**
   - Elevate laptop NOW (improves airflow)
   - Move to cooler location if possible
   - Ensure vents are clear

---

## 💡 For Future Runs

### Thermal-Safe Configuration (Recommended)
```bash
# 10 workers with wave-based execution
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/throttle_execution.py \
  config/batch_schedule_550_6day.yaml \
  --workers 10 \
  --wave-size 50 \
  --cooldown 30
```
- **CPU:** 55-65% (safe)
- **Time:** ~1.5 hours
- **Thermal:** ✅ Safe for extended runs

### Maximum Performance (Current)
```bash
# 14 workers, no throttling
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_550_6day.yaml --workers 14 --use-partitions
```
- **CPU:** 75-85% (borderline)
- **Time:** ~1 hour
- **Thermal:** ⚠️ Monitor closely

### Conservative (Overnight Runs)
```bash
# 6 workers, wave-based
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/throttle_execution.py \
  config/batch_schedule_550_6day.yaml \
  --workers 6 \
  --wave-size 30 \
  --cooldown 60
```
- **CPU:** 35-45% (very safe)
- **Time:** ~2.5 hours
- **Thermal:** ✅ Safe indefinitely

---

## 🔧 Emergency Procedures

### If Laptop Gets Too Hot

**Signs:**
- Fan noise increases significantly
- CPU throttling (performance drops)
- System becomes sluggish
- Temperature warnings

**Immediate Action:**
```bash
# 1. Kill the job
pkill -f execute_batch_schedule

# 2. Check what completed
DJANGO_SETTINGS_MODULE=aquamind.settings python3 -c "
import django; django.setup()
from apps.batch.models import Batch
print(f'Batches saved: {Batch.objects.count()}/550')
"

# 3. Let cool for 5-10 minutes
# 4. Restart with thermal-safe config (8 workers)
```

### Resume After Cooling

Since schedule-based execution is deterministic, you can:
1. **Wipe and restart** (if < 100 batches completed)
2. **Continue from checkpoint** (edit YAML to skip completed batches)
3. **Accept partial dataset** (if > 400 batches completed)

---

## 📈 Performance vs Thermal Trade-offs

| Workers | CPU % | Time | Thermal Risk | Recommended For |
|---------|-------|------|--------------|-----------------|
| 14 | 75-85% | 1.0h | ⚠️ Moderate | Short bursts, monitoring |
| 10 | 55-65% | 1.4h | ✅ Low | Standard runs |
| 8 | 45-55% | 1.8h | ✅ Very Low | Extended runs, hot environments |
| 6 | 35-45% | 2.5h | ✅ Minimal | Overnight, unattended |

---

## 🎯 Current Recommendation

**Your current job (14 workers, 78% CPU):**

✅ **Continue running** - You're in the moderate zone  
⏰ **Monitor every 15 minutes** - Check CPU doesn't exceed 85%  
🌡️ **Elevate laptop** - Improve airflow immediately  
⏱️ **Expected completion:** ~1 hour from start (10:40 AM)

**If CPU exceeds 85% in next check:**
- Kill job
- Cool for 5 minutes  
- Restart with 10 workers

---

**Your call!** The job is progressing well, but thermal safety is important for laptop longevity.

