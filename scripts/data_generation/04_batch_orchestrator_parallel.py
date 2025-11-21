#!/usr/bin/env python3
"""
AquaMind Phase 4: Parallel Batch Generation Orchestrator

Generates multiple batches simultaneously using multiprocessing.
Uses round-robin station/area selection to prevent container conflicts.
Date-bounded to prevent batches from running into the future.

Key Features:
- Parallel execution across CPU cores (10-15x speedup)
- Round-robin infrastructure distribution (no container conflicts)
- Date-bounded execution (stops at today, no future data)
- Safe for M4 Max 16-core machines (14 workers recommended)

Performance:
- Sequential: 20 batches × 25 min = 8-10 hours
- Parallel (14 workers): ~45-60 minutes (10-12x speedup)

Usage:
    # Dry run (shows plan)
    python scripts/data_generation/04_batch_orchestrator_parallel.py --batches 20

    # Execute with 14 workers (leaves 2 cores for system/DB)
    python scripts/data_generation/04_batch_orchestrator_parallel.py \\
        --execute --batches 20 --workers 14
"""
import os
import sys
import json
import django
import subprocess
from datetime import date, timedelta
from pathlib import Path
import random

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, Container, FreshwaterStation
from apps.batch.models import Batch


def generate_batch_worker(batch_config):
    """
    Worker function for parallel batch generation.
    
    Args:
        batch_config: Dict with start_date, eggs, geography, duration
        
    Returns:
        Dict with success status and batch info
    """
    import os
    script_path = Path(__file__).parent / "03_event_engine_core.py"
    
    # Set environment variable to skip Celery signals during generation
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    
    # Calculate duration limited by today (prevent future data)
    today = date.today()
    days_since_start = (today - batch_config['start_date']).days
    duration = min(batch_config['max_duration'], days_since_start)
    
    # Skip if start date is in the future
    if duration <= 0:
        return {
            'success': True,
            'skipped': True,
            'batch': batch_config['start_date'],
            'geography': batch_config['geography']
        }
    
    cmd = [
        'python',
        str(script_path),
        '--start-date', str(batch_config['start_date']),
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(duration),  # Date-bounded duration
        '--station', batch_config['station_name']  # DETERMINISTIC: Pre-assigned station
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,  # 60 min timeout per batch (900-day batches need more time)
            env=env  # Pass environment with SKIP_CELERY_SIGNALS=1
        )
        
        return {
            'success': True,
            'batch': batch_config['start_date'],
            'geography': batch_config['geography'],
            'duration': duration,
            'output': result.stdout[-500:] if len(result.stdout) > 500 else result.stdout  # Last 500 chars
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'batch': batch_config['start_date'],
            'geography': batch_config['geography'],
            'error': 'Timeout after 60 minutes'
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'batch': batch_config['start_date'],
            'geography': batch_config['geography'],
            'error': f"Exit code {e.returncode}",
            'output': e.stderr[-500:] if len(e.stderr) > 500 else e.stderr
        }


def growth_analysis_worker_subprocess(batch_config):
    """
    Subprocess worker that initializes Django and runs growth analysis.
    Returns JSON-serializable result (not Django model instances).
    
    This approach avoids the Django model pickling issue that breaks multiprocessing.Pool.
    Each subprocess initializes Django independently.
    
    Args:
        batch_config: Dict with batch_id, batch_number, status, start_date, end_date
        
    Returns:
        Dict with success status, batch info, and stats
    """
    import subprocess
    import json
    
    worker_script = '''
import os, sys, django, json
from datetime import date

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.services.growth_assimilation import recompute_batch_assignments

# Read config from stdin
config = json.load(sys.stdin)

# Parse dates
start_date = date.fromisoformat(config['start_date'])
end_date = date.fromisoformat(config['end_date']) if config.get('end_date') else None

# Run growth analysis
try:
    result = recompute_batch_assignments(
        batch_id=config['batch_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    # Return JSON result (not Django models)
    json.dump({
        'batch_id': config['batch_id'],
        'batch_number': config['batch_number'],
        'status': config['status'],
        'success': result.get('total_errors', 0) == 0,
        'states': result.get('total_rows_created', 0),
        'assignments': result.get('assignments_processed', 0),
        'errors': result.get('errors', [])
    }, sys.stdout)
except Exception as e:
    json.dump({
        'batch_id': config['batch_id'],
        'batch_number': config['batch_number'],
        'status': config['status'],
        'success': False,
        'error': str(e)
    }, sys.stdout)
'''
    
    # Prepare input
    config = {
        'batch_id': batch_config['batch_id'],
        'batch_number': batch_config['batch_number'],
        'status': batch_config['status'],
        'start_date': str(batch_config['start_date']),
        'end_date': str(batch_config['end_date']) if batch_config.get('end_date') else None
    }
    
    try:
        proc = subprocess.Popen(
            [sys.executable, '-c', worker_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input=json.dumps(config), timeout=300)
        
        if proc.returncode == 0 and stdout:
            return json.loads(stdout)
        else:
            return {
                'batch_id': batch_config['batch_id'],
                'batch_number': batch_config['batch_number'],
                'status': batch_config['status'],
                'success': False,
                'error': stderr[:500] if stderr else 'Unknown error'
            }
    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            'batch_id': batch_config['batch_id'],
            'batch_number': batch_config['batch_number'],
            'status': batch_config['status'],
            'success': False,
            'error': 'Timeout after 300 seconds'
        }
    except Exception as e:
        return {
            'batch_id': batch_config['batch_id'],
            'batch_number': batch_config['batch_number'],
            'status': batch_config['status'],
            'success': False,
            'error': str(e)
        }


