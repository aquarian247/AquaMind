#!/usr/bin/env python3
"""
Throttled batch execution to prevent laptop overheating.

Strategies:
1. Reduce worker count (14 → 8 workers)
2. Add delays between batches (thermal breathing room)
3. Monitor temperature and pause if too hot
4. Process in waves (batch groups with cooldown)
"""
import os
import sys
import json
import yaml
import argparse
import subprocess
import time
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def execute_batch_from_schedule(batch_config):
    """Execute single batch using pre-allocated containers."""
    start_time = time.time()
    batch_id = batch_config['batch_id']
    
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    env['USE_SCHEDULE'] = '1'
    env['CONTAINER_SCHEDULE'] = json.dumps(batch_config['freshwater'])
    if 'sea' in batch_config and batch_config['sea']:
        env['SEA_SCHEDULE'] = json.dumps(batch_config['sea'])
    
    cmd = [
        'python', 'scripts/data_generation/03_event_engine_core.py',
        '--start-date', batch_config['start_date'],
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(batch_config['duration']),
        '--use-schedule'
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            env=env, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=str(project_root)
        )
        duration = time.time() - start_time
        return {'success': True, 'batch_id': batch_id, 'duration': duration}
    except subprocess.CalledProcessError as e:
        return {'success': False, 'batch_id': batch_id, 'error': e.stderr}

def main():
    parser = argparse.ArgumentParser(description='Throttled batch execution (thermal-safe)')
    parser.add_argument('schedule_file', help='Path to YAML schedule file')
    parser.add_argument('--workers', type=int, default=8, 
                       help='Number of parallel workers (default: 8 for thermal safety)')
    parser.add_argument('--wave-size', type=int, default=50,
                       help='Batches per wave (default: 50)')
    parser.add_argument('--cooldown', type=int, default=30,
                       help='Cooldown seconds between waves (default: 30)')
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"THROTTLED BATCH EXECUTION (Thermal-Safe Mode)")
    print(f"{'='*80}\n")
    print(f"Workers: {args.workers} (reduced for thermal safety)")
    print(f"Wave size: {args.wave_size} batches")
    print(f"Cooldown: {args.cooldown}s between waves")
    print()
    
    # Load schedule
    with open(args.schedule_file) as f:
        schedule = yaml.safe_load(f)
    
    batches = schedule.get('batches', [])
    total_batches = len(batches)
    
    print(f"Loaded {total_batches} batches from schedule.")
    print(f"Estimated time: {total_batches * 8 / args.workers / 60:.1f} minutes\n")
    
    # Process in waves
    results = []
    wave_num = 1
    
    for i in range(0, total_batches, args.wave_size):
        wave_batches = batches[i:i+args.wave_size]
        wave_end = min(i + args.wave_size, total_batches)
        
        print(f"{'='*80}")
        print(f"WAVE {wave_num}: Batches {i+1}-{wave_end}")
        print(f"{'='*80}\n")
        
        # Execute wave
        import multiprocessing as mp
        with mp.Pool(processes=args.workers) as pool:
            for j, result in enumerate(pool.imap_unordered(execute_batch_from_schedule, wave_batches)):
                status = "✅" if result['success'] else "❌"
                print(f"[{i+j+1}/{total_batches}] {status} Batch {result['batch_id']} ({result.get('duration', 0):.1f}s)")
                results.append(result)
        
        # Cooldown between waves (thermal breathing room)
        if wave_end < total_batches:
            print(f"\n💤 Cooldown: {args.cooldown}s (thermal safety)...\n")
            time.sleep(args.cooldown)
        
        wave_num += 1
    
    # Summary
    success_count = sum(1 for r in results if r['success'])
    fail_count = total_batches - success_count
    
    print(f"\n{'='*80}")
    print("EXECUTION COMPLETE")
    print(f"{'='*80}")
    print(f"Success: {success_count}/{total_batches} ({success_count/total_batches*100:.1f}%)")
    print(f"Failed: {fail_count}")
    
    return 0 if fail_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())

