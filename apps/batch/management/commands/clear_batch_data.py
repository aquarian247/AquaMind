"""
Management command to clear batch-related data while preserving infrastructure.

This command safely removes all batch-related data including health records, growth samples,
mortality events, and feeding events, while preserving infrastructure data like geographies,
areas, stations, containers, etc.
"""
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

# Health models
from apps.health.models import (
    JournalEntry, HealthSamplingEvent, IndividualFishObservation, FishParameterScore,
    LiceCount, Treatment, HealthLabSample
)

# Batch models
from apps.batch.models import (
    Batch, BatchContainerAssignment, BatchTransfer, GrowthSample, MortalityEvent
)

# Inventory models
from apps.inventory.models import FeedingEvent, BatchFeedingSummary

# Environmental models that might be tied to batches
from apps.environmental.models import EnvironmentalReading


class Command(BaseCommand):
    help = 'Clears all batch-related data while preserving infrastructure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write(self.style.WARNING(
            'WARNING: This command will delete ALL batch-related data including:'
        ))
        self.stdout.write('  • Health records (journal entries, sampling events, lice counts, treatments)')
        self.stdout.write('  • Batch data (growth samples, mortality events, transfers, assignments)')
        self.stdout.write('  • Feed data (feeding events, feed usage)')
        self.stdout.write('  • Any batch-related environmental readings')
        self.stdout.write('\n')
        self.stdout.write(self.style.WARNING(
            'WARNING: Infrastructure data will be preserved (geographies, areas, stations, containers, etc.)'
        ))
        self.stdout.write('\n')
        
        # Count records to be deleted
        counts = self._get_record_counts()
        self.stdout.write(self.style.NOTICE('Records to be deleted:'))
        
        # Health data
        self.stdout.write(f'  • {counts["journal_entries"]:,} journal entries')
        self.stdout.write(f'  • {counts["fish_parameter_scores"]:,} fish parameter scores')
        self.stdout.write(f'  • {counts["individual_fish_observations"]:,} individual fish observations')
        self.stdout.write(f'  • {counts["health_sampling_events"]:,} health sampling events')
        self.stdout.write(f'  • {counts["lice_counts"]:,} lice counts')
        self.stdout.write(f'  • {counts["treatments"]:,} treatments')
        self.stdout.write(f'  • {counts["lab_samples"]:,} lab samples')
        
        # Batch data
        self.stdout.write(f'  • {counts["growth_samples"]:,} growth samples')
        self.stdout.write(f'  • {counts["mortality_events"]:,} mortality events')
        self.stdout.write(f'  • {counts["batch_transfers"]:,} batch transfers')
        self.stdout.write(f'  • {counts["batch_assignments"]:,} batch container assignments')
        
        # Feed data
        self.stdout.write(f'  • {counts["feeding_events"]:,} feeding events')
        self.stdout.write(f'  • {counts["batch_feeding_summaries"]:,} batch feeding summaries')
        
        # Environmental data
        self.stdout.write(f'  • {counts["environmental_readings"]:,} batch-related environmental readings')
        
        # Batches
        self.stdout.write(f'  • {counts["batches"]:,} batches')
        
        total_records = sum(counts.values())
        self.stdout.write(f'\nTotal: {total_records:,} records')
        
        if not force:
            self.stdout.write(self.style.WARNING(
                '\nWARNING: Run with --force to proceed with deletion'
            ))
            return
        
        # Proceed with deletion
        self.stdout.write('\nProceeding with deletion...')
        start_time = time.time()
        
        try:
            with transaction.atomic():
                # Delete health data first (respecting foreign key relationships)
                self._delete_records(JournalEntry, 'journal entries')
                self._delete_records(FishParameterScore, 'fish parameter scores')
                self._delete_records(IndividualFishObservation, 'individual fish observations')
                self._delete_records(HealthSamplingEvent, 'health sampling events')
                self._delete_records(LiceCount, 'lice counts')
                self._delete_records(Treatment, 'treatments')
                self._delete_records(HealthLabSample, 'lab samples')
                
                # Delete batch-related data
                self._delete_records(GrowthSample, 'growth samples')
                self._delete_records(MortalityEvent, 'mortality events')
                self._delete_records(FeedingEvent, 'feeding events')
                self._delete_records(BatchFeedingSummary, 'batch feeding summaries')
                
                # Delete batch relationships
                self._delete_records(BatchTransfer, 'batch transfers')
                self._delete_records(BatchContainerAssignment, 'batch container assignments')
                
                # Delete any batch-related environmental readings
                # Note: This assumes EnvironmentalReading has a batch foreign key
                # If not, this can be modified or removed
                try:
                    if hasattr(EnvironmentalReading, 'batch'):
                        self._delete_records(EnvironmentalReading.objects.filter(batch__isnull=False), 
                                            'batch-related environmental readings')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'Skipping environmental readings: {str(e)}'
                    ))
                
                # Finally delete batches
                self._delete_records(Batch, 'batches')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during deletion: {str(e)}'))
            self.stdout.write(self.style.ERROR('No data was deleted due to transaction rollback'))
            return
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSUCCESS: Successfully deleted {total_records:,} records in {duration:.2f} seconds'
        ))
        self.stdout.write(self.style.SUCCESS(
            'SUCCESS: All batch data has been cleared while preserving infrastructure'
        ))
        self.stdout.write('\nYou can now run data generation scripts to create new test data.')
    
    def _get_record_counts(self):
        """Get counts of all records that will be deleted."""
        return {
            # Health data
            "journal_entries": JournalEntry.objects.count(),
            "fish_parameter_scores": FishParameterScore.objects.count(),
            "individual_fish_observations": IndividualFishObservation.objects.count(),
            "health_sampling_events": HealthSamplingEvent.objects.count(),
            "lice_counts": LiceCount.objects.count(),
            "treatments": Treatment.objects.count(),
            "lab_samples": HealthLabSample.objects.count(),
            
            # Batch data
            "growth_samples": GrowthSample.objects.count(),
            "mortality_events": MortalityEvent.objects.count(),
            "batch_transfers": BatchTransfer.objects.count(),
            "batch_assignments": BatchContainerAssignment.objects.count(),
            "batches": Batch.objects.count(),
            
            # Feed data
            "feeding_events": FeedingEvent.objects.count(),
            "batch_feeding_summaries": BatchFeedingSummary.objects.count(),
            
            # Environmental data (if tied to batches)
            "environmental_readings": (
                EnvironmentalReading.objects.filter(batch__isnull=False).count() 
                if hasattr(EnvironmentalReading, 'batch') else 0
            ),
        }
    
    def _delete_records(self, model_or_queryset, description):
        """Delete records with progress reporting."""
        try:
            if hasattr(model_or_queryset, 'objects'):
                # It's a model class
                count = model_or_queryset.objects.count()
                if count > 0:
                    model_or_queryset.objects.all().delete()
                    self.stdout.write(f'  [OK] Deleted {count:,} {description}')
            else:
                # It's a queryset
                count = model_or_queryset.count()
                if count > 0:
                    model_or_queryset.delete()
                    self.stdout.write(f'  [OK] Deleted {count:,} {description}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Error deleting {description}: {str(e)}'))
            raise
