#!/bin/bash
# Lice Tracking Test Script
# Runs a single 900-day batch to generate lice data in Adult stage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║          Lice Tracking Test - Single Batch (900 days)           ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Verify lice types are populated
echo "Checking lice types in database..."
cd "$PROJECT_ROOT"
LICE_COUNT=$(python manage.py shell -c "from apps.health.models import LiceType; print(LiceType.objects.count())" 2>/dev/null)

if [ "$LICE_COUNT" -eq "0" ]; then
    echo "⚠️  WARNING: No lice types found in database!"
    echo "   Please run migrations first:"
    echo "   python manage.py migrate health 0021_populate_lice_types"
    exit 1
fi

echo "✓ Found $LICE_COUNT lice types"
echo ""

# Run test batch
echo "Running test batch (this will take ~5-7 minutes)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python "$SCRIPT_DIR/03_event_engine_core.py" \
    --start-date 2024-01-01 \
    --eggs 350000 \
    --geography "Faroe Islands" \
    --duration 900

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Verifying lice data..."
echo ""

# Verification queries
python manage.py shell << 'EOF'
from apps.health.models import LiceCount, LiceType
from apps.batch.models import Batch
from django.db.models import Sum, Avg, Count

print("═" * 70)
print("LICE DATA VERIFICATION")
print("═" * 70)
print()

# Get test batch
batch = Batch.objects.latest('id')
print(f"Batch: {batch.batch_number}")
print(f"Current Stage: {batch.lifecycle_stage.name}")
print()

# Total lice records
total_records = LiceCount.objects.filter(batch=batch).count()
print(f"Total Lice Records: {total_records:,}")

# Check format
normalized = LiceCount.objects.filter(batch=batch, lice_type__isnull=False).count()
print(f"Normalized Format: {normalized}/{total_records} ({normalized/total_records*100:.0f}%)" if total_records > 0 else "Normalized Format: N/A")
print()

# Species distribution
print("Species Distribution:")
for species in ['Lepeophtheirus salmonis', 'Caligus elongatus', 'Unknown']:
    count = LiceCount.objects.filter(
        batch=batch,
        lice_type__species=species
    ).aggregate(total=Sum('count_value'))['total'] or 0
    
    records = LiceCount.objects.filter(
        batch=batch,
        lice_type__species=species
    ).count()
    
    if records > 0:
        print(f"  {species}: {count:,} lice ({records} records)")

print()

# Development stage distribution
print("Development Stage Distribution:")
stages = LiceCount.objects.filter(
    batch=batch
).values(
    'lice_type__development_stage'
).annotate(
    total_count=Sum('count_value'),
    record_count=Count('id')
).order_by('-total_count')

for stage in stages:
    stage_name = stage['lice_type__development_stage']
    total = stage['total_count']
    records = stage['record_count']
    print(f"  {stage_name}: {total:,} lice ({records} records)")

print()

# Average lice per fish over time
avg_per_fish = LiceCount.objects.filter(
    batch=batch
).aggregate(
    avg_lice_per_fish=Avg('count_value')
)['avg_lice_per_fish']

if avg_per_fish:
    print(f"Average Lice per Sampling: {avg_per_fish:.2f}")
    
    # Alert level
    if avg_per_fish < 0.5:
        alert = "GOOD (Green)"
    elif avg_per_fish < 1.0:
        alert = "WARNING (Yellow)"
    else:
        alert = "CRITICAL (Red)"
    
    print(f"Overall Alert Level: {alert}")

print()
print("═" * 70)
EOF

echo ""
echo "✓ Lice tracking test complete!"
echo ""
echo "Next steps:"
echo "  1. Review the lice data above"
echo "  2. Test API endpoints:"
echo "     - GET /api/v1/health/lice-counts/summary/?geography=1"
echo "     - GET /api/v1/health/lice-counts/trends/?interval=weekly"
echo "  3. If satisfied, run parallel orchestrator with more batches"
echo ""
