#!/usr/bin/env python
"""
Generate FCR summaries for all active batches.
Based on the script from 2025-10-22 debugging session.
"""
import os
import sys
import django
from datetime import date, timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.services.fcr_service import FCRCalculationService
from apps.batch.models import Batch, BatchContainerAssignment

def generate_fcr_for_all_batches():
    """Generate FCR summaries for all active batches."""
    
    # Get all active batches
    active_batches = Batch.objects.filter(status='ACTIVE')
    total_batches = active_batches.count()
    
    print(f"\n{'='*80}")
    print(f"🐟 Generating FCR Summaries for {total_batches} Active Batches")
    print(f"{'='*80}\n")
    
    # Date range: last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f"📅 Period: {start_date} to {end_date}\n")
    
    batch_success = 0
    batch_no_assignments = 0
    batch_errors = 0
    container_summaries_created = 0
    
    for idx, batch in enumerate(active_batches, 1):
        batch_number = batch.batch_number
        print(f"[{idx}/{total_batches}] Processing {batch_number}...", end=" ")
        
        # Get active assignments for this batch
        assignments = BatchContainerAssignment.objects.filter(
            batch=batch, 
            is_active=True
        )
        
        if assignments.count() == 0:
            print(f"⚠️  No active containers")
            batch_no_assignments += 1
            continue
        
        try:
            container_success = 0
            
            # Create container-level summaries
            for assignment in assignments:
                try:
                    summary = FCRCalculationService.create_container_feeding_summary(
                        assignment, start_date, end_date
                    )
                    if summary:
                        container_success += 1
                except Exception as e:
                    print(f"\n  ❌ Error for container {assignment.container.name}: {e}")
            
            if container_success > 0:
                # Aggregate to batch level
                batch_summary = FCRCalculationService.aggregate_container_fcr_to_batch(
                    batch, start_date, end_date
                )
                
                if batch_summary:
                    container_summaries_created += container_success
                    batch_success += 1
                    fcr = float(batch_summary.weighted_avg_fcr) if batch_summary.weighted_avg_fcr else 0
                    print(f"✅ FCR: {fcr:.2f} ({container_success} containers)")
                else:
                    print(f"⚠️  Batch summary creation failed")
                    batch_errors += 1
            else:
                print(f"⚠️  No container summaries created")
                batch_errors += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            batch_errors += 1
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 Summary")
    print(f"{'='*80}")
    print(f"✅ Successful batches:       {batch_success}")
    print(f"⚠️  No active containers:     {batch_no_assignments}")
    print(f"❌ Errors:                   {batch_errors}")
    print(f"📦 Container summaries:      {container_summaries_created}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    generate_fcr_for_all_batches()

