#!/usr/bin/env python3
"""
Compute Live Forward Projections for all active batch assignments.

This script runs the Live Forward Projection computation that normally runs
as a nightly Celery task. It:
1. Pins scenarios to batches (if not already pinned)
2. Computes forward projections from current ActualDailyAssignmentState
3. Stores results in LiveForwardProjection (TimescaleDB hypertable)
4. Updates ContainerForecastSummary for Executive Dashboard

Usage:
    python scripts/data_generation/run_live_projections.py
    python scripts/data_generation/run_live_projections.py --dry-run
    python scripts/data_generation/run_live_projections.py --limit 50

This is the manual equivalent of the Celery task:
    apps.batch.tasks.compute_all_live_forward_projections
"""
import os
import sys
import argparse
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from django.db.models import Q
from django.utils import timezone
from apps.batch.models import Batch, BatchContainerAssignment, LiveForwardProjection
from apps.batch.services.live_projection_engine import LiveProjectionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def pin_scenarios_to_batches():
    """
    Ensure all active batches have pinned_projection_run set.
    
    The event engine creates scenarios but may not pin them.
    This step ensures the projection engine can find the scenario.
    """
    logger.info("Checking scenario pinning for active batches...")
    
    fixed = 0
    for batch in Batch.objects.filter(status='ACTIVE', pinned_projection_run__isnull=True):
        scenario = batch.scenarios.first()
        if scenario:
            projection_run = scenario.projection_runs.first()
            if projection_run:
                batch.pinned_projection_run = projection_run
                batch.save(update_fields=['pinned_projection_run'])
                fixed += 1
    
    if fixed > 0:
        logger.info(f"Pinned scenarios for {fixed} batches")
    
    # Verify
    total = Batch.objects.filter(status='ACTIVE').count()
    pinned = Batch.objects.filter(status='ACTIVE', pinned_projection_run__isnull=False).count()
    logger.info(f"Active batches with pinned scenarios: {pinned}/{total}")
    
    return fixed


def compute_live_projections(limit=None, dry_run=False):
    """
    Compute Live Forward Projections for all active assignments.
    
    Args:
        limit: Maximum number of assignments to process (None = all)
        dry_run: If True, only count assignments without computing
        
    Returns:
        Dict with statistics
    """
    print("=" * 80)
    print("COMPUTE LIVE FORWARD PROJECTIONS")
    print("=" * 80)
    print()
    
    computed_date = timezone.now().date()
    print(f"Computed date: {computed_date}")
    
    # First, ensure scenarios are pinned
    pin_scenarios_to_batches()
    print()
    
    # Get active assignments for active batches with pinned scenarios
    active_assignments = BatchContainerAssignment.objects.filter(
        is_active=True,
        batch__status='ACTIVE',
    ).filter(
        Q(batch__pinned_projection_run__isnull=False) |
        Q(batch__scenarios__isnull=False)
    ).select_related(
        'batch__pinned_projection_run__scenario__tgc_model__profile',
        'batch__pinned_projection_run__scenario__mortality_model',
        'container'
    ).distinct()
    
    if limit:
        active_assignments = active_assignments[:limit]
    
    total = active_assignments.count()
    print(f"Active assignments to process: {total}")
    print()
    
    if dry_run:
        print("DRY RUN - No projections will be computed")
        return {
            'success': True,
            'dry_run': True,
            'assignments_found': total,
        }
    
    stats = {
        'assignments_processed': 0,
        'assignments_skipped': 0,
        'total_rows_created': 0,
        'errors': [],
    }
    
    for i, assignment in enumerate(active_assignments):
        try:
            engine = LiveProjectionEngine(assignment)
            result = engine.compute_and_store(computed_date=computed_date)
            
            if result.get('success'):
                stats['assignments_processed'] += 1
                stats['total_rows_created'] += result.get('rows_created', 0)
            else:
                stats['assignments_skipped'] += 1
                if result.get('error'):
                    stats['errors'].append({
                        'assignment_id': assignment.id,
                        'error': result['error'],
                    })
                    
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{total}... ({stats['total_rows_created']:,} rows)")
                
        except Exception as e:
            stats['errors'].append({
                'assignment_id': assignment.id,
                'error': str(e),
            })
            logger.error(f"Error processing assignment {assignment.id}: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Assignments processed: {stats['assignments_processed']}")
    print(f"Assignments skipped: {stats['assignments_skipped']}")
    print(f"Total rows created: {stats['total_rows_created']:,}")
    print(f"Errors: {len(stats['errors'])}")
    
    if stats['errors'][:3]:
        print()
        print("Sample errors:")
        for e in stats['errors'][:3]:
            print(f"  Assignment {e['assignment_id']}: {e['error']}")
    
    # Verify
    total_live = LiveForwardProjection.objects.filter(computed_date=computed_date).count()
    print()
    print(f"LiveForwardProjection records for today: {total_live:,}")
    
    print()
    print("✅ LIVE FORWARD PROJECTIONS COMPUTED SUCCESSFULLY")
    
    stats['success'] = True
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Compute Live Forward Projections for active batch assignments'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of assignments to process (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Count assignments without computing projections'
    )
    args = parser.parse_args()
    
    result = compute_live_projections(
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
