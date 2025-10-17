#!/usr/bin/env python3
"""
AquaMind Phase 4: Parallel Batch Generation Orchestrator
Saturates infrastructure with staggered batches using multiprocessing
"""
import os
import sys
import django
import subprocess
from datetime import date, timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count
import time

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, Container, Hall
from apps.batch.models import Batch


def run_batch(batch_config):
    """
    Worker function to run a single batch generation
    Returns: (success, batch_number, duration)
    """
    start_time = time.time()
    script_path = Path(__file__).parent / "03_event_engine_core.py"
    
    cmd = [
        'python',
        str(script_path),
        '--start-date', str(batch_config['start_date']),
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(batch_config['duration'])
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        duration = time.time() - start_time
        return (True, f"{batch_config['geography'][:3]}-{batch_config['start_date']}", duration)
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        return (False, f"{batch_config['geography'][:3]}-{batch_config['start_date']}", duration, str(e))


class ParallelBatchOrchestrator:
    """
    Orchestrates generation of multiple batches using parallel processing
    """
    
    def __init__(self, target_saturation=0.85, max_workers=None):
        """
        Args:
            target_saturation: Target percentage of infrastructure to saturate (0.0-1.0)
            max_workers: Max parallel workers (defaults to CPU count - 2)
        """
        self.target_saturation = target_saturation
        self.max_workers = max_workers or max(1, cpu_count() - 2)
        self.stats = {
            'total_containers': 0,
            'available_containers': 0,
            'target_batches': 0,
            'batches_generated': 0,
            'batches_failed': 0,
            'total_time': 0
        }
        
    def analyze_infrastructure(self):
        """Analyze available infrastructure capacity"""
        print("\n" + "="*80)
        print("INFRASTRUCTURE CAPACITY ANALYSIS")
        print("="*80 + "\n")
        
        for geo in Geography.objects.all():
            fw_containers = Container.objects.filter(
                hall__freshwater_station__geography=geo,
                active=True
            ).count()
            
            sea_containers = Container.objects.filter(
                area__geography=geo,
                active=True
            ).count()
            
            total = fw_containers + sea_containers
            self.stats['total_containers'] += total
            
            print(f"{geo.name}:")
            print(f"  Freshwater Containers: {fw_containers}")
            print(f"  Sea Containers: {sea_containers}")
            print(f"  Total: {total}")
            print()
        
        print(f"TOTAL INFRASTRUCTURE: {self.stats['total_containers']} containers")
        print(f"Target Saturation: {self.target_saturation*100:.0f}%")
        print(f"Parallel Workers: {self.max_workers} (of {cpu_count()} cores)")
        print()
        
    def calculate_batch_plan(self):
        """Calculate optimal batch distribution"""
        print("\n" + "="*80)
        print("BATCH GENERATION PLAN")
        print("="*80 + "\n")
        
        containers_per_batch = 10
        target_batches = int(
            (self.stats['total_containers'] / containers_per_batch) * 
            self.target_saturation
        )
        
        self.stats['target_batches'] = target_batches
        
        print(f"Infrastructure Capacity:")
        print(f"  Total Containers: {self.stats['total_containers']}")
        print(f"  Containers per Batch: {containers_per_batch}")
        print(f"  Target Saturation: {self.target_saturation*100:.0f}%")
        print()
        print(f"Batch Plan:")
        print(f"  Target Batches: {target_batches}")
        print(f"  Lifecycle Duration: 900 days (~30 months)")
        print(f"  Stagger Interval: 30 days")
        print(f"  **PARALLEL PROCESSING: {self.max_workers} batches at once**")
        print()
        
        batches_per_geo = target_batches // 2
        print(f"Distribution:")
        print(f"  Faroe Islands: {batches_per_geo} batches")
        print(f"  Scotland: {batches_per_geo} batches")
        print()
        
        return batches_per_geo
    
    def generate_batch_schedule(self, batches_per_geo, start_date=None):
        """Generate staggered batch start dates"""
        if start_date is None:
            start_date = date.today() - timedelta(days=900)
        
        print("\n" + "="*80)
        print("GENERATING BATCH SCHEDULE")
        print("="*80 + "\n")
        
        schedule = []
        
        for geo_name in ["Faroe Islands", "Scotland"]:
            print(f"\n{geo_name}:")
            print("-" * 40)
            
            for i in range(batches_per_geo):
                batch_start = start_date + timedelta(days=i * 30)
                
                import random
                eggs = random.randint(3200000, 3800000)
                
                schedule.append({
                    'start_date': batch_start,
                    'eggs': eggs,
                    'geography': geo_name,
                    'duration': 900
                })
                
                if i < 5:
                    print(f"  Batch {i+1:3d}: {batch_start} | {eggs:,} eggs")
            
            if batches_per_geo > 5:
                print(f"  ... ({batches_per_geo - 5} more)")
        
        print(f"\nTotal Batches Scheduled: {len(schedule)}")
        print(f"Date Range: {schedule[0]['start_date']} to {schedule[-1]['start_date']}")
        print()
        
        return schedule
    
    def execute_batch_generation_parallel(self, schedule):
        """
        Execute batch generation in parallel using multiprocessing
        """
        print("\n" + "="*80)
        print(f"EXECUTING PARALLEL BATCH GENERATION ({self.max_workers} workers)")
        print("="*80 + "\n")
        
        start_time = time.time()
        
        # Create process pool
        with Pool(processes=self.max_workers) as pool:
            # Map batches to workers
            results = pool.map(run_batch, schedule)
        
        # Process results
        for i, result in enumerate(results, 1):
            if result[0]:  # Success
                success, batch_id, duration = result
                self.stats['batches_generated'] += 1
                print(f"✓ Batch {i}/{len(schedule)}: {batch_id} ({duration:.1f}s)")
            else:  # Failure
                success, batch_id, duration, error = result
                self.stats['batches_failed'] += 1
                print(f"✗ Batch {i}/{len(schedule)}: {batch_id} FAILED ({duration:.1f}s)")
                print(f"  Error: {error}")
        
        self.stats['total_time'] = time.time() - start_time
        
        print("\n" + "="*80)
        print("PARALLEL BATCH GENERATION COMPLETE")
        print("="*80)
        print(f"\nBatches Generated: {self.stats['batches_generated']}/{len(schedule)}")
        print(f"Batches Failed: {self.stats['batches_failed']}")
        print(f"Total Time: {self.stats['total_time']/60:.1f} minutes")
        print(f"Avg Time per Batch: {self.stats['total_time']/len(schedule):.1f} seconds")
        
        # Calculate speedup vs sequential
        sequential_time = self.stats['total_time'] * self.max_workers
        speedup = sequential_time / self.stats['total_time']
        print(f"Speedup vs Sequential: {speedup:.1f}x")
        print()
        
        return self.stats['batches_failed'] == 0
    
    def run(self, batches_per_geo=None, start_date=None):
        """
        Main orchestration workflow with parallel execution
        """
        print("\n" + "╔" + "═" * 78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "  Phase 4: PARALLEL Batch Generation Orchestrator".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "═" * 78 + "╝")
        
        # Step 1: Analyze infrastructure
        self.analyze_infrastructure()
        
        # Step 2: Calculate batch plan
        if batches_per_geo is None:
            batches_per_geo = self.calculate_batch_plan()
        
        # Step 3: Generate schedule
        schedule = self.generate_batch_schedule(batches_per_geo, start_date)
        
        # Step 4: Execute in parallel
        success = self.execute_batch_generation_parallel(schedule)
        
        return 0 if success else 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate multiple batches in parallel to saturate infrastructure'
    )
    parser.add_argument(
        '--saturation',
        type=float,
        default=0.85,
        help='Target infrastructure saturation (0.0-1.0, default: 0.85)'
    )
    parser.add_argument(
        '--batches',
        type=int,
        help='Override: Number of batches per geography'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Override: Base start date (YYYY-MM-DD, default: 900 days ago)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        help=f'Number of parallel workers (default: {max(1, cpu_count() - 2)})'
    )
    
    args = parser.parse_args()
    
    # Parse start date if provided
    start_date = None
    if args.start_date:
        from datetime import datetime
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    
    orchestrator = ParallelBatchOrchestrator(
        target_saturation=args.saturation,
        max_workers=args.workers
    )
    
    return orchestrator.run(
        batches_per_geo=args.batches,
        start_date=start_date
    )


if __name__ == '__main__':
    sys.exit(main())
