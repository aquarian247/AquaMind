"""
Diagnose Data Generation Issues

This script will run a diagnostic check on the data generation process and verify that:
1. We can create a batch successfully
2. We can create container assignments
3. We can create growth samples
4. We can create mortality events

Using more direct database queries and explicit error handling to identify issues.
"""
import os
import sys
import logging
import datetime
import traceback
from decimal import Decimal

# Configure logging to output to console with high visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('diagnostics')

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

# Import Django and setup
try:
    import django
    django.setup()
    logger.info("Django successfully initialized")
except Exception as e:
    logger.error(f"Failed to initialize Django: {e}")
    sys.exit(1)

# Now import Django models after setup
from django.db import connection, transaction
from django.db.models import Count
from django.utils import timezone
from apps.batch.models import (
    Species, LifeCycleStage, Batch, BatchContainerAssignment, 
    GrowthSample, MortalityEvent
)
from apps.infrastructure.models import Container, ContainerType

def print_separator(title=None):
    """Print a separator line with optional title."""
    if title:
        print("\n" + "=" * 30 + f" {title} " + "=" * 30)
    else:
        print("\n" + "=" * 80)

def check_data_counts():
    """Check data counts in key tables."""
    print_separator("DATABASE COUNTS")
    
    tables = [
        ("Batch", Batch),
        ("BatchContainerAssignment", BatchContainerAssignment),
        ("GrowthSample", GrowthSample),
        ("MortalityEvent", MortalityEvent),
        ("Container", Container)
    ]
    
    for name, model in tables:
        try:
            count = model.objects.count()
            print(f"{name}: {count:,} records")
        except Exception as e:
            print(f"Error counting {name}: {e}")

def check_database_schema():
    """Check if all required tables and fields exist."""
    print_separator("DATABASE SCHEMA CHECK")
    
    try:
        # Check BatchContainerAssignment fields
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM information_schema.columns WHERE table_name=%s", ['batch_batchcontainerassignment'])
            columns = [col[3] for col in cursor.fetchall()]  # column_name is at index 3
            print(f"BatchContainerAssignment fields: {', '.join(columns)}")
            
            # Check if critical fields exist
            required_fields = ['id', 'batch_id', 'container_id', 'lifecycle_stage_id', 'population_count', 'biomass_kg', 'assignment_date']
            missing = [field for field in required_fields if field not in columns]
            if missing:
                print(f"MISSING FIELDS: {', '.join(missing)}")
            else:
                print("All required fields present")
                
            # Check if is_active or removal_date exists
            if 'is_active' in columns:
                print("Using is_active field for assignment status")
            elif 'removal_date' in columns:
                print("Using removal_date field for assignment status")
            else:
                print("WARNING: Neither is_active nor removal_date field found")
        
        # Check Growth Sample fields
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM information_schema.columns WHERE table_name=%s", ['batch_growthsample'])
            columns = [col[3] for col in cursor.fetchall()]
            print(f"\nGrowthSample fields: {', '.join(columns)}")
    except Exception as e:
        print(f"Error checking schema: {e}")
        print(traceback.format_exc())

def create_test_samples():
    """Attempt to create test growth samples directly."""
    print_separator("CREATING TEST SAMPLES")
    
    try:
        # Get an existing batch
        batch = Batch.objects.first()
        if not batch:
            print("No batches found. Cannot create samples.")
            return
        
        # Get an existing container
        container = Container.objects.first()
        if not container:
            print("No containers found. Cannot create samples.")
            return
            
        print(f"Working with Batch: {batch.batch_number}, Container: {container.name}")
        
        # Get existing container assignment or create one
        assignment = BatchContainerAssignment.objects.filter(batch=batch).first()
        if not assignment:
            print("No assignment found, creating a test one")
            
            # Create a test assignment
            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=batch.lifecycle_stage,
                population_count=batch.population_count,
                biomass_kg=batch.biomass_kg,
                assignment_date=batch.start_date
            )
            print(f"Created test assignment: {assignment.id}")
        else:
            print(f"Using existing assignment: {assignment.id}")
            
        # Create a test growth sample
        today = timezone.now().date()
        sample = GrowthSample.objects.create(
            batch=batch,
            sample_date=today,
            avg_weight_g=100.0,
            avg_length_cm=20.0,
            sample_size=50,
            sample_method="Manual",
            container=container,
            notes="Diagnostic test sample"
        )
        print(f"Created test growth sample: {sample.id}")
        
        # Create a test mortality event
        mortality = MortalityEvent.objects.create(
            batch=batch,
            assignment=assignment,
            event_date=today,
            count=10,
            biomass_kg=Decimal('1.0'),
            cause="TEST",
            description="Diagnostic test mortality"
        )
        print(f"Created test mortality event: {mortality.id}")
        
        # Verify the sample and mortality were created
        sample_exists = GrowthSample.objects.filter(id=sample.id).exists()
        mortality_exists = MortalityEvent.objects.filter(id=mortality.id).exists()
        
        print(f"Growth sample exists: {sample_exists}")
        print(f"Mortality event exists: {mortality_exists}")
        
        return True
    except Exception as e:
        print(f"Error creating test samples: {e}")
        print(traceback.format_exc())
        return False

def main():
    """Run the diagnostic checks."""
    print_separator("AquaMind Data Generation Diagnostics")
    print(f"Start time: {datetime.datetime.now()}")
    
    try:
        # Check current data counts
        check_data_counts()
        
        # Check database schema
        check_database_schema()
        
        # Try to create test samples
        success = create_test_samples()
        
        # Recheck counts after test
        if success:
            print("\nRechecking counts after test:")
            check_data_counts()
        
        print_separator("DIAGNOSTICS COMPLETE")
        print(f"End time: {datetime.datetime.now()}")
    except Exception as e:
        print(f"Fatal error in diagnostics: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
