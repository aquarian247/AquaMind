"""
Management command to backfill batch completion status for existing data.

This command identifies batches that have been fully harvested (all assignments inactive)
but are still marked as ACTIVE, and updates them to COMPLETED with the appropriate
actual_end_date.

Usage:
    python manage.py backfill_batch_completion_status [--dry-run] [--batch-id ID]
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, Q
from django.utils import timezone

from apps.batch.models import Batch


class Command(BaseCommand):
    help = 'Backfill batch completion status for batches that are fully harvested but still ACTIVE'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--batch-id',
            type=int,
            help='Only process a specific batch by ID',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt and proceed automatically',
        )
    
    def handle(self, *args, **options):
        """Execute the backfill command."""
        dry_run = options['dry_run']
        batch_id = options.get('batch_id')
        
        self.stdout.write(self.style.WARNING(
            '\n' + '='*80 + '\n'
            'Batch Completion Status Backfill\n'
            '='*80
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))
        
        # Query for batches that should be marked COMPLETED
        query = Batch.objects.filter(status='ACTIVE')
        
        # If specific batch ID provided, filter to just that batch
        if batch_id:
            query = query.filter(id=batch_id)
            if not query.exists():
                raise CommandError(f'Batch with ID {batch_id} not found or not ACTIVE')
        
        self.stdout.write(f'\nSearching for ACTIVE batches with no active assignments...\n')
        
        batches_to_update = []
        
        for batch in query.select_related('species', 'lifecycle_stage').prefetch_related('batch_assignments'):
            # Check if this batch has any active assignments
            has_active_assignments = batch.batch_assignments.filter(is_active=True).exists()
            
            if not has_active_assignments:
                # Check if batch has ANY assignments at all
                total_assignments = batch.batch_assignments.count()
                
                if total_assignments == 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ Batch {batch.batch_number} (ID: {batch.id}) has no assignments. Skipping.'
                        )
                    )
                    continue
                
                # Get the latest departure date
                latest_departure = batch.batch_assignments.aggregate(
                    Max('departure_date')
                )['departure_date__max']
                
                # Fall back to updated_at if no departure dates
                if not latest_departure:
                    latest_update = batch.batch_assignments.aggregate(
                        Max('updated_at')
                    )['updated_at__max']
                    latest_departure = latest_update.date() if latest_update else timezone.now().date()
                
                batches_to_update.append({
                    'batch': batch,
                    'actual_end_date': latest_departure,
                    'assignment_count': total_assignments,
                })
        
        if not batches_to_update:
            self.stdout.write(self.style.SUCCESS('\n✓ No batches need updating. All are correct!\n'))
            return
        
        # Display summary
        self.stdout.write(
            self.style.WARNING(
                f'\nFound {len(batches_to_update)} batch(es) to mark as COMPLETED:\n'
            )
        )
        
        for item in batches_to_update:
            batch = item['batch']
            self.stdout.write(
                f'  • Batch {batch.batch_number} (ID: {batch.id})\n'
                f'    - Species: {batch.species.name}\n'
                f'    - Stage: {batch.lifecycle_stage.name}\n'
                f'    - Assignments: {item["assignment_count"]} (all inactive)\n'
                f'    - Will set actual_end_date: {item["actual_end_date"]}\n'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nDRY RUN COMPLETE - No changes made. '
                    'Run without --dry-run to apply updates.\n'
                )
            )
            return
        
        # Confirm before proceeding (unless specific batch ID provided or --yes flag)
        if not batch_id and not options.get('yes'):
            confirm = input(f'\nProceed with updating {len(batches_to_update)} batch(es)? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('Aborted by user.\n'))
                return
        
        # Perform the updates
        updated_count = 0
        
        for item in batches_to_update:
            batch = item['batch']
            
            try:
                batch.status = 'COMPLETED'
                batch.actual_end_date = item['actual_end_date']
                batch.save(update_fields=['status', 'actual_end_date'])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated Batch {batch.batch_number} to COMPLETED'
                    )
                )
                updated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to update Batch {batch.batch_number}: {str(e)}'
                    )
                )
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*80}\n'
                f'Backfill Complete!\n'
                f'{"="*80}\n'
                f'  Total batches updated: {updated_count}\n'
                f'  Status: ACTIVE → COMPLETED\n'
                f'  actual_end_date: Set from latest assignment departure\n'
            )
        )

