#!/usr/bin/env python
"""
Test script to verify data generation fixes.
This script runs a short 20-day data generation test to validate that
growth samples and mortality events are being created properly.
"""
import os
import sys
import datetime
import logging
import argparse
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_generation_test.log')
    ]
)

logger = logging.getLogger('test_data_generation')

# Import modules after Django setup
from django.utils import timezone
from django.db.models import Count
from apps.batch.models import Batch, GrowthSample, MortalityEvent, BatchContainerAssignment
from scripts.data_generation.modules.batch_manager import BatchManager
from scripts.data_generation.modules.growth_manager import GrowthManager
from scripts.data_generation.modules.mortality_manager import MortalityManager

def print_section_header(title):
    """Print a section header for console output"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def cleanup_test_data(start_date, end_date):
    """Remove test data from the specified date range"""
    print_section_header("CLEANING UP TEST DATA")
    
    # Remove growth samples in the date range
    growth_samples = GrowthSample.objects.filter(
        sample_date__gte=start_date,
        sample_date__lte=end_date
    )
    growth_count = growth_samples.count()
    if growth_count > 0:
        print(f"Deleting {growth_count} growth samples from {start_date} to {end_date}")
        growth_samples.delete()
    else:
        print("No growth samples found in the date range to delete")
    
    # Remove mortality events in the date range
    mortality_events = MortalityEvent.objects.filter(
        event_date__gte=start_date,
        event_date__lte=end_date
    )
    mortality_count = mortality_events.count()
    if mortality_count > 0:
        print(f"Deleting {mortality_count} mortality events from {start_date} to {end_date}")
        mortality_events.delete()
    else:
        print("No mortality events found in the date range to delete")
    
    print(f"Cleanup complete. Removed {growth_count} growth samples and {mortality_count} mortality events.")
    return growth_count + mortality_count

def verify_growth_samples():
    """Verify that growth samples are being created properly"""
    print_section_header("GROWTH SAMPLES")
    
    # Check if any growth samples exist
    total_samples = GrowthSample.objects.count()
    print(f"Total growth samples in database: {total_samples}")
    
    # Get distribution by batch
    batch_samples = GrowthSample.objects.values('batch__batch_number').annotate(
        count=Count('id')
    ).order_by('-count')
    
    print("\nGrowth samples by batch:")
    for item in batch_samples:
        print(f"  Batch {item['batch__batch_number']}: {item['count']} samples")
    
    # Check fields
    if total_samples > 0:
        sample = GrowthSample.objects.first()
        print("\nSample growth sample fields:")
        print(f"  Batch: {sample.batch.batch_number}")
        print(f"  Date: {sample.sample_date}")
        print(f"  Sample size: {sample.sample_size}")
        print(f"  Avg weight: {sample.avg_weight_g}g")
        print(f"  Avg length: {sample.avg_length_cm}cm")
        print(f"  Condition factor: {sample.condition_factor}")
    
    return total_samples

def verify_mortality_events():
    """Verify that mortality events are being created properly"""
    print_section_header("MORTALITY EVENTS")
    
    # Check if any mortality events exist
    total_events = MortalityEvent.objects.count()
    print(f"Total mortality events in database: {total_events}")
    
    # Get distribution by batch
    batch_events = MortalityEvent.objects.values('batch__batch_number').annotate(
        count=Count('id')
    ).order_by('-count')
    
    print("\nMortality events by batch:")
    for item in batch_events:
        print(f"  Batch {item['batch__batch_number']}: {item['count']} events")
    
    # Check distribution by cause
    cause_events = MortalityEvent.objects.values('cause').annotate(
        count=Count('id')
    ).order_by('-count')
    
    print("\nMortality events by cause:")
    for item in cause_events:
        print(f"  {item['cause']}: {item['count']} events")
    
    # Check fields
    if total_events > 0:
        event = MortalityEvent.objects.first()
        print("\nSample mortality event fields:")
        print(f"  Batch: {event.batch.batch_number}")
        print(f"  Date: {event.event_date}")
        print(f"  Count: {event.count}")
        print(f"  Biomass: {event.biomass_kg}kg")
        print(f"  Cause: {event.cause}")
        print(f"  Description: {event.description}")
    
    return total_events

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test data generation for AquaMind.')
    parser.add_argument('--cleanup', action='store_true', help='Clean up existing test data before generating new data')
    parser.add_argument('--days', type=int, default=20, help='Number of days to generate data for (default: 20)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing data, do not generate new data')
    return parser.parse_args()

def main():
    """Run a short test of data generation"""
    args = parse_args()
    print_section_header("DATA GENERATION TEST")
    
    # Calculate test date range
    today = timezone.now().date()
    start_date = today - datetime.timedelta(days=args.days)
    end_date = today
    
    print(f"Date range: {start_date} to {end_date} ({args.days} days)")
    
    # Clean up existing test data if requested
    if args.cleanup:
        cleanup_test_data(start_date, end_date)
    
    # Verify only mode - just check existing data without generating new data
    if args.verify_only:
        print("\nVerifying existing data only (no new data generation)")
        verify_growth_samples()
        verify_mortality_events()
        return
    
    # Check for existing assignments
    assignments = BatchContainerAssignment.objects.filter(is_active=True)
    assignment_count = assignments.count()
    
    if assignment_count == 0:
        print("WARNING: No active batch container assignments found.")
        print("You need to run batch initialization first!")
        return
    
    print(f"Found {assignment_count} active batch container assignments")
    
    # Generate growth samples
    print("\nGenerating growth samples...")
    growth_manager = GrowthManager()
    growth_samples = growth_manager.generate_growth_samples(start_date, end_date)
    print(f"Generated {growth_samples} growth samples")
    
    # Generate mortality events
    print("\nGenerating mortality events...")
    mortality_manager = MortalityManager()
    mortality_events = mortality_manager.generate_mortality_events(start_date, end_date)
    print(f"Generated {mortality_events} mortality events")
    
    # Verify results
    verify_growth_samples()
    verify_mortality_events()
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
