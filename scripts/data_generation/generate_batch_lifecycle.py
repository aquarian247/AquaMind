#!/usr/bin/env python
"""
Batch Lifecycle Test Data Generation Script

This script creates comprehensive test data for the AquaMind system, including infrastructure,
batches with full lifecycle progression, environmental readings, feed data, and growth metrics.

This script is designed to work in different environments (dev, test, prod) and is compatible
with both PostgreSQL/TimescaleDB and SQLite databases.

Usage:
    python -m scripts.data_generation.generate_batch_lifecycle

Configuration:
    Use environment variables or command line arguments to control generation options.
"""
import os
import sys
import random
import logging
import traceback
import datetime
import argparse
from decimal import Decimal
from django.db import connection, transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('batch_lifecycle')

# Initialize Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
import django
django.setup()

# Import modules
from scripts.data_generation.modules.batch_manager import BatchManager
from scripts.data_generation.modules.environmental_manager import EnvironmentalManager
from scripts.data_generation.modules.feed_manager import FeedManager
from scripts.data_generation.modules.growth_manager import GrowthManager
from scripts.data_generation.modules.mortality_manager import MortalityManager
from scripts.data_generation.modules.health_manager import HealthManager

# Import for infrastructure setup
from apps.infrastructure.models import Geography, Area, FreshwaterStation, ContainerType, Hall, Container, FeedContainer
from apps.batch.models import Species, LifeCycleStage, GrowthSample, MortalityEvent
# Health models for statistics
from apps.health.models import (
    JournalEntry, HealthSamplingEvent, LiceCount, Treatment, HealthLabSample
)

def is_timescaledb_available():
    """Check if TimescaleDB is available in the current database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
            return cursor.fetchone() is not None
    except Exception:
        return False


def print_section_header(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"=== {title} {'=' * (75 - len(title))}")
    print(f"{'=' * 80}\n")


def cleanup_generated_data():
    """
    Clean up generated data (growth samples and mortality events) from the database.
    This preserves core infrastructure and batch data created by init_test_data.py.
    """
    print_section_header("Cleaning Up Generated Data")
    
    # Delete all growth samples
    growth_count = GrowthSample.objects.count()
    if growth_count > 0:
        print(f"Deleting {growth_count} growth samples...")
        GrowthSample.objects.all().delete()
        print(f"Done: Deleted {growth_count} growth samples")
    else:
        print("No growth samples to delete")
    
    # Delete all mortality events
    mortality_count = MortalityEvent.objects.count()
    if mortality_count > 0:
        print(f"Deleting {mortality_count} mortality events...")
        MortalityEvent.objects.all().delete()
        print(f"Done: Deleted {mortality_count} mortality events")
    else:
        print("No mortality events to delete")
    
    print(f"\nCleanup complete. Removed {growth_count} growth samples and {mortality_count} mortality events.")
    return growth_count + mortality_count


def verify_infrastructure():
    """Verify that the necessary infrastructure exists in the database."""
    print_section_header("Verifying Infrastructure")

    # Check if basic infrastructure exists
    geographies = Geography.objects.count()
    areas = Area.objects.count()
    stations = FreshwaterStation.objects.count()
    container_types = ContainerType.objects.count()
    containers = Container.objects.count()
    feed_containers = FeedContainer.objects.count()

    # Check if species and lifecycle stages exist
    species = Species.objects.filter(name="Atlantic Salmon").exists()
    lifecycle_stages = LifeCycleStage.objects.count()

    infrastructure_ok = (
        geographies > 0 and
        areas > 0 and
        stations > 0 and
        container_types > 0 and
        containers > 0 and
        feed_containers > 0 and
        species and
        lifecycle_stages >= 6
    )

    print(f"Geographies: {geographies}")
    print(f"Areas: {areas}")
    print(f"Freshwater Stations: {stations}")
    print(f"Container Types: {container_types}")
    print(f"Containers: {containers}")
    print(f"Feed Containers: {feed_containers}")
    # Avoid Unicode symbols that may cause encoding issues on some terminals (e.g., Windows cmd)
    print(f"Atlantic Salmon species: {'Yes' if species else 'No'}")
    print(f"Lifecycle Stages: {lifecycle_stages}")

    return infrastructure_ok


def generate_test_data(start_date=None, days_to_generate=900):
    """
    Generate comprehensive test data for the AquaMind system.
    
    Args:
        start_date: The start date for data generation (defaults to 900 days ago)
        days_to_generate: Number of days of data to generate (default: 900)
        
    Returns:
        Dictionary of generation statistics
    """
    print_section_header("Generating Test Data")
    
    # Initialize managers
    batch_manager = BatchManager()
    environmental_manager = EnvironmentalManager()
    feed_manager = FeedManager()
    growth_manager = GrowthManager()
    mortality_manager = MortalityManager()
    health_manager = HealthManager()
    
    # Set start and end dates
    if start_date is None:
        start_date = timezone.now().date() - datetime.timedelta(days=days_to_generate)
    
    end_date = min(start_date + datetime.timedelta(days=days_to_generate), timezone.now().date())
    
    print(f"Data generation period: {start_date} to {end_date} ({(end_date - start_date).days} days)")
    
    # Create a batch
    batch = batch_manager.create_batch(start_date=start_date)
    
    # Process lifecycle stages
    print_section_header(f"Processing Lifecycle for Batch {batch.batch_number}")
    batch_manager.process_lifecycle(batch, end_date)
    
    # Generate environmental readings (8 per day)
    print_section_header("Generating Environmental Readings")
    environmental_readings = environmental_manager.generate_readings(
        start_date, 
        end_date, 
        # Reduce density to speed up generation & avoid duplicate‐key conflicts
        reading_count=2
    )
    
    # Generate growth samples (weekly)
    print_section_header("Generating Growth Samples")
    try:
        growth_samples = growth_manager.generate_growth_samples(
            start_date, 
            end_date, 
            sample_interval_days=7
        )
        logger.info(f"Generated {growth_samples} growth samples")
    except Exception as e:
        logger.error(f"Error generating growth samples: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"ERROR generating growth samples: {str(e)}")
        growth_samples = 0
    
    # Generate feeding events (4 per day)
    print_section_header("Generating Feeding Events")
    try:
        feeding_events = feed_manager.generate_feeding_events(
            start_date, 
            end_date, 
            feedings_per_day=4
        )
        logger.info(f"Generated {feeding_events} feeding events")
    except Exception as e:
        logger.error(f"Error generating feeding events: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"ERROR generating feeding events: {str(e)}")
        feeding_events = 0
    
    # Generate mortality events (daily)
    print_section_header("Generating Mortality Events")
    try:
        mortality_events = mortality_manager.generate_mortality_events(
            start_date, 
            end_date
        )
        logger.info(f"Generated {mortality_events} mortality events")
    except Exception as e:
        logger.error(f"Error generating mortality events: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"ERROR generating mortality events: {str(e)}")
        mortality_events = 0
    
    # ------------------------------------------------------------------
    # Generate health monitoring data (journal entries, samples, lice, etc.)
    # ------------------------------------------------------------------
    print_section_header("Generating Health Data")
    try:
        health_manager.generate_health_data(
            batch=batch,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error generating health data: {str(e)}")
        logger.error(traceback.format_exc())

    # ------------------------------------------------------------------
    # Collect health-related statistics
    # ------------------------------------------------------------------
    journal_entries = JournalEntry.objects.filter(
        batch=batch,
        entry_date__date__gte=start_date,
        entry_date__date__lte=end_date
    ).count()
    sampling_events = HealthSamplingEvent.objects.filter(
        batch=batch,
        sample_date__date__gte=start_date,
        sample_date__date__lte=end_date
    ).count()
    lice_counts = LiceCount.objects.filter(
        batch=batch,
        count_date__date__gte=start_date,
        count_date__date__lte=end_date
    ).count()
    treatments = Treatment.objects.filter(
        batch=batch,
        treatment_date__date__gte=start_date,
        treatment_date__date__lte=end_date
    ).count()
    lab_samples = HealthLabSample.objects.filter(
        batch=batch,
        sample_date__date__gte=start_date,
        sample_date__date__lte=end_date
    ).count()

    # Compile statistics
    stats = {
        'batch': 1,
        'environmental_readings': environmental_readings,
        'growth_samples': growth_samples,
        'feeding_events': feeding_events,
        'mortality_events': mortality_events,
        'journal_entries': journal_entries,
        'health_sampling_events': sampling_events,
        'lice_counts': lice_counts,
        'treatments': treatments,
        'lab_samples': lab_samples,
        'start_date': start_date,
        'end_date': end_date,
        'duration_days': (end_date - start_date).days
    }
    
    print_section_header("Test Data Generation Summary")
    print(f"Generated {stats['batch']} batch with complete lifecycle data:")
    print(f"- {stats['environmental_readings']:,} environmental readings")
    print(f"- {stats['growth_samples']:,} growth samples")
    print(f"- {stats['feeding_events']:,} feeding events")
    print(f"- {stats['mortality_events']:,} mortality events")
    print(f"- {stats['journal_entries']:,} health journal entries")
    print(f"- {stats['health_sampling_events']:,} health sampling events")
    print(f"- {stats['lice_counts']:,} lice counts")
    print(f"- {stats['treatments']:,} treatments")
    print(f"- {stats['lab_samples']:,} lab samples")
    print(f"Total duration: {stats['duration_days']} days ({stats['start_date']} to {stats['end_date']})")
    
    return stats


def main():
    """Main function to orchestrate test data generation."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate test data for AquaMind')
    parser.add_argument('--days', type=int, default=900, help='Number of days to generate data for')
    parser.add_argument('--start-date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--no-verify', action='store_true', help='Skip infrastructure verification')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip cleaning up existing generated data')
    args = parser.parse_args()
    
    # Check database compatibility
    has_timescaledb = is_timescaledb_available()
    print(f"TimescaleDB available: {'Yes' if has_timescaledb else 'No - falling back to standard PostgreSQL/SQLite'}")
    
    # Verify infrastructure
    if not args.no_verify:
        if not verify_infrastructure():
            print("ERROR: Required infrastructure is missing from the database.")
            print("Please run the infrastructure initialization script first:")
            print("  python -m scripts.init_test_data")
            return
    
    # Clean up existing generated data
    if not args.no_cleanup:
        cleanup_generated_data()
    
    # Parse start date if provided
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"ERROR: Invalid start date format. Please use YYYY-MM-DD.")
            return
    
    # Generate test data
    stats = generate_test_data(start_date, args.days)
    return True


if __name__ == "__main__":
    main()