class ParallelBatchOrchestrator:
    """
    Orchestrates parallel batch generation with intelligent scheduling.
    """
    
    def __init__(self, target_saturation=0.85, verbose=False):
        self.target_saturation = target_saturation
        self.verbose = verbose
        self.stats = {
            'total_containers': 0,
            'target_batches': 0,
            'batches_generated': 0,
            'batches_failed': 0,
            'batches_skipped': 0
        }
    
    def analyze_infrastructure(self):
        """Analyze available infrastructure capacity"""
        print("\n" + "="*80)
        print("INFRASTRUCTURE CAPACITY ANALYSIS")
        print("="*80 + "\n")
        
        for geo in Geography.objects.all():
            # Count freshwater containers
            fw_containers = Container.objects.filter(
                hall__freshwater_station__geography=geo,
                active=True
            ).count()
            
            # Count sea containers
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
        print()
    
    def generate_batch_schedule(self, batches_per_geo, start_date=None):
        """
        Generate staggered batch schedule with 6-year operational history.
        
        Strategy: 30-day stagger starting 6 years ago creates both:
        - Completed/harvested batches (>900 days old)
        - Active batches in various stages (<900 days old)
        
        Args:
            batches_per_geo: Number of batches per geography
            start_date: Base start date (defaults to calculated historical date)
        """
        today = date.today()
        
        if start_date is None:
            # Calculate start date so:
            # - First batches are completed (>900 days old)
            # - Last batches are active in early stages
            stagger_days = 11  # 11-day stagger for 80%+ saturation (41 batches overlap = 82% Scotland)
            span_days = (batches_per_geo - 1) * stagger_days
            buffer_days = 50  # Small buffer so youngest batch is in early stage
            days_back = span_days + buffer_days
            start_date = today - timedelta(days=days_back)
            years_back = days_back / 365
        
        print("\n" + "="*80)
        print(f"GENERATING DETERMINISTIC BATCH SCHEDULE ({batches_per_geo} per geography)")
        print("="*80 + "\n")
        print(f"Strategy: 11-day stagger + PRE-ASSIGNED stations (zero conflicts)")
        print(f"Start: {start_date} ({years_back:.1f} years ago)")
        print(f"Today: {today}")
        print(f"Stagger: Every 11 days (80%+ saturation, respects 50-hall bottleneck)\n")
        
        # Get stations for each geography (for deterministic pre-assignment)
        from apps.infrastructure.models import FreshwaterStation
        geo_stations = {}
        for geo_name in ["Faroe Islands", "Scotland"]:
            geo_stations[geo_name] = list(
                FreshwaterStation.objects.filter(geography__name=geo_name).order_by('name')
            )
        
        print(f"Station Pre-Assignment:")
        for geo_name, stations in geo_stations.items():
            print(f"  {geo_name}: {len(stations)} stations available")
        print()
        
        schedule = []
        
        for geo_name in ["Faroe Islands", "Scotland"]:
            print(f"\n{geo_name}:")
            print("-" * 40)
            
            status_counts = {'Active': 0, 'Completed': 0}
            
            for i in range(batches_per_geo):
                # Stagger batches every 11 days (80%+ saturation)
                batch_start = start_date + timedelta(days=i * 11)
                
                # Calculate duration: run up to TODAY (date-bounded)
                days_since_start = (today - batch_start).days
                duration = min(900, days_since_start)
                
                # Determine current stage/status
                if duration >= 900:
                    current_stage = 'Completed'
                    status = 'Completed'
                elif duration < 90:
                    current_stage = 'Egg&Alevin'
                    status = 'Active'
                elif duration < 180:
                    current_stage = 'Fry'
                    status = 'Active'
                elif duration < 270:
                    current_stage = 'Parr'
                    status = 'Active'
                elif duration < 360:
                    current_stage = 'Smolt'
                    status = 'Active'
                elif duration < 450:
                    current_stage = 'Post-Smolt'
                    status = 'Active'
                else:  # 450-900
                    current_stage = 'Adult'
                    status = 'Active'
                
                status_counts[status] += 1
                
                # Vary egg count for realism
                eggs = random.randint(3000000, 3800000)
                
                # DETERMINISTIC: Pre-assign station using round-robin on index
                # Each batch gets its own station, no runtime queries needed
                stations = geo_stations[geo_name]
                station_idx = i % len(stations)
                assigned_station = stations[station_idx].name
                
                schedule.append({
                    'start_date': batch_start,
                    'eggs': eggs,
                    'geography': geo_name,
                    'max_duration': 900,
                    'actual_duration': duration,
                    'current_stage': current_stage,
                    'status': status,
                    'station_name': assigned_station,  # DETERMINISTIC PRE-ASSIGNMENT!
                })
                
                # Show first 3, last 2
                actual_count = len([b for b in schedule if b['geography'] == geo_name])
                if actual_count <= 3 or i >= batches_per_geo - 2:
                    print(f"  Batch {actual_count:3d}: {batch_start} | {eggs:,} eggs | "
                          f"{duration:3d} days | {current_stage:12s} | {assigned_station}")
                elif actual_count == 4:
                    print(f"  ...")
            
            # Show distribution
            actual_batches = len([b for b in schedule if b['geography'] == geo_name])
            print(f"\n  Total: {actual_batches} batches")
            print(f"  Active: {status_counts['Active']} | Completed: {status_counts['Completed']}")
        
        print(f"\n{'='*80}")
        print(f"Total Batches Scheduled: {len(schedule)}")
        print(f"Active: {len([b for b in schedule if b['status'] == 'Active'])}")
        print(f"Completed: {len([b for b in schedule if b['status'] == 'Completed'])}")
        print()
        print("✅ DETERMINISTIC SCHEDULING:")
        print(f"   Each batch pre-assigned to specific station at schedule time")
        print(f"   Zero database queries for station selection during execution")
        print(f"   Expected success rate: 100% (no race conditions)")
        print()
        
        return schedule
    
    def execute_parallel(self, schedule, workers):
        """
        Execute batch generation in parallel using multiprocessing.
        
        Args:
            schedule: List of batch configurations
            workers: Number of parallel workers
        """
        print("\n" + "="*80)
        print(f"EXECUTING PARALLEL GENERATION ({workers} workers)")
        print("="*80 + "\n")
        
        print(f"Total batches: {len(schedule)}")
        print(f"Workers: {workers}")
        print(f"Estimated time: {(len(schedule) * 25) / workers:.0f} minutes\n")
        print("Starting parallel execution...\n")
        
        # Execute in parallel
        with mp.Pool(processes=workers) as pool:
            results = pool.map(generate_batch_worker, schedule)
        
        # Process results
        print("\n" + "="*80)
        print("EXECUTION COMPLETE")
        print("="*80 + "\n")
        
        successful = [r for r in results if r['success'] and not r.get('skipped')]
        failed = [r for r in results if not r['success']]
        skipped = [r for r in results if r.get('skipped')]
        
        self.stats['batches_generated'] = len(successful)
        self.stats['batches_failed'] = len(failed)
        self.stats['batches_skipped'] = len(skipped)
        
        print(f"✓ Successful: {len(successful)}")
        print(f"✗ Failed: {len(failed)}")
        print(f"○ Skipped: {len(skipped)}")
        
        if failed:
            print(f"\n⚠️  Failed batches:")
            for r in failed:
                print(f"  - {r['batch']} ({r['geography']}): {r.get('error', 'Unknown error')}")
        
        if skipped:
            print(f"\nSkipped batches (start date in future):")
            for r in skipped:
                print(f"  - {r['batch']} ({r['geography']})")
        
        print()
        return len(failed) == 0
    
    def _execute_growth_analysis_parallel(self, tasks, workers):
        """
        Run growth analysis using subprocess-based parallelization.
        
        This approach avoids Django model pickling issues by using subprocess
        workers that initialize Django independently.
        
        Args:
            tasks: List of batch configs with batch_id, batch_number, status, dates
            workers: Number of parallel workers to use
            
        Returns:
            List of result dicts with success status and stats
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import time
        
        start_time = time.time()
        results = []
        total = len(tasks)
        interval = max(1, total // 10)
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs
            future_to_task = {
                executor.submit(growth_analysis_worker_subprocess, task): task
                for task in tasks
            }
            
            # Collect results as they complete
            processed = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    processed += 1
                    self._log_growth_progress(result, processed, total, interval)
                except Exception as exc:
                    # Worker crashed - create error result
                    error_result = {
                        'success': False,
                        'batch_number': task['batch_number'],
                        'status': task['status'],
                        'error': f'Worker exception: {str(exc)[:100]}'
                    }
                    results.append(error_result)
                    processed += 1
                    self._log_growth_progress(error_result, processed, total, interval)
        
        elapsed = time.time() - start_time
        print(f"\n  Total time: {elapsed/60:.1f} minutes ({elapsed/total:.1f}s per batch)\n")
        
        return results

    def _log_growth_progress(self, result, processed, total, interval):
        """Print concise progress updates unless verbose logging requested."""
        if self.verbose or not result['success']:
            status_icon = "✓" if result['success'] else "✗"
            if result['success']:
                print(f"{status_icon} {result['batch_number']} ({result['status']}): {result.get('states', 0):,} states")
            else:
                print(f"{status_icon} {result['batch_number']} ({result['status']}): {result.get('error', 'Unknown error')}")
        elif processed % interval == 0 or processed == total:
            print(f"  ... {processed}/{total} batches processed")
    
    def recompute_all_batches(self):
        """
        Recompute Growth Analysis (ActualDailyAssignmentState) for ALL successful batches.
        
        This is the final step after parallel batch generation completes.
        It computes the orange "Actual Daily State" line for Growth Analysis charts.
        
        Computes for:
        - ACTIVE batches (not yet harvested)
        - COMPLETED batches (already harvested)
        
        Skips batches that already have Growth Analysis data (from event engine).
        """
        print("\n" + "="*80)
        print("GROWTH ANALYSIS BULK RECOMPUTE")
        print("="*80 + "\n")
        
        try:
            from apps.batch.models import Batch
            
            # Get ALL batches with assignments (successful generation)
            all_batches = Batch.objects.filter(
                batch_assignments__isnull=False
            ).distinct().order_by('batch_number')
            
            # Filter to only those without Growth Analysis
            batches_needing_compute = [b for b in all_batches if not b.daily_states.exists()]
            total = len(batches_needing_compute)
            
            if total == 0:
                print("✅ All batches already have Growth Analysis data. Skipping.")
                return
            
            print(f"Found {total} batches needing Growth Analysis computation")
            print(f"(Includes ACTIVE and COMPLETED batches)")
            print()

            # Prepare batch data for parallel processing
            growth_tasks = []
            for batch in batches_needing_compute:
                # For active batches, use current date as end_date
                # For completed batches, use actual_end_date if available, otherwise current date
                if batch.status == 'COMPLETED' and batch.actual_end_date:
                    end_date = batch.actual_end_date
                else:
                    end_date = None  # Let recompute_batch_assignments default to today

                growth_tasks.append({
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'status': batch.status,
                    'start_date': batch.start_date,
                    'end_date': end_date
                })

            # Execute growth analysis in parallel
            num_workers = max(1, min(14, total))  # Use same number as batch generation
            print(f"EXECUTING PARALLEL GROWTH ANALYSIS ({num_workers} workers)")
            print("="*80 + "\n")

            results = self._execute_growth_analysis_parallel(growth_tasks, num_workers)

            # Process results
            print("\n" + "="*80)
            print("GROWTH ANALYSIS COMPLETE")
            print("="*80 + "\n")

            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            total_states = sum(r.get('states', 0) for r in successful)

            print(f"✓ Successful: {len(successful)}/{total}")
            print(f"✓ Total states generated: {total_states:,}")

            if failed:
                print(f"⚠ Failed: {len(failed)}/{total}")
                for result in failed:
                    print(f"   - {result['batch_number']} ({result['status']}): {result.get('error', 'Unknown error')}")

            print()
            print("="*80)
            print(f"GROWTH ANALYSIS RECOMPUTE COMPLETE")
            print("="*80)
            if not failed:
                print("✅ All batches now have ActualDailyAssignmentState data")
                print("   Growth Analysis UI will show all 3 series (samples, scenario, actual)")
            else:
                print("⚠ Some batches failed to recompute. See logs above for details.")
            
        except Exception as e:
            print(f"❌ Bulk recompute failed: {e}")
            import traceback
            traceback.print_exc()
            print("\n⚠️  Growth Analysis recompute failed but batches were generated successfully")
            print("   UI will work but Growth Analysis charts may be incomplete")
    
    def generate_finance_data(self):
        """
        Generate finance facts and intercompany transactions from harvest events.
        
        Runs the finance_project management command which:
        - Creates FactHarvest records for all HarvestLot records
        - Creates IntercompanyTransaction records for cross-subsidiary flows
        - Links harvest data to finance dimensions (company, site, grade)
        
        Required for:
        - Finance reporting and BI
        - NAV/ERP export readiness
        - Intercompany pricing and reconciliation
        """
        try:
            print()
            print("="*80)
            print("FINANCE DATA GENERATION")
            print("="*80)
            print()
            print("🏦 Creating Finance Facts and Intercompany Transactions...")
            print("   (This processes all harvest events and lots)")
            print()
            
            from django.core.management import call_command
            from apps.finance.models import FactHarvest, IntercompanyTransaction
            
            # Get counts before
            facts_before = FactHarvest.objects.count()
            txs_before = IntercompanyTransaction.objects.count()
            
            # Run finance projection
            call_command('finance_project', verbosity=1)
            
            # Get counts after
            facts_after = FactHarvest.objects.count()
            txs_after = IntercompanyTransaction.objects.count()
            
            print()
            print("="*80)
            print("FINANCE DATA GENERATION COMPLETE")
            print("="*80)
            print(f"✅ Finance Facts: {facts_after} (created {facts_after - facts_before} new)")
            print(f"✅ Intercompany Transactions: {txs_after} (created {txs_after - txs_before} new)")
            print()
            print("   Finance reporting ready!")
            print("   NAV export ready (once transactions approved)")
            print()
            
        except Exception as e:
            print(f"\n⚠️  Finance data generation failed: {e}")
            print("   You can run manually:")
            print("   python manage.py finance_project")
            import traceback
            traceback.print_exc()
    
    def run(self, dry_run=True, batches_per_geo=None, workers=None):
        """
        Main orchestration workflow
        
        Args:
            dry_run: If True, only show what would be generated
            batches_per_geo: Number of batches per geography
            workers: Number of parallel workers
        """
        print("\n" + "╔" + "═" * 78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "  Phase 4: Parallel Batch Orchestrator".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "═" * 78 + "╝")
        
        # Analyze infrastructure
        self.analyze_infrastructure()
        
        # Generate schedule
        if batches_per_geo is None:
            # Calculate based on infrastructure
            containers_per_batch = 10
            batches_per_geo = int(
                (self.stats['total_containers'] / containers_per_batch) * 
                self.target_saturation / 2  # Divide by 2 geographies
            )
        
        schedule = self.generate_batch_schedule(batches_per_geo)
        
        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN COMPLETE - No batches generated")
            print("="*80)
            print("\nTo execute with parallel processing:")
            print(f"  python scripts/data_generation/04_batch_orchestrator_parallel.py \\")
            print(f"    --execute --batches {batches_per_geo} --workers {workers or 14}")
            print()
            return 0
        
        # Execute in parallel
        success = self.execute_parallel(schedule, workers or 14)
        
        # Run post-processing even if some batches failed
        # (successful batches still need Growth Analysis and Finance data)
        if not dry_run:
            successful_count = self.stats.get('batches_generated', 0)
            
            if successful_count > 0:
                print(f"\n📊 Post-processing {successful_count} successful batches...")
                
                # Recompute growth analysis for all batches (ACTIVE + COMPLETED)
                self.recompute_all_batches()
                
                # Generate finance facts and intercompany transactions
                self.generate_finance_data()
            else:
                print("\n⚠️  No successful batches to post-process")
        
        return 0 if success else 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate multiple batches in parallel'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute batch generation (default is dry-run)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=14,
        help='Number of parallel workers (default: 14, max: 16)'
    )
    parser.add_argument(
        '--batches',
        type=int,
        default=10,
        help='Number of batches per geography (default: 10)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging for worker progress'
    )
    
    args = parser.parse_args()
    
    # Validate workers
    cpu_count = mp.cpu_count()
    if args.workers > cpu_count:
        print(f"⚠️  Warning: Requested {args.workers} workers but only {cpu_count} CPUs available.")
        print(f"   Limiting to {cpu_count - 2} workers (leaving 2 for system/DB)")
        args.workers = cpu_count - 2
    
    orchestrator = ParallelBatchOrchestrator(verbose=args.verbose)
    
    return orchestrator.run(
        dry_run=not args.execute,
        batches_per_geo=args.batches,
        workers=args.workers
    )


if __name__ == '__main__':
    sys.exit(main())
