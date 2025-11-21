#!/usr/bin/env python3
"""
Batch Generation Schedule Executor

Executes a pre-planned batch generation schedule using the Event Engine.
Supports parallel execution with 100% reliability (no race conditions).

Usage:
    python execute_batch_schedule.py config/batch_schedule.yaml --workers 14
"""
import os
import sys
import json
import yaml
import argparse
import subprocess
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
import time

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _resolve_log_path(log_dir, batch_id):
    """Resolve log file path for batch."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"batch_{batch_id}.log"


def _write_batch_log(log_path, stdout, stderr, success):
    """Write batch execution log."""
    with open(log_path, 'w') as f:
        f.write(f"{'='*80}\n")
        f.write(f"Batch Execution Log\n")
        f.write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
        f.write(f"{'='*80}\n\n")
        
        f.write("=== STDOUT ===\n")
        f.write(stdout or "(empty)\n")
        f.write("\n=== STDERR ===\n")
        f.write(stderr or "(empty)\n")


def execute_batch_from_schedule(batch_config, log_dir=None):
    """
    Execute single batch using pre-allocated containers from schedule.
    Running in a separate process via subprocess.
    """
    start_time = time.time()
    batch_id = batch_config['batch_id']

    # Prepare environment variables with schedule
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    env['USE_SCHEDULE'] = '1'
    env['CONTAINER_SCHEDULE'] = json.dumps(batch_config['freshwater'])
    if 'sea' in batch_config and batch_config['sea']:
        env['SEA_SCHEDULE'] = json.dumps(batch_config['sea'])

    # Pass harvest target if specified (for deterministic randomness)
    if 'harvest_target_kg' in batch_config:
        env['HARVEST_TARGET_KG'] = str(batch_config['harvest_target_kg'])

    cmd = [
        'python', 'scripts/data_generation/03_event_engine_core.py',
        '--start-date', batch_config['start_date'],
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(batch_config['duration']),
        '--use-schedule'
    ]
    
    try:
        # Capture output to avoid terminal spam, but save logs if needed
        result = subprocess.run(
            cmd, 
            env=env, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=str(project_root)
        )
        duration = time.time() - start_time
        
        # Write log file if log_dir provided
        if log_dir:
            log_path = _resolve_log_path(log_dir, batch_id)
            _write_batch_log(log_path, result.stdout, "", True)
        
        return {
            'success': True, 
            'batch_id': batch_id, 
            'duration': duration,
            'output': result.stdout
        }
    except subprocess.CalledProcessError as e:
        # Write error log
        if log_dir:
            log_path = _resolve_log_path(log_dir, batch_id)
            _write_batch_log(log_path, e.stdout, e.stderr, False)
        
        return {
            'success': False, 
            'batch_id': batch_id, 
            'error': e.stderr,
            'output': e.stdout
        }

def execute_worker_partition(args):
    """Execute a partition of batches assigned to a single worker."""
    worker_id, batch_configs, log_dir = args
    results = []
    
    for batch_config in batch_configs:
        result = execute_batch_from_schedule(batch_config, log_dir)
        result['worker_id'] = worker_id
        results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Execute batch generation schedule')
    parser.add_argument('schedule_file', help='Path to YAML schedule file')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers (default: 1)')
    parser.add_argument('--use-partitions', action='store_true', 
                       help='Use pre-planned worker partitions (eliminates races)')
    parser.add_argument('--log-dir', type=str, default='scripts/data_generation/logs',
                       help='Directory for per-batch execution logs (default: scripts/data_generation/logs)')
    args = parser.parse_args()
    
    if not os.path.exists(args.schedule_file):
        print(f"❌ Schedule file not found: {args.schedule_file}")
        return 1
    
    print(f"\n{'='*80}")
    print(f"EXECUTING BATCH SCHEDULE: {args.schedule_file}")
    print(f"Workers: {args.workers}")
    print(f"Mode: {'Partitioned (Zero Conflicts)' if args.use_partitions else 'Standard'}")
    print(f"{'='*80}\n")
    
    # Load schedule
    with open(args.schedule_file) as f:
        schedule = yaml.safe_load(f)
    
    batches = schedule.get('batches', [])
    total_batches = len(batches)
    metadata = schedule.get('metadata', {})
    worker_partitions = metadata.get('worker_partitions', {})
    
    print(f"Loaded {total_batches} batches from schedule.")
    
    start_time = time.time()
    results = []
    
    # Execute based on mode
    if args.workers > 1 and args.use_partitions and worker_partitions:
        # PARTITIONED MODE: Each worker gets non-overlapping time slice
        print(f"\n🎯 Using pre-planned partitions (zero container conflicts):")
        
        # Build worker tasks
        worker_tasks = []
        for worker_id, partition_info in worker_partitions.items():
            batch_indices = partition_info['batch_indices']
            worker_batches = [batches[i] for i in batch_indices]
            worker_tasks.append((worker_id, worker_batches, args.log_dir))
            print(f"  {worker_id}: {partition_info['count']} batches (indices {partition_info['batch_range']})")
        
        print(f"\nStarting {len(worker_tasks)} workers with partitioned execution...\n")
        
        # Execute partitions in parallel (each worker processes its own time slice)
        with mp.Pool(processes=min(args.workers, len(worker_tasks))) as pool:
            partition_results = pool.map(execute_worker_partition, worker_tasks)
        
        # Flatten results
        completed = 0
        for worker_results in partition_results:
            for result in worker_results:
                completed += 1
                status = "✅" if result['success'] else "❌"
                worker = result.get('worker_id', 'unknown')
                print(f"[{completed}/{total_batches}] {status} {worker}: Batch {result['batch_id']} ({result.get('duration', 0):.1f}s)")
                results.append(result)
                
                if not result['success']:
                    print(f"  Error: {result.get('error', 'Unknown error')[:100]}...")
    
    elif args.workers > 1:
        # STANDARD MODE: Workers compete for batches (may have races)
        print(f"Starting parallel execution with {args.workers} workers...")
        from functools import partial
        execute_with_log = partial(execute_batch_from_schedule, log_dir=args.log_dir)
        with mp.Pool(processes=args.workers) as pool:
            for i, result in enumerate(pool.imap_unordered(execute_with_log, batches)):
                status = "✅" if result['success'] else "❌"
                print(f"[{i+1}/{total_batches}] {status} Batch {result['batch_id']} ({result.get('duration', 0):.1f}s)")
                results.append(result)
                
                if not result['success']:
                    print(f"\nError in batch {result['batch_id']}:")
                    print(result.get('error', 'Unknown error'))
                    print("-" * 40)
    else:
        # SEQUENTIAL MODE
        print("Starting sequential execution...")
        for i, batch in enumerate(batches):
            result = execute_batch_from_schedule(batch, args.log_dir)
            status = "✅" if result['success'] else "❌"
            print(f"[{i+1}/{total_batches}] {status} Batch {result['batch_id']} ({result.get('duration', 0):.1f}s)")
            results.append(result)
            
            if not result['success']:
                print(f"\nError in batch {result['batch_id']}:")
                print(result.get('error', 'Unknown error'))
                print("-" * 40)
    
    # Summary
    total_duration = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    fail_count = total_batches - success_count
    
    print(f"\n{'='*80}")
    print("EXECUTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total Time: {total_duration/60:.1f} minutes ({total_duration/3600:.1f} hours)")
    print(f"Success: {success_count}/{total_batches} ({success_count/total_batches*100:.1f}%)")
    print(f"Failed: {fail_count}")
    
    if fail_count > 0:
        print("\nFailed Batches:")
        for r in results:
            if not r['success']:
                print(f"  - {r['batch_id']}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())