#!/usr/bin/env python3
"""
Run optimized growth analysis on all existing batches.

This script uses the bulk-optimized growth assimilation engine that:
- Loads all data with single queries per data type (not per-day)
- Processes entirely in memory
- Bulk creates/updates ActualDailyAssignmentState records

Expected performance: ~5-10 seconds per batch (vs 300s+ timeout with original)

Usage:
    python scripts/data_generation/run_growth_analysis_optimized.py
    python scripts/data_generation/run_growth_analysis_optimized.py --workers 8
    python scripts/data_generation/run_growth_analysis_optimized.py --batch FAR-2020-001
"""
import os
import sys
import time
import argparse
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from django.db import connection
from apps.batch.models import Batch


def process_single_batch(batch_info: dict) -> dict:
    """Process a single batch in a subprocess."""
    import os, sys, django
    from datetime import date
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
    django.setup()
    
    from apps.batch.models import Batch
    from apps.batch.services.growth_assimilation_optimized import recompute_batch_assignments_optimized
    
    batch_id = batch_info['batch_id']
    batch_number = batch_info['batch_number']
    
    start_time = time.time()
    
    try:
        batch = Batch.objects.get(id=batch_id)
        
        result = recompute_batch_assignments_optimized(
            batch_id=batch_id,
            start_date=batch.start_date,
            end_date=batch.actual_end_date if batch.status == 'COMPLETED' else None
        )
        
        elapsed = time.time() - start_time
        
        return {
            'batch_number': batch_number,
            'success': True,
            'assignments': result.get('assignments_processed', 0),
            'states_created': result.get('total_rows_created', 0),
            'states_updated': result.get('total_rows_updated', 0),
            'errors': result.get('total_errors', 0),
            'elapsed_seconds': round(elapsed, 1)
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'batch_number': batch_number,
            'success': False,
            'error': str(e),
            'elapsed_seconds': round(elapsed, 1)
        }


def main():
    parser = argparse.ArgumentParser(description='Run optimized growth analysis')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--batch', type=str, help='Process specific batch number only')
    parser.add_argument('--limit', type=int, help='Limit number of batches to process')
    parser.add_argument('--status', type=str, choices=['ACTIVE', 'COMPLETED', 'ALL'], 
                        default='ALL', help='Filter by batch status')
    args = parser.parse_args()
    
    print("=" * 80)
    print("OPTIMIZED GROWTH ANALYSIS")
    print("=" * 80)
    print()
    
    # Get batches to process
    batches = Batch.objects.all()
    
    if args.batch:
        batches = batches.filter(batch_number=args.batch)
    elif args.status != 'ALL':
        batches = batches.filter(status=args.status)
    
    # Only process batches with scenarios
    batches = batches.filter(
        models.Q(pinned_scenario__isnull=False) | 
        models.Q(scenarios__isnull=False)
    ).distinct()
    
    if args.limit:
        batches = batches[:args.limit]
    
    batch_list = list(batches.values('id', 'batch_number', 'status', 'start_date'))
    
    if not batch_list:
        print("No batches found with scenarios. Run scenario initialization first.")
        return
    
    print(f"Batches to process: {len(batch_list)}")
    print(f"Workers: {args.workers}")
    print()
    
    # Prepare batch info for workers
    batch_infos = [
        {'batch_id': b['id'], 'batch_number': b['batch_number']}
        for b in batch_list
    ]
    
    # Process in parallel
    start_time = time.time()
    success_count = 0
    error_count = 0
    total_states = 0
    
    # Close Django DB connections before forking
    connection.close()
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_single_batch, info): info 
            for info in batch_infos
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            
            if result['success']:
                success_count += 1
                states = result['states_created'] + result['states_updated']
                total_states += states
                print(f"[{i}/{len(batch_list)}] ✅ {result['batch_number']}: "
                      f"{result['assignments']} assignments, {states} states "
                      f"({result['elapsed_seconds']}s)")
            else:
                error_count += 1
                print(f"[{i}/{len(batch_list)}] ❌ {result['batch_number']}: "
                      f"{result.get('error', 'Unknown error')} "
                      f"({result['elapsed_seconds']}s)")
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total batches: {len(batch_list)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total states created/updated: {total_states:,}")
    print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"Average per batch: {elapsed/len(batch_list):.1f}s")
    print()
    
    if success_count == len(batch_list):
        print("✅ ALL BATCHES PROCESSED SUCCESSFULLY")
    else:
        print(f"⚠️  {error_count} batches had errors")


if __name__ == '__main__':
    # Need to import models after Django setup for the Q filter
    from django.db import models
    main()











