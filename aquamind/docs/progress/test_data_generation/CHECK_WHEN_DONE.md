# Post-Generation Verification

**Run these commands when generation completes:**

## 1. Quick Stats
```bash
cd /Users/aquarian247/Projects/AquaMind

DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading

total = Batch.objects.count()
planned = Batch.objects.filter(status='PLANNED').count()
active = Batch.objects.filter(status='ACTIVE').count()
completed = Batch.objects.filter(status='COMPLETED').count()

env = EnvironmentalReading.objects.count()
feed = FeedingEvent.objects.count()

print(f'Batches: {total}/40')
print(f'  PLANNED (stubs): {planned} ❌')
print(f'  ACTIVE (data): {active}')
print(f'  COMPLETED (data): {completed}')
print()
print(f'Environmental: {env:,}')
print(f'Feeding: {feed:,}')
print()

success_rate = (active + completed) / total * 100 if total > 0 else 0
print(f'Success Rate: {success_rate:.0f}%')
print()

if success_rate < 80:
    print('⚠️ HIGH FAILURE RATE - Container conflicts with 6 workers')
    print('Recommendation: Use sequential generation (1 worker)')
elif env < 7_000_000:
    print('⚠️ LOW DATA VOLUME - Some batches failed')
else:
    print('✅ Generation successful!')
"
```

## 2. Comprehensive Verification
```bash
python scripts/data_generation/verify_test_data.py
```

## 3. FK Population Check
```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import MortalityEvent
from apps.environmental.models import EnvironmentalReading

mort_total = MortalityEvent.objects.count()
mort_with_fk = MortalityEvent.objects.filter(assignment__isnull=False).count()

env_total = EnvironmentalReading.objects.count()
env_with_fk = EnvironmentalReading.objects.filter(batch_container_assignment__isnull=False).count()

print('FK Population Check:')
print(f'  MortalityEvent: {mort_with_fk}/{mort_total} = {mort_with_fk/mort_total*100 if mort_total > 0 else 0:.1f}%')
print(f'  EnvironmentalReading: {env_with_fk}/{env_total} = {env_with_fk/env_total*100 if env_total > 0 else 0:.1f}%')
print()
if mort_with_fk == mort_total and env_with_fk == env_total:
    print('✅ All FKs populated correctly')
else:
    print('❌ Some FKs missing')
"
```

## 4. Check Log for Errors
```bash
tail -200 /tmp/batch_gen_40_with_fixes.log | grep -E "Success|Failed|Error"
```

---

