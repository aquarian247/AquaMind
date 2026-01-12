#!/usr/bin/env python3
"""
UAT-Optimized Batch Generation Schedule Planner

Creates a deterministic schedule with batches positioned at specific lifecycle stages
for comprehensive User Acceptance Testing (UAT).

Key Differences from Standard Schedule:
- "Lifecycle Ladder" distribution: Batches at specific day targets (not time-staggered)
- Equal representation across all lifecycle stages
- Near-transition positioning for workflow testing
- Fresh data extending to TODAY for live forward projection

Usage:
    # Generate UAT schedule (recommended)
    python generate_uat_schedule.py --output config/schedule_uat.yaml
    
    # Dry run (just validate, don't save)
    python generate_uat_schedule.py --dry-run
    
    # Custom completed batch count
    python generate_uat_schedule.py --completed-batches 60 --output config/schedule_uat.yaml
"""
import os
import sys
import django
import yaml
import argparse
from datetime import date, timedelta
from pathlib import Path
import random
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, FreshwaterStation, Hall, Area, Container
from apps.batch.models import LifeCycleStage


# ============================================================================
# UAT LIFECYCLE TARGETS
# ============================================================================
# These define specific day positions for batches to enable comprehensive UAT testing.
# Each batch will be at exactly this lifecycle position on the day of execution.
#
# Formula: start_date = TODAY - day_number
# ============================================================================

UAT_LIFECYCLE_TARGETS = [
    # -------------------------------------------------------------------------
    # Egg & Alevin (Stage Order 1, Days 1-90)
    # Testing: Initial batch creation, early mortality, no feeding
    # -------------------------------------------------------------------------
    {"day": 25,  "stage_order": 1, "purpose": "early_stage", "desc": "Early incubation"},
    {"day": 45,  "stage_order": 1, "purpose": "mid_stage", "desc": "Mid incubation"},
    {"day": 65,  "stage_order": 1, "purpose": "mid_stage", "desc": "Late incubation"},
    {"day": 82,  "stage_order": 1, "purpose": "pre_transition", "desc": "Near first feeding"},
    {"day": 88,  "stage_order": 1, "purpose": "transition_ready", "desc": "Ready for Fry transition"},
    
    # -------------------------------------------------------------------------
    # Fry (Stage Order 2, Days 91-180)
    # Testing: First feeding, early growth samples, vaccination scheduling
    # -------------------------------------------------------------------------
    {"day": 105, "stage_order": 2, "purpose": "early_stage", "desc": "Early Fry"},
    {"day": 130, "stage_order": 2, "purpose": "mid_stage", "desc": "Mid Fry"},
    {"day": 155, "stage_order": 2, "purpose": "mid_stage", "desc": "Late Fry"},
    {"day": 175, "stage_order": 2, "purpose": "transition_ready", "desc": "Ready for Parr transition"},
    
    # -------------------------------------------------------------------------
    # Parr (Stage Order 3, Days 181-270)
    # Testing: Growth tracking, health sampling, FCR calculations
    # -------------------------------------------------------------------------
    {"day": 195, "stage_order": 3, "purpose": "early_stage", "desc": "Early Parr"},
    {"day": 220, "stage_order": 3, "purpose": "mid_stage", "desc": "Mid Parr"},
    {"day": 245, "stage_order": 3, "purpose": "mid_stage", "desc": "Late Parr"},
    {"day": 265, "stage_order": 3, "purpose": "transition_ready", "desc": "Ready for Smolt transition"},
    
    # -------------------------------------------------------------------------
    # Smolt (Stage Order 4, Days 271-360)
    # Testing: CRITICAL FW→Sea transfer workflows, intercompany transactions
    # -------------------------------------------------------------------------
    {"day": 285, "stage_order": 4, "purpose": "early_stage", "desc": "Early Smolt"},
    {"day": 315, "stage_order": 4, "purpose": "mid_stage", "desc": "Mid Smolt"},
    {"day": 345, "stage_order": 4, "purpose": "pre_transition", "desc": "Pre-sea transfer"},
    {"day": 358, "stage_order": 4, "purpose": "transition_critical", "desc": "FW→Sea transfer imminent"},
    
    # -------------------------------------------------------------------------
    # Post-Smolt (Stage Order 5, Days 361-450)
    # Testing: Sea adaptation, first sea health checks, lice monitoring
    # -------------------------------------------------------------------------
    {"day": 375, "stage_order": 5, "purpose": "early_stage", "desc": "Early Post-Smolt"},
    {"day": 405, "stage_order": 5, "purpose": "mid_stage", "desc": "Mid Post-Smolt"},
    {"day": 435, "stage_order": 5, "purpose": "mid_stage", "desc": "Late Post-Smolt"},
    {"day": 448, "stage_order": 5, "purpose": "transition_ready", "desc": "Ready for Adult transition"},
    
    # -------------------------------------------------------------------------
    # Adult (Stage Order 6, Days 451-900)
    # Testing: Live forward projection, harvest planning, growth analysis
    # -------------------------------------------------------------------------
    {"day": 480, "stage_order": 6, "purpose": "early_adult", "desc": "Early Adult"},
    {"day": 550, "stage_order": 6, "purpose": "mid_adult", "desc": "Growing Adult"},
    {"day": 650, "stage_order": 6, "purpose": "mid_adult", "desc": "Mid Adult"},
    {"day": 720, "stage_order": 6, "purpose": "late_adult", "desc": "Late Adult"},
    {"day": 780, "stage_order": 6, "purpose": "pre_harvest", "desc": "Pre-harvest (~4kg)"},
    {"day": 820, "stage_order": 6, "purpose": "harvest_threshold", "desc": "Harvest threshold (~5kg)"},
    {"day": 860, "stage_order": 6, "purpose": "harvest_ready", "desc": "Harvest ready (~5.5kg)"},
]


