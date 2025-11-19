#!/bin/bash
# Monitor batch generation progress

echo "================================================================================"
echo "BATCH GENERATION MONITOR"
echo "================================================================================"
echo ""

# Check process status
PROCESSES=$(ps aux | grep -E "execute_batch_schedule|03_event_engine" | grep -v grep | wc -l)
echo "Active processes: $PROCESSES"
echo ""

# Check log file
if [ -f /tmp/batch_550_execution.log ]; then
    echo "Latest log entries:"
    tail -30 /tmp/batch_550_execution.log | grep -E "^\[|Success:|Failed:|Error"
    echo ""
    
    # Count successes and failures
    SUCCESS=$(grep -c "✅" /tmp/batch_550_execution.log || echo "0")
    FAILED=$(grep -c "❌" /tmp/batch_550_execution.log || echo "0")
    
    echo "Progress:"
    echo "  Success: $SUCCESS"
    echo "  Failed: $FAILED"
    echo "  Total: $((SUCCESS + FAILED))/550"
fi

# Check database
echo ""
echo "Database status:"
DJANGO_SETTINGS_MODULE=aquamind.settings python3 << 'PYEOF'
import django
django.setup()
from apps.batch.models import Batch

total = Batch.objects.count()
print(f"  Batches created: {total}")
PYEOF

echo ""
echo "================================================================================"

