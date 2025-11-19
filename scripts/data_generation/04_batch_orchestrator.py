#!/usr/bin/env python3
"""
AquaMind Phase 4: Batch Generation Orchestrator
Saturates infrastructure with staggered batches across both geographies
"""
import os
import sys
import django
import subprocess
from datetime import date, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, Container, Hall
from apps.batch.models import Batch


class BatchOrchestrator:
    """
    Orchestrates generation of multiple batches to saturate infrastructure
    """
    
    def __init__(self, target_saturation=0.85):
        """
        Args:
            target_saturation: Target percentage of infrastructure to saturate (0.0-1.0)
        """
        self.target_saturation = target_saturation
        self.stats = {
            'total_containers': 0,
            'available_containers': 0,
            'target_batches': 0,
            'batches_generated': 0
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
        
    def calculate_batch_plan(self):
        """
        Calculate optimal batch distribution
        
        Strategy:
        - Each batch uses ~10 containers in early stages (Egg-Parr: days 0-270)
        - Then ~10 containers in Smolt/Post-Smolt stages (days 270-450)
        - Then ~10 containers in Adult stage (days 450-900)
        
        With 900-day lifecycle and staggered starts every 30 days:
        - We can fit ~30 batches per "slot" of 10 containers
        - Total batches = (total_containers / 10) * (900 / 30) = containers * 3
        
        But we need to account for stage transitions and overlap
        """
        print("\n" + "="*80)
        print("BATCH GENERATION PLAN")
        print("="*80 + "\n")
        
        # Simplified calculation: 
        # Average 10 containers per batch, 900-day lifecycle
        # With 30-day stagger, we can overlap ~30 batches per container set
        # But we want to be conservative and target ~85% saturation
        
        containers_per_batch = 10
        
        # Target number of batches to saturate infrastructure
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
        print()
        
        # Split evenly between geographies
        batches_per_geo = target_batches // 2
        print(f"Distribution:")
        print(f"  Faroe Islands: {batches_per_geo} batches")
        print(f"  Scotland: {batches_per_geo} batches")
        print()
        
        return batches_per_geo
    
    def generate_batch_schedule(self, batches_per_geo, start_date=None, stagger_days=5):
        """
        Generate chronologically-ordered batch schedule.
        
        Strategy: Configurable stagger, chronologically sorted for realistic history.
        Both geographies start simultaneously and progress together.
        - Active batches in various stages (<900 days old) = current operations
        
        This simulates looking at a real farm database after years of operation.
        
        Args:
            batches_per_geo: Number of batches per geography
            start_date: Base start date (defaults to 6 years ago)
        """
        import random
        today = date.today()
        
        if start_date is None:
            # Calculate start date based on stagger and batch count
            span_days = (batches_per_geo - 1) * stagger_days
            buffer_days = 50
            days_back = span_days + buffer_days
            start_date = today - timedelta(days=days_back)
            years_back = days_back / 365
        else:
            years_back = (today - start_date).days / 365
        
        print("\n" + "="*80)
        print("GENERATING BATCH SCHEDULE (Chronological History)")
        print("="*80 + "\n")
        print(f"Strategy: {stagger_days}-day stagger, chronological order (both geographies)")
        print(f"Start: {start_date} ({years_back:.1f} years ago)")
        print(f"Today: {today}")
        print(f"Stagger: Every {stagger_days} days\n")
        
        schedule = []
        
        for geo_name in ["Faroe Islands", "Scotland"]:
            print(f"\n{geo_name}:")
            print("-" * 40)
            
            # Status counters
            status_counts = {
                'Active': 0,
                'Completed': 0
            }
            stage_counts = {
                'Egg&Alevin': 0,
                'Fry': 0,
                'Parr': 0,
                'Smolt': 0,
                'Post-Smolt': 0,
                'Adult': 0,
                'Completed': 0
            }
            
            for i in range(batches_per_geo):
                # Stagger batches every N days
                batch_start = start_date + timedelta(days=i * stagger_days)
                
                # Calculate duration: run up to TODAY
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
                stage_counts[current_stage] += 1
                
                # Vary egg count for realism
                eggs = random.randint(3000000, 3800000)
                
                schedule.append({
                    'start_date': batch_start,
                    'eggs': eggs,
                    'geography': geo_name,
                    'duration': duration,
                    'current_stage': current_stage,
                    'status': status,
                })
                
                # Show first 3, last 2, and status boundary
                actual_count = len([b for b in schedule if b['geography'] == geo_name])
                if actual_count <= 3 or i >= batches_per_geo - 2 or (i > 0 and status != schedule[-2].get('status', '')):
                    print(f"  Batch {actual_count:3d}: {batch_start} | {eggs:,} eggs | {duration:3d} days | {current_stage:12s} | {status}")
                elif actual_count == 4 and schedule[-2].get('status', '') == status:
                    print(f"  ...")
            
            # Show distribution
            actual_batches = len([b for b in schedule if b['geography'] == geo_name])
            print(f"\n  Total Batches: {actual_batches}")
            print(f"  Status Distribution:")
            for status, count in status_counts.items():
                if count > 0:
                    print(f"    {status:15s}: {count:2d} batches ({count/actual_batches*100:.1f}%)")
            print(f"  Active Stage Distribution:")
            for stage, count in stage_counts.items():
                if count > 0 and stage != 'Completed':
                    print(f"    {stage:15s}: {count:2d} batches")
        
        print(f"\n{'='*80}")
        print(f"Total Batches Scheduled: {len(schedule)}")
        
        # Overall distribution
        active_count = len([b for b in schedule if b['status'] == 'Active'])
        completed_count = len([b for b in schedule if b['status'] == 'Completed'])
        
        print(f"\nOverall Distribution:")
        print(f"  Active Batches:    {active_count:3d} ({active_count/len(schedule)*100:.1f}%)")
        print(f"  Completed/Harvest: {completed_count:3d} ({completed_count/len(schedule)*100:.1f}%)")
        
        # Sort chronologically (both geographies interleaved)
        schedule.sort(key=lambda x: x['start_date'])
        
        print(f"\n✅ Schedule sorted chronologically ({len(schedule)} batches)")
        print()
        
        return schedule
    
    def execute_batch_generation(self, schedule, dry_run=True):
        """
        Execute batch generation based on schedule
        
        Args:
            schedule: List of batch configurations
            dry_run: If True, only print commands without executing
        """
        print("\n" + "="*80)
        if dry_run:
            print("BATCH GENERATION PLAN (DRY RUN)")
        else:
            print("EXECUTING BATCH GENERATION")
        print("="*80 + "\n")
        
        script_path = Path(__file__).parent / "03_event_engine_core.py"
        
        for i, batch_config in enumerate(schedule, 1):
            cmd = [
                'python',
                str(script_path),
                '--start-date', str(batch_config['start_date']),
                '--eggs', str(batch_config['eggs']),
                '--geography', batch_config['geography'],
                '--duration', str(batch_config['duration'])
            ]
            
            cmd_str = ' '.join(cmd)
            
            if dry_run:
                if i <= 5 or i > len(schedule) - 2:
                    print(f"Batch {i}/{len(schedule)}: {batch_config['geography'][:3]}-{batch_config['start_date']}")
                    print(f"  Command: {cmd_str}\n")
                elif i == 6:
                    print(f"... (processing batches 6-{len(schedule)-2}) ...\n")
            else:
                # Execute mode - clean progress output
                geo_short = "Faroe" if "Faroe" in batch_config['geography'] else "Scotland"
                print(f"[{i}/{len(schedule)}] Creating batch in {geo_short:8s} | "
                      f"Start: {batch_config['start_date']} | "
                      f"{batch_config['duration']:3d} days...", end=" ", flush=True)
                
                try:
                    result = subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        env={**os.environ, 'SKIP_CELERY_SIGNALS': '1'}  # Always skip Celery in orchestrator
                    )
                    self.stats['batches_generated'] += 1
                    print(f"✓")
                    
                except subprocess.CalledProcessError as e:
                    print(f"✗ FAILED")
                    print(f"     Error: {str(e)[:100]}")
                    self.stats['batches_generated'] += 1  # Count as attempted
                    # Continue with next batch (don't fail entire run)
        
        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN COMPLETE - No batches generated")
            print("="*80)
            print("\nTo execute batch generation, run:")
            print("  python scripts/data_generation/04_batch_orchestrator.py --execute")
            print()
        else:
            print("\n" + "="*80)
            print("BATCH GENERATION COMPLETE")
            print("="*80)
            print(f"\nBatches Generated: {self.stats['batches_generated']}/{len(schedule)}")
            print()
        
        return True
    
    def run(self, dry_run=True, batches_per_geo=None, start_date=None, stagger_days=5):
        """
        Main orchestration workflow
        
        Args:
            dry_run: If True, only show what would be generated
            batches_per_geo: Override calculated batch count
            start_date: Override default start date
            stagger_days: Days between batch starts (default: 5)
        """
        print("\n" + "╔" + "═" * 78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "  Phase 4: Batch Generation Orchestrator".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "═" * 78 + "╝")
        
        # Step 1: Analyze infrastructure
        self.analyze_infrastructure()
        
        # Step 2: Calculate batch plan
        if batches_per_geo is None:
            batches_per_geo = self.calculate_batch_plan()
        
        # Step 3: Generate schedule
        schedule = self.generate_batch_schedule(batches_per_geo, start_date, stagger_days)
        
        # Step 4: Execute (or dry run)
        self.execute_batch_generation(schedule, dry_run)
        
        return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate multiple batches to saturate infrastructure'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute batch generation (default is dry-run)'
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
        '--stagger',
        type=int,
        default=5,
        help='Days between batch starts (default: 5 for 87%% saturation)'
    )
    
    args = parser.parse_args()
    
    # Parse start date if provided
    start_date = None
    if args.start_date:
        from datetime import datetime
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    
    orchestrator = BatchOrchestrator(target_saturation=args.saturation)
    
    return orchestrator.run(
        dry_run=not args.execute,
        batches_per_geo=args.batches,
        start_date=start_date,
        stagger_days=args.stagger
    )


if __name__ == '__main__':
    sys.exit(main())