class UATSchedulePlanner:
    """
    Plans UAT-optimized batch generation schedule with lifecycle ladder distribution.
    """
    
    def __init__(self, completed_batches_per_geo=40, target_saturation=0.85):
        self.completed_batches_per_geo = completed_batches_per_geo
        self.target_saturation = target_saturation
        self.occupancy = defaultdict(list)  # {container_name: [(start_day, end_day, batch_id), ...]}
        self.schedule = []
        
        # Stage durations (from event engine)
        self.stage_durations = {
            'Egg&Alevin': 90,
            'Fry': 90,
            'Parr': 90,
            'Smolt': 90,
            'Post-Smolt': 90,
            'Adult': 450
        }
        
        # Harvest parameters
        tgc_adult, temp_sea = self._get_adult_tgc_and_temp()
        self.harvest_targets = {
            'min_weight_kg': 4.5,
            'max_weight_kg': 6.5,
            'adult_start_weight_g': 450,
            'tgc_adult': tgc_adult,
            'temp_sea_c': temp_sea
        }
    
    def _get_adult_tgc_and_temp(self):
        """Get Adult stage TGC and temperature from database."""
        try:
            from apps.scenario.models import TGCModel, TemperatureProfile, TemperatureReading
            from django.db.models import Avg
            
            tgc_model = TGCModel.objects.first()
            tgc_value = float(tgc_model.tgc_value) if tgc_model else 0.0031
            
            temp_profile = TemperatureProfile.objects.filter(name__icontains='Sea').first()
            if temp_profile:
                avg_temp = TemperatureReading.objects.filter(
                    profile=temp_profile
                ).aggregate(avg=Avg('temperature'))['avg']
                temp_c = float(avg_temp) if avg_temp else 9.0
            else:
                temp_c = 9.0
            
            return tgc_value, temp_c
        except Exception:
            return 0.0031, 9.0
    
    def generate_schedule(self):
        """Generate complete UAT-optimized schedule."""
        print("\n" + "="*80)
        print("UAT-OPTIMIZED BATCH GENERATION SCHEDULE PLANNER")
        print("="*80 + "\n")
        
        today = date.today()
        
        print(f"Configuration:")
        print(f"  Today: {today}")
        print(f"  Active targets: {len(UAT_LIFECYCLE_TARGETS)} positions per geography")
        print(f"  Completed batches: {self.completed_batches_per_geo} per geography")
        print(f"  Total batches: {(len(UAT_LIFECYCLE_TARGETS) + self.completed_batches_per_geo) * 2}")
        print(f"  Target saturation: {self.target_saturation*100:.0f}%")
        print()
        
        # Load infrastructure
        self._load_infrastructure()
        
        geos = ["Faroe Islands", "Scotland"]
        
        # =====================================================================
        # PHASE 1: Generate strategically positioned ACTIVE batches
        # =====================================================================
        print("\n📍 Phase 1: Generating active batches at lifecycle positions...")
        print("-" * 60)
        
        # Group targets by stage for reporting
        stage_names = {1: "Egg&Alevin", 2: "Fry", 3: "Parr", 4: "Smolt", 5: "Post-Smolt", 6: "Adult"}
        
        batch_index = 0
        for geo_name in geos:
            geo_data = self.infrastructure[geo_name]
            geo_prefix = "FAR" if "Faroe" in geo_name else "SCO"
            
            current_stage = None
            for target in UAT_LIFECYCLE_TARGETS:
                # Calculate start date to position batch at target day today
                start_date = today - timedelta(days=target['day'])
                duration = target['day']  # Batch runs exactly to today
                
                # Print stage header when stage changes
                stage_order = target['stage_order']
                if current_stage != stage_order:
                    current_stage = stage_order
                    print(f"\n  {stage_names[stage_order]} ({geo_name}):")
                
                try:
                    batch_id = f"{geo_prefix}-UAT-{target['day']:03d}"
                    
                    batch_config = self._plan_single_batch(
                        geo_name=geo_name,
                        geo_data=geo_data,
                        batch_index=batch_index,
                        batch_id=batch_id,
                        batch_start=start_date,
                        duration=duration,
                        purpose=target['purpose']
                    )
                    
                    self.schedule.append(batch_config)
                    
                    print(f"    Day {target['day']:3d}: {batch_id} | {target['desc']} | {target['purpose']}")
                    batch_index += 1
                    
                except Exception as e:
                    print(f"    ❌ Day {target['day']:3d}: FAILED - {e}")
                    raise
        
        # =====================================================================
        # PHASE 2: Generate COMPLETED batches for historical depth
        # =====================================================================
        print(f"\n📚 Phase 2: Generating {self.completed_batches_per_geo * 2} completed batches...")
        print("-" * 60)
        
        # Start historical batches ~5.5 years ago with 30-day stagger
        total_lifecycle = sum(self.stage_durations.values())  # 900 days
        historical_start = today - timedelta(days=5*365 + total_lifecycle)
        
        for geo_idx, geo_name in enumerate(geos):
            geo_data = self.infrastructure[geo_name]
            geo_prefix = "FAR" if "Faroe" in geo_name else "SCO"
            
            for i in range(self.completed_batches_per_geo):
                # Interleave geographies: day 0, 15, 30, 45... (30-day per-geo stagger)
                # This gives 15-day global stagger between F and S
                start_offset = (i * 2 + geo_idx) * 15
                start_date = historical_start + timedelta(days=start_offset)
                
                # Calculate how many days this batch should run
                days_since_start = (today - start_date).days
                
                # Only include if batch would be completed (>900 days old)
                if days_since_start < total_lifecycle:
                    continue
                
                duration = total_lifecycle  # Full 900-day lifecycle
                batch_id = f"{geo_prefix}-{start_date.year}-{(i+1):03d}"
                
                try:
                    batch_config = self._plan_single_batch(
                        geo_name=geo_name,
                        geo_data=geo_data,
                        batch_index=batch_index,
                        batch_id=batch_id,
                        batch_start=start_date,
                        duration=duration,
                        purpose="completed"
                    )
                    
                    self.schedule.append(batch_config)
                    batch_index += 1
                    
                    if i < 3 or i >= self.completed_batches_per_geo - 2:
                        print(f"  {batch_id}: {start_date} | 900 days | Completed")
                    elif i == 3:
                        print(f"  ...")
                    
                except Exception as e:
                    print(f"  ❌ {batch_id}: FAILED - {e}")
                    # Continue with others for completed batches
        
        return self.schedule
    
    def _load_infrastructure(self):
        """Load and organize infrastructure data."""
        print("Loading infrastructure...")
        
        self.infrastructure = {}
        
        for geo in Geography.objects.filter(name__in=['Faroe Islands', 'Scotland']):
            prefix = 'FI-FW' if geo.name == 'Faroe Islands' else 'S-FW'
            stations = list(FreshwaterStation.objects.filter(
                geography=geo,
                name__startswith=prefix
            ).order_by('name'))
            
            areas = list(Area.objects.filter(geography=geo).order_by('name'))
            
            self.infrastructure[geo.name] = {
                'geography': geo,
                'stations': stations,
                'areas': areas,
            }
            
            print(f"  {geo.name}: {len(stations)} stations, {len(areas)} sea areas")
        
        print()
    
    def _plan_single_batch(self, geo_name, geo_data, batch_index, batch_id, batch_start, duration, purpose):
        """Plan container allocation for single batch."""
        
        # Estimate harvest timing for container planning
        harvest_target_kg = self.harvest_targets['max_weight_kg']
        estimated_harvest_days = self._estimate_harvest_days(
            adult_start_weight_g=self.harvest_targets['adult_start_weight_g'],
            target_harvest_kg=harvest_target_kg,
            tgc=self.harvest_targets['tgc_adult'],
            temp_c=self.harvest_targets['temp_sea_c']
        )
        effective_duration = max(duration, int(estimated_harvest_days) + 450)
        
        # Allocate freshwater containers
        fw_containers = self._allocate_freshwater_independent(
            geo_data['stations'],
            batch_index,
            batch_start,
            duration  # Use actual duration for allocation
        )
        
        # Get station name from first allocated hall
        first_hall_name = list(fw_containers.values())[0]['hall'] if fw_containers else None
        station_name = first_hall_name.rsplit('-Hall-', 1)[0] if first_hall_name else geo_data['stations'][0].name
        
        # Allocate sea rings
        area_idx = batch_index % len(geo_data['areas'])
        sea_containers = self._allocate_sea_rings(
            geo_data['areas'],
            area_idx,
            batch_index,
            batch_start,
            duration
        )
        
        # Deterministic egg count
        eggs = 3000000 + ((batch_index * 123456) % 800000)
        actual_harvest_target = random.uniform(
            self.harvest_targets['min_weight_kg'],
            self.harvest_targets['max_weight_kg']
        )
        
        return {
            'batch_id': batch_id,
            'start_date': str(batch_start),
            'eggs': eggs,
            'duration': duration,
            'effective_duration': effective_duration,
            'harvest_target_kg': actual_harvest_target,
            'geography': geo_name,
            'station': station_name,
            'purpose': purpose,
            'freshwater': fw_containers,
            'sea': sea_containers,
        }
    
    def _allocate_freshwater_independent(self, all_stations, batch_index, batch_start, duration):
        """Allocate freshwater halls independently per stage."""
        allocations = {}
        
        stage_configs = [
            ('Egg&Alevin', 'A', 0),
            ('Fry', 'B', 90),
            ('Parr', 'C', 180),
            ('Smolt', 'D', 270),
            ('Post-Smolt', 'E', 360)
        ]
        
        for stage_name, hall_letter, stage_start_day in stage_configs:
            stage_end_day = stage_start_day + self.stage_durations[stage_name]
            
            if stage_start_day >= duration:
                continue
            
            allocated_hall = None
            allocated_containers = []
            
            for station in all_stations:
                hall_name = f"{station.name}-Hall-{hall_letter}"
                containers = list(Container.objects.filter(hall__name=hall_name).order_by('name'))
                
                if len(containers) < 10:
                    continue
                
                absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
                absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
                
                available = []
                for container in containers:
                    if self._check_container_available(container.name, absolute_start, absolute_end):
                        available.append(container)
                    if len(available) == 10:
                        break
                
                if len(available) == 10:
                    allocated_hall = hall_name
                    allocated_containers = available
                    
                    for container in available:
                        self.occupancy[container.name].append((absolute_start, absolute_end, batch_index))
                    
                    break
            
            if not allocated_hall:
                raise Exception(
                    f"No {hall_letter} hall has 10 available containers for batch {batch_index} "
                    f"starting {batch_start}!"
                )
            
            allocations[stage_name.lower().replace('&', '_').replace('-', '_')] = {
                'hall': allocated_hall,
                'containers': [c.name for c in allocated_containers],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration)
            }
        
        return allocations
    
    def _allocate_sea_rings(self, areas, preferred_area_idx, batch_index, batch_start, duration):
        """Allocate sea rings for Adult stage."""
        adult_start_day = sum([90, 90, 90, 90, 90])  # 450
        adult_end_day = min(adult_start_day + self.stage_durations['Adult'], duration)
        
        if duration < adult_start_day:
            return None
        
        for offset in range(len(areas)):
            area_idx = (preferred_area_idx + offset) % len(areas)
            area = areas[area_idx]
            
            rings = list(Container.objects.filter(area=area).order_by('name'))
            
            if len(rings) != 20:
                continue
            
            for ring_count in [10, 12, 15, 20, 8]:
                available_rings = []
                for ring in rings:
                    if self._check_rings_available([ring], batch_start, adult_start_day, adult_end_day):
                        available_rings.append(ring)
                    if len(available_rings) == ring_count:
                        break
                
                if len(available_rings) >= ring_count:
                    selected_rings = available_rings[:ring_count]
                    self._mark_rings_occupied(selected_rings, batch_start, adult_start_day, adult_end_day, batch_index)
                    
                    return {
                        'area': area.name,
                        'rings': [r.name for r in selected_rings],
                        'rings_count': ring_count,
                        'start_day': adult_start_day,
                        'end_day': adult_end_day,
                    }
        
        raise Exception(f"No available rings for batch {batch_index}!")
    
    def _estimate_harvest_days(self, adult_start_weight_g, target_harvest_kg, tgc, temp_c):
        """Estimate days needed to reach harvest weight."""
        w_start_kg = adult_start_weight_g / 1000
        w_target_kg = target_harvest_kg
        days_needed = (w_target_kg**(1/3) - w_start_kg**(1/3)) / (tgc * temp_c)
        return min(max(days_needed, 1), self.stage_durations['Adult'])
    
    def _check_container_available(self, container_name, start_day, end_day):
        """Check if container is available during specified period."""
        occupied_periods = self.occupancy.get(container_name, [])
        for occ_start, occ_end, _ in occupied_periods:
            if not (end_day <= occ_start or start_day >= occ_end):
                return False
        return True
    
    def _check_rings_available(self, rings, batch_start, adult_start_day, adult_end_day):
        """Check if rings are available during Adult stage."""
        absolute_start = (batch_start - date(2018, 1, 1)).days + adult_start_day
        absolute_end = (batch_start - date(2018, 1, 1)).days + adult_end_day
        
        for ring in rings:
            occupied_periods = self.occupancy.get(ring.name, [])
            for occ_start, occ_end, _ in occupied_periods:
                if not (absolute_end <= occ_start or absolute_start >= occ_end):
                    return False
        return True
    
    def _mark_rings_occupied(self, rings, batch_start, adult_start_day, adult_end_day, batch_index):
        """Mark rings as occupied."""
        absolute_start = (batch_start - date(2018, 1, 1)).days + adult_start_day
        absolute_end = (batch_start - date(2018, 1, 1)).days + adult_end_day
        
        for ring in rings:
            self.occupancy[ring.name].append((absolute_start, absolute_end, batch_index))
    
    def validate_schedule(self):
        """Validate schedule has no conflicts."""
        print("\n" + "="*80)
        print("VALIDATING SCHEDULE")
        print("="*80 + "\n")
        
        conflicts = 0
        
        for container_name, periods in self.occupancy.items():
            sorted_periods = sorted(periods, key=lambda x: x[0])
            
            for i in range(len(sorted_periods) - 1):
                curr_start, curr_end, curr_batch = sorted_periods[i]
                next_start, next_end, next_batch = sorted_periods[i + 1]
                
                if curr_end > next_start:
                    print(f"  ❌ Conflict: {container_name}")
                    print(f"     Batch {curr_batch}: Days {curr_start}-{curr_end}")
                    print(f"     Batch {next_batch}: Days {next_start}-{next_end}")
                    conflicts += 1
        
        if conflicts == 0:
            print(f"✅ Zero conflicts detected")
            print(f"✅ Schedule is valid")
        else:
            print(f"❌ {conflicts} conflicts detected")
        
        return conflicts == 0
    
    def print_statistics(self):
        """Print schedule statistics."""
        print("\n" + "="*80)
        print("SCHEDULE STATISTICS")
        print("="*80 + "\n")
        
        total_batches = len(self.schedule)
        
        # Count by purpose
        active_batches = [b for b in self.schedule if b.get('purpose') != 'completed']
        completed_batches = [b for b in self.schedule if b.get('purpose') == 'completed']
        
        # Count by stage (for active batches)
        stage_counts = defaultdict(int)
        transition_ready = defaultdict(int)
        
        for batch in active_batches:
            duration = batch['duration']
            # Determine current stage based on duration (days elapsed)
            if duration <= 90:
                stage = "Egg&Alevin"
            elif duration <= 180:
                stage = "Fry"
            elif duration <= 270:
                stage = "Parr"
            elif duration <= 360:
                stage = "Smolt"
            elif duration <= 450:
                stage = "Post-Smolt"
            else:
                stage = "Adult"
            
            stage_counts[stage] += 1
            
            # Check if near transition
            purpose = batch.get('purpose', '')
            if 'transition' in purpose:
                transition_ready[stage] += 1
        
        print(f"Total Batches: {total_batches}")
        print(f"  Active (strategic positions): {len(active_batches)}")
        print(f"  Completed (historical): {len(completed_batches)}")
        print()
        
        print(f"Active Batch Distribution by Stage:")
        for stage in ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]:
            count = stage_counts.get(stage, 0)
            trans = transition_ready.get(stage, 0)
            trans_str = f" ({trans} near transition)" if trans > 0 else ""
            print(f"  {stage}: {count} batches{trans_str}")
        print()
        
        # Geography distribution
        faroe = [b for b in self.schedule if 'Faroe' in b['geography']]
        scotland = [b for b in self.schedule if 'Scotland' in b['geography']]
        print(f"Geography Distribution:")
        print(f"  Faroe Islands: {len(faroe)} batches")
        print(f"  Scotland: {len(scotland)} batches")
        print()
        
        # Container utilization
        total_containers = Container.objects.filter(active=True).count()
        unique_containers_used = len(self.occupancy)
        print(f"Container Utilization:")
        print(f"  Total containers: {total_containers}")
        print(f"  Containers allocated: {unique_containers_used}")
        print(f"  Utilization: {unique_containers_used/total_containers*100:.1f}%")
        print()
    
    def save_schedule(self, output_path):
        """Save schedule to YAML file with worker partitioning."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        worker_partitions = self._partition_for_workers(num_workers=14)
        
        # Count active vs completed
        active_count = len([b for b in self.schedule if b.get('purpose') != 'completed'])
        completed_count = len([b for b in self.schedule if b.get('purpose') == 'completed'])
        
        schedule_data = {
            'metadata': {
                'generated_date': str(date.today()),
                'schedule_type': 'UAT_OPTIMIZED',
                'description': 'Lifecycle ladder distribution for comprehensive UAT testing',
                'total_batches': len(self.schedule),
                'active_batches': active_count,
                'completed_batches': completed_count,
                'lifecycle_targets': len(UAT_LIFECYCLE_TARGETS),
                'worker_partitions': worker_partitions,
            },
            'batches': self.schedule
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(schedule_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Schedule saved to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"\n📊 Worker Partitioning:")
        for worker_id, info in worker_partitions.items():
            print(f"   {worker_id}: Batches {info['batch_range']} ({info['count']} batches)")
        print()
    
    def _partition_for_workers(self, num_workers=14):
        """Partition schedule into worker groups."""
        if len(self.schedule) < num_workers:
            return {
                f"worker_{i+1}": {
                    'batch_indices': [i],
                    'batch_range': f"{i+1}",
                    'count': 1
                }
                for i in range(len(self.schedule))
            }
        
        batches_per_worker = len(self.schedule) // num_workers
        remainder = len(self.schedule) % num_workers
        
        partitions = {}
        start_idx = 0
        
        for worker_num in range(num_workers):
            worker_batch_count = batches_per_worker + (1 if worker_num < remainder else 0)
            end_idx = start_idx + worker_batch_count
            
            batch_indices = list(range(start_idx, end_idx))
            
            partitions[f"worker_{worker_num + 1}"] = {
                'batch_indices': batch_indices,
                'batch_range': f"{start_idx + 1}-{end_idx}",
                'count': worker_batch_count
            }
            
            start_idx = end_idx
        
        return partitions


def main():
    parser = argparse.ArgumentParser(
        description='Generate UAT-optimized batch generation schedule'
    )
    parser.add_argument(
        '--completed-batches',
        type=int,
        default=40,
        help='Number of completed batches per geography (default: 40)'
    )
    parser.add_argument(
        '--saturation',
        type=float,
        default=0.85,
        help='Target infrastructure saturation (default: 0.85)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='config/schedule_uat.yaml',
        help='Output YAML file path'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate and validate schedule but don\'t save'
    )
    
    args = parser.parse_args()
    
    print(f"\n🎯 UAT-OPTIMIZED SCHEDULE GENERATION")
    print(f"   Lifecycle targets: {len(UAT_LIFECYCLE_TARGETS)} per geography")
    print(f"   Completed batches: {args.completed_batches} per geography")
    print(f"   Expected total: {(len(UAT_LIFECYCLE_TARGETS) + args.completed_batches) * 2} batches\n")
    
    try:
        planner = UATSchedulePlanner(
            completed_batches_per_geo=args.completed_batches,
            target_saturation=args.saturation
        )
        
        schedule = planner.generate_schedule()
        valid = planner.validate_schedule()
        planner.print_statistics()
        
        if not valid:
            print("\n❌ Schedule validation failed!")
            return 1
        
        if args.dry_run:
            print("\n🏃 DRY RUN MODE - Schedule not saved")
            print(f"   Would save to: {args.output}")
        else:
            planner.save_schedule(args.output)
            print("\n✅ UAT schedule generation complete!")
            print(f"\nExecute with:")
            print(f"  SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py {args.output} --workers 14 --use-partitions")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
