#!/bin/bash
# Check if 550-batch generation is complete

echo "================================================================================"
echo "🎯 BATCH GENERATION COMPLETION CHECK"
echo "================================================================================"
echo ""

# Check if process still running
PROCESS_COUNT=$(ps aux | grep "execute_batch_schedule" | grep -v grep | wc -l)

if [ $PROCESS_COUNT -gt 0 ]; then
    echo "⏳ Status: RUNNING"
    echo "   Active processes: $PROCESS_COUNT"
else
    echo "✅ Status: COMPLETED (no active processes)"
fi

echo ""

# Check database
DJANGO_SETTINGS_MODULE=aquamind.settings python3 << 'EOF'
import django
django.setup()
from apps.batch.models import Batch, BatchContainerAssignment
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading
from apps.batch.models import GrowthSample, MortalityEvent

print("📊 DATABASE STATISTICS")
print("="*80)

batches = Batch.objects.count()
assignments = BatchContainerAssignment.objects.count()
env = EnvironmentalReading.objects.count()
feeding = FeedingEvent.objects.count()
growth = GrowthSample.objects.count()
mortality = MortalityEvent.objects.count()

print(f"\nBatches: {batches}/550 ({batches/550*100:.1f}%)")
print(f"Assignments: {assignments:,}")
print(f"Environmental: {env:,}")
print(f"Feeding: {feeding:,}")
print(f"Growth: {growth:,}")
print(f"Mortality: {mortality:,}")
print(f"\nTotal events: {env + feeding + growth + mortality:,}")

# Check completion
if batches >= 550:
    print("\n✅ GENERATION COMPLETE!")
    print("\nNext steps:")
    print("  1. Run verification: python scripts/data_generation/verify_test_data.py")
    print("  2. Check Growth Analysis: See EXECUTION_STATUS_550_BATCHES.md")
    print("  3. Commit changes: git add -A && git commit")
elif batches >= 500:
    print(f"\n⏳ Nearly done: {550 - batches} batches remaining")
else:
    print(f"\n⏳ In progress: {550 - batches} batches remaining")

# Stage distribution
print("\n📈 Stage Distribution:")
from apps.batch.models import LifeCycleStage
for stage in LifeCycleStage.objects.all().order_by('order'):
    count = Batch.objects.filter(lifecycle_stage=stage).count()
    if count > 0:
        print(f"   {stage.name}: {count} batches")

EOF

echo ""
echo "================================================================================"

