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
    
    def generate_batch_schedule(self, batches_per_geo, start_date=None):
        """
        Generate staggered batch start dates
        
        Args:
            batches_per_geo: Number of batches per geography
            start_date: Base start date (defaults to 900 days ago to have active batches)
        """
        if start_date is None:
            # Default: start 900 days ago so first batch is just finishing
            start_date = date.today() - timedelta(days=900)
        
        print("\n" + "="*80)
        print("GENERATING BATCH SCHEDULE")
        print("="*80 + "\n")
        
        schedule = []
        
        for geo_name in ["Faroe Islands", "Scotland"]:
            print(f"\n{geo_name}:")
            print("-" * 40)
            
            for i in range(batches_per_geo):
                # Stagger batches every 30 days
                batch_start = start_date + timedelta(days=i * 30)
                
                # Vary egg count slightly for realism (3.2M - 3.8M)
                import random
                eggs = random.randint(3200000, 3800000)
                
                schedule.append({
                    'start_date': batch_start,
                    'eggs': eggs,
                    'geography': geo_name,
                    'duration': 900  # Full lifecycle
                })
                
                if i < 5:  # Show first 5 for preview
                    print(f"  Batch {i+1:3d}: {batch_start} | {eggs:,} eggs")
            
            if batches_per_geo > 5:
                print(f"  ... ({batches_per_geo - 5} more)")
        
        print(f"\nTotal Batches Scheduled: {len(schedule)}")
        print(f"Date Range: {schedule[0]['start_date']} to {schedule[-1]['start_date']}")
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
            
            if i <= 5 or i > len(schedule) - 2:  # Show first 5 and last 2
                print(f"Batch {i}/{len(schedule)}: {batch_config['geography'][:3]}-{batch_config['start_date']}")
                if dry_run:
                    print(f"  Command: {cmd_str}\n")
            elif i == 6:
                print(f"... (processing batches 6-{len(schedule)-2}) ...\n")
            
            if not dry_run:
                try:
                    result = subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self.stats['batches_generated'] += 1
                    
                    if i <= 3 or i > len(schedule) - 1:
                        print(f"  ✓ Success\n")
                    
                except subprocess.CalledProcessError as e:
                    print(f"  ✗ Error: {e}")
                    print(f"  Output: {e.output}")
                    return False
        
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
    
    def run(self, dry_run=True, batches_per_geo=None, start_date=None):
        """
        Main orchestration workflow
        
        Args:
            dry_run: If True, only show what would be generated
            batches_per_geo: Override calculated batch count
            start_date: Override default start date
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
        schedule = self.generate_batch_schedule(batches_per_geo, start_date)
        
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
        start_date=start_date
    )


if __name__ == '__main__':
    sys.exit(main())
