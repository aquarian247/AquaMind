"""
Management command for nightly catch-up recomputation of daily states.

This command recomputes actual daily states for recent days across all
active batches. Intended to run as a nightly cron job to catch any events
that might have been missed by real-time signals.

Usage:
    # Recompute last 14 days for all active batches
    python manage.py recompute_recent_daily_states
    
    # Custom window
    python manage.py recompute_recent_daily_states --days 30
    
    # Specific batch only
    python manage.py recompute_recent_daily_states --batch-id 123
    
    # Dry run (show what would be done)
    python manage.py recompute_recent_daily_states --dry-run

Performance:
    - Typical batch: 1-5 seconds
    - Full farm (50 batches): 2-10 minutes
    - Uses Celery tasks for background processing

Issue: #112 - Phase 4 (Event-Driven Recompute)
"""
import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.batch.models import Batch
from apps.batch.tasks import recompute_batch_window

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Nightly catch-up: recompute actual daily states for recent days "
        "across all active batches"
    )
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of recent days to recompute (default: 14)',
        )
        parser.add_argument(
            '--batch-id',
            type=int,
            help='Recompute specific batch only (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without enqueuing tasks',
        )
        parser.add_argument(
            '--status',
            choices=['ACTIVE', 'COMPLETED', 'TERMINATED', 'PLANNING'],
            default='ACTIVE',
            help='Batch status filter (default: ACTIVE)',
        )
    
    def handle(self, *args, **options):
        """Execute command."""
        days = options['days']
        batch_id = options.get('batch_id')
        dry_run = options['dry_run']
        status_filter = options['status']
        
        # Calculate date window
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'[DRY RUN] ' if dry_run else ''}Nightly Catch-Up: "
                f"Recomputing daily states for {start_date} to {end_date}"
            )
        )
        
        # Get batches to process
        if batch_id:
            # Specific batch
            try:
                batches = Batch.objects.filter(id=batch_id)
                self.stdout.write(f"Processing batch ID: {batch_id}")
            except Batch.DoesNotExist:
                raise CommandError(f"Batch {batch_id} not found")
        else:
            # All active batches
            batches = Batch.objects.filter(status=status_filter).order_by('id')
            self.stdout.write(
                f"Processing all {status_filter} batches: {batches.count()} found"
            )
        
        if batches.count() == 0:
            self.stdout.write(self.style.WARNING("No batches to process"))
            return
        
        # Process batches
        tasks_enqueued = []
        errors = []
        
        for batch in batches:
            try:
                # Check if batch has pinned scenario (required)
                if not batch.pinned_scenario and not batch.scenarios.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Skipping {batch.batch_number}: "
                            f"No scenario available"
                        )
                    )
                    continue
                
                # Check if batch has assignments
                assignment_count = batch.batch_assignments.count()
                if assignment_count == 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Skipping {batch.batch_number}: "
                            f"No container assignments"
                        )
                    )
                    continue
                
                # Enqueue task
                if not dry_run:
                    task = recompute_batch_window.delay(
                        batch.id,
                        start_date.isoformat(),
                        end_date.isoformat()
                    )
                    tasks_enqueued.append({
                        'batch': batch.batch_number,
                        'batch_id': batch.id,
                        'task_id': task.id,
                        'assignments': assignment_count,
                    })
                    status_icon = "📋"
                else:
                    tasks_enqueued.append({
                        'batch': batch.batch_number,
                        'batch_id': batch.id,
                        'assignments': assignment_count,
                    })
                    status_icon = "🔍"
                
                self.stdout.write(
                    f"  {status_icon}  {batch.batch_number} "
                    f"({assignment_count} assignments)"
                )
                
            except Exception as e:
                error_msg = f"{batch.batch_number}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(
                    self.style.ERROR(f"  ❌  {error_msg}")
                )
                logger.error(
                    f"Failed to enqueue recompute for batch {batch.id}: {e}",
                    exc_info=True
                )
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {'Would enqueue' if dry_run else 'Enqueued'} "
                f"{len(tasks_enqueued)} task(s)"
            )
        )
        
        if errors:
            self.stdout.write(
                self.style.ERROR(f"❌ {len(errors)} error(s)")
            )
        
        # Show details
        if not dry_run and tasks_enqueued:
            self.stdout.write("\nTask IDs:")
            for task_info in tasks_enqueued:
                self.stdout.write(
                    f"  • {task_info['batch']}: {task_info['task_id']}"
                )
        
        self.stdout.write("\nDate window: " + self.style.NOTICE(
            f"{start_date} to {end_date} ({days} days)"
        ))
        self.stdout.write("=" * 60 + "\n")

