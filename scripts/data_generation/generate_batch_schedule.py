#!/usr/bin/env python3
"""
Batch Generation Schedule Planner

Creates deterministic, conflict-free schedule for test data generation.
Eliminates race conditions by pre-allocating all containers.

Key Features:
- Pre-allocated containers (no runtime queries)
- Variable sea ring allocation (10-20 per batch, default 20)
- Multi-batch area packing (2+ batches per area when beneficial)
- 100% deterministic (same schedule → same data)
- Supports migration testing (reproducible)

Usage:
    # Generate schedule for 250 batches
    python generate_batch_schedule.py --batches 125 --output config/schedule_250.yaml
    
    # Dry run (just validate, don't save)
    python generate_batch_schedule.py --batches 125 --dry-run
"""
import os
import sys
import django
import yaml
import argparse
from datetime import date, timedelta
from pathlib import Path
import random  # Used only for harvest target variation (deterministic via seed in schedule)
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, FreshwaterStation, Hall, Area, Container
from apps.batch.models import LifeCycleStage


class BatchSchedulePlanner:
    """
    Plans deterministic batch generation schedule with optimal container utilization.
    """
    
    def __init__(self, batches_per_geo=125, target_saturation=0.85, stagger_days=5, adult_duration=450):
        self.batches_per_geo = batches_per_geo
        self.target_saturation = target_saturation
        self.stagger_days = stagger_days
        self.adult_duration = adult_duration
        self.occupancy = defaultdict(list)  # {container_name: [(start_day, end_day, batch_id), ...]}
        self.schedule = []

        # Stage durations (from event engine)
        self.stage_durations = {
            'Egg&Alevin': 90,
            'Fry': 90,
            'Parr': 90,
            'Smolt': 90,
            'Post-Smolt': 90,
            'Adult': adult_duration
        }

        # Weight-based harvest parameters (from event engine)
        # Get actual TGC and temperature from database models
        tgc_adult, temp_sea = self._get_adult_tgc_and_temp()
        self.harvest_targets = {
            'min_weight_kg': 4.5,  # Minimum harvest weight
            'max_weight_kg': 6.5,  # Maximum harvest weight
            'adult_start_weight_g': 450,  # Weight when entering Adult stage
            'tgc_adult': tgc_adult,  # Adult stage TGC value from database
            'temp_sea_c': temp_sea   # Sea temperature from database
        }
    
    def _get_adult_tgc_and_temp(self):
        """
        Get actual Adult stage TGC value and sea temperature from database models.
        Falls back to defaults if models not initialized.
        
        Returns:
            Tuple of (tgc_value, temperature_c)
        """
        try:
            from apps.scenario.models import TGCModel, TemperatureProfile, TemperatureReading
            from django.db.models import Avg
            
            # Get any TGC model (they should be similar for Adult stage)
            tgc_model = TGCModel.objects.first()
            
            if tgc_model:
                tgc_value = float(tgc_model.tgc_value)
            else:
                tgc_value = 0.0031  # Fallback to standard value
            
            # Get average sea temperature from any temperature profile
            temp_profile = TemperatureProfile.objects.filter(
                name__icontains='Sea'
            ).first()
            
            if temp_profile:
                avg_temp = TemperatureReading.objects.filter(
                    profile=temp_profile
                ).aggregate(avg=Avg('temperature'))['avg']
                temp_c = float(avg_temp) if avg_temp else 9.0
            else:
                temp_c = 9.0  # Fallback
            
            print(f"  Using TGC from database: {tgc_value}")
            print(f"  Using sea temp from database: {temp_c:.1f}°C")
            
            return tgc_value, temp_c
            
        except Exception as e:
            print(f"  ⚠ Could not load TGC/temp from database: {e}")
            print(f"  Using fallback values: TGC=0.0031, Temp=9.0°C")
            return 0.0031, 9.0  # Safe defaults
    
    def generate_schedule(self):
        """Generate complete deterministic schedule."""
        print("\n" + "="*80)
        print("BATCH GENERATION SCHEDULE PLANNER")
        print("="*80 + "\n")
        
        # Calculate start date (historical)
        today = date.today()
        # Interleaved batches (F, S, F, S...) with global stagger
        total_batches = self.batches_per_geo * 2
        span_days = (total_batches - 1) * self.stagger_days
        buffer_days = 50
        days_back = span_days + buffer_days
        start_date = today - timedelta(days=days_back)
        years_back = days_back / 365
        
        print(f"Configuration:")
        print(f"  Batches per geography: {self.batches_per_geo}")
        print(f"  Total batches: {total_batches}")
        print(f"  Start date: {start_date} ({years_back:.1f} years ago)")
        print(f"  Today: {today}")
        print(f"  Global Stagger: {self.stagger_days} days (Effective per-geo: {self.stagger_days*2} days)")
        print(f"  Adult stage: {self.adult_duration} days")
        print(f"  Target saturation: {self.target_saturation*100:.0f}%")
        print()
        
        # Load infrastructure
        self._load_infrastructure()
        
        # Interleaved generation
        # Even indices: Faroe Islands
        # Odd indices: Scotland
        
        geos = ["Faroe Islands", "Scotland"]
        
        for i in range(total_batches):
            geo_idx = i % 2
            geo_name = geos[geo_idx]
            batch_index_in_geo = i // 2
            
            batch_start = start_date + timedelta(days=i * self.stagger_days)
            days_since_start = (today - batch_start).days
            total_lifecycle_days = sum(self.stage_durations.values())
            duration = min(total_lifecycle_days, days_since_start)  # Date-bounded
            
            geo_data = self.infrastructure[geo_name]
            
            try:
                batch_config = self._plan_single_batch(
                    geo_name=geo_name,
                    geo_data=geo_data,
                    batch_index=batch_index_in_geo,
                    batch_start=batch_start,
                    duration=duration
                )
                
                self.schedule.append(batch_config)
                
                # Show progress
                if i < 6 or i >= total_batches - 4:
                    total_lifecycle = sum(self.stage_durations.values())
                    status = "Completed" if duration >= total_lifecycle else "Active"
                    rings = batch_config['sea']['rings_count'] if batch_config.get('sea') else 0
                    rings_str = f"{rings:2d} rings" if rings > 0 else "no sea   "
                    print(f"  Batch {i+1:3d} ({geo_name[:2]}): {batch_start} | {duration:3d} days | "
                          f"{rings_str} | {status}")
                elif i == 6:
                    print(f"  ...")
            
            except Exception as e:
                print(f"❌ Failed to plan batch {i+1} ({geo_name}): {e}")
                # Continue to try planning others or raise?
                # Raising is better to fail early
                raise e

        return self.schedule
    
    def _load_infrastructure(self):
        """Load and organize infrastructure data."""
        print("Loading infrastructure...")
        
        self.infrastructure = {}
        
        for geo in Geography.objects.filter(name__in=['Faroe Islands', 'Scotland']):
            # Filter to production stations only (FI-FW-* and S-FW-* patterns)
            prefix = 'FI-FW' if geo.name == 'Faroe Islands' else 'S-FW'
            stations = list(FreshwaterStation.objects.filter(
                geography=geo,
                name__startswith=prefix
            ).order_by('name'))
            
            areas = list(Area.objects.filter(
                geography=geo
            ).order_by('name'))
            
            self.infrastructure[geo.name] = {
                'geography': geo,
                'stations': stations,
                'areas': areas,
            }
            
            print(f"  {geo.name}: {len(stations)} stations, {len(areas)} sea areas")
        
        print()
    
    def _plan_single_batch(self, geo_name, geo_data, batch_index, batch_start, duration):
        """Plan container allocation for single batch with weight-based harvest estimation."""

        # For weight-based planning: Estimate actual harvest timing
        # Use worst-case scenario (slowest growth to highest weight target)
        harvest_target_kg = self.harvest_targets['max_weight_kg']  # Plan for maximum weight (longest duration)
        estimated_harvest_days = self._estimate_harvest_days(
            adult_start_weight_g=self.harvest_targets['adult_start_weight_g'],
            target_harvest_kg=harvest_target_kg,
            tgc=self.harvest_targets['tgc_adult'],
            temp_c=self.harvest_targets['temp_sea_c']
        )

        # Use the longer of: date-bounded duration OR estimated harvest duration
        # This ensures containers are planned for worst-case occupation
        effective_duration = max(duration, estimated_harvest_days + 450)  # +450 for full lifecycle

        # Allocate freshwater containers (10 per stage)
        # Each stage can use ANY available hall (doesn't need to be same station)
        fw_containers = self._allocate_freshwater_independent(
            geo_data['stations'],
            batch_index,
            batch_start,
            effective_duration  # Use conservative duration for planning
        )

        # Get station name from first allocated hall (for batch metadata)
        first_hall_name = list(fw_containers.values())[0]['hall'] if fw_containers else None
        station_name = first_hall_name.rsplit('-Hall-', 1)[0] if first_hall_name else geo_data['stations'][0].name

        # Deterministic sea area selection (round-robin)
        area_idx = batch_index % len(geo_data['areas'])

        # Allocate sea rings (20 per batch, full area utilization)
        sea_containers = self._allocate_sea_rings(
            geo_data['areas'],
            area_idx,
            batch_index,
            batch_start,
            effective_duration  # Conservative planning
        )

        # Generate batch config - include harvest target for execution
        batch_id = f"{geo_data['geography'].code if hasattr(geo_data['geography'], 'code') else geo_name[:3].upper()}-{batch_start.year}-{batch_index+1:03d}"
        # Deterministic egg count based on batch index (eliminates random seed)
        eggs = 3000000 + ((batch_index * 123456) % 800000)  # Range: 3.0M - 3.8M
        actual_harvest_target = self._get_random_harvest_target()  # Random target for execution

        return {
            'batch_id': batch_id,
            'start_date': str(batch_start),
            'eggs': eggs,
            'duration': duration,  # Actual execution duration
            'effective_duration': effective_duration,  # Conservative planning duration
            'harvest_target_kg': actual_harvest_target,  # For execution (matches engine)
            'geography': geo_name,
            'station': station_name,
            'freshwater': fw_containers,
            'sea': sea_containers,
        }
    
    def _allocate_freshwater_independent(self, all_stations, batch_index, batch_start, duration):
        """
        Allocate freshwater halls independently per stage.
        Each stage can use ANY available hall (not restricted to single station).
        
        This maximizes packing density and prevents artificial station bottlenecks.
        """
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
            
            # Only allocate if this stage is reached (date-bounded)
            if stage_start_day >= duration:
                continue
            
            # Find ANY hall of this type (across all stations) with 10 available containers
            allocated_hall = None
            allocated_containers = []
            
            for station in all_stations:
                hall_name = f"{station.name}-Hall-{hall_letter}"
                containers = list(Container.objects.filter(hall__name=hall_name).order_by('name'))
                
                if len(containers) < 10:
                    continue
                
                # Check availability
                absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
                absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
                
                # Find 10 available containers in this hall
                available = []
                for container in containers:
                    if self._check_container_available(container.name, absolute_start, absolute_end):
                        available.append(container)
                    if len(available) == 10:
                        break
                
                if len(available) == 10:
                    # Found a hall with capacity!
                    allocated_hall = hall_name
                    allocated_containers = available
                    
                    # Mark as occupied
                    for container in available:
                        self.occupancy[container.name].append((absolute_start, absolute_end, batch_index))
                    
                    break
            
            if not allocated_hall:
                raise Exception(
                    f"No {hall_letter} hall has 10 available containers for batch {batch_index} "
                    f"starting {batch_start}! Capacity exceeded - reduce batch count or increase stagger."
                )
            
            allocations[stage_name.lower().replace('&', '_')] = {
                'hall': allocated_hall,
                'containers': [c.name for c in allocated_containers],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration)
            }
        
        return allocations
    
    def _allocate_freshwater(self, station, batch_index, batch_start, duration):
        """
        Allocate freshwater containers for all stages.
        
        Key insight: Each batch occupies ONE hall per stage sequentially.
        A station can host 5 batches simultaneously (1 per hall).
        
        With 90-day stages and 30-day stagger, each hall hosts ~3 batches over time.
        """
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
            
            # Only allocate if this stage is reached (date-bounded)
            if stage_start_day >= duration:
                continue
            
            hall_name = f"{station.name}-Hall-{hall_letter}"
            
            # Get all containers in this hall
            containers = list(Container.objects.filter(
                hall__name=hall_name
            ).order_by('name'))
            
            if len(containers) < 10:
                raise Exception(f"Hall {hall_name} has only {len(containers)} containers (need 10)")
            
            # Check hall availability during this stage period
            absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
            absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
            
            # Find 10 available containers in this hall
            available = []
            for container in containers:
                if self._check_container_available(container.name, absolute_start, absolute_end):
                    available.append(container)
                if len(available) == 10:
                    break
            
            if len(available) < 10:
                raise Exception(f"Hall {hall_name} doesn't have 10 available containers for batch starting {batch_start}")
            
            # Mark as occupied
            for container in available:
                self.occupancy[container.name].append((absolute_start, absolute_end, batch_index))
            
            allocations[stage_name.lower().replace('&', '_')] = {
                'hall': hall_name,
                'containers': [c.name for c in available],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration)
            }
        
        return allocations
    
    def _estimate_harvest_days(self, adult_start_weight_g, target_harvest_kg, tgc, temp_c):
        """
        Estimate days needed to reach harvest weight from adult stage entry.

        Uses the same TGC formula as the event engine:
        W_final^(1/3) = W_initial^(1/3) + TGC * temp * days

        Args:
            adult_start_weight_g: Weight when entering adult stage (g)
            target_harvest_kg: Target harvest weight (kg)
            tgc: Thermal growth coefficient
            temp_c: Temperature in Celsius

        Returns:
            Days needed to reach target weight (capped at adult_duration)
        """
        w_start_kg = adult_start_weight_g / 1000  # Convert to kg
        w_target_kg = target_harvest_kg

        # TGC formula: W_target^(1/3) = W_start^(1/3) + TGC * temp * days
        # Solve for days: days = (W_target^(1/3) - W_start^(1/3)) / (TGC * temp)
        days_needed = (w_target_kg**(1/3) - w_start_kg**(1/3)) / (tgc * temp_c)

        # Cap at maximum adult duration (some batches may not reach target weight)
        return min(max(days_needed, 1), self.adult_duration)

    def _get_random_harvest_target(self):
        """Get random harvest target weight (4.5-6.5kg) matching event engine."""
        return random.uniform(
            self.harvest_targets['min_weight_kg'],
            self.harvest_targets['max_weight_kg']
        )

    def _check_container_available(self, container_name, start_day, end_day):
        """Check if container is available during specified period."""
        occupied_periods = self.occupancy.get(container_name, [])
        for occ_start, occ_end, _ in occupied_periods:
            # Check for overlap
            if not (end_day <= occ_start or start_day >= occ_end):
                return False  # Conflict detected
        return True  # Available
    
    def _select_best_station(self, stations, batch_start, duration):
        """
        Select station with available halls for this batch's lifecycle.
        
        Allows multiple batches per station (up to 5 simultaneous, 1 per hall).
        """
        # Try each station
        for station in stations:
            # Check if this station has available halls for all needed stages
            if self._station_has_capacity(station, batch_start, duration):
                return station
        
        # Fallback: just use round-robin (shouldn't happen with proper capacity)
        raise Exception(f"No station has capacity for batch starting {batch_start}! Reduce batch count.")
    
    def _station_has_capacity(self, station, batch_start, duration):
        """
        Check if station has at least 10 available containers in each needed hall.
        """
        stage_configs = [
            ('A', 0, 90),      # Egg&Alevin
            ('B', 90, 180),    # Fry
            ('C', 180, 270),   # Parr
            ('D', 270, 360),   # Smolt
            ('E', 360, 450)    # Post-Smolt
        ]
        
        for hall_letter, stage_start, stage_end in stage_configs:
            if stage_start >= duration:
                continue  # Stage not reached
            
            hall_name = f"{station.name}-Hall-{hall_letter}"
            containers = list(Container.objects.filter(hall__name=hall_name).order_by('name'))
            
            if len(containers) < 10:
                return False  # Hall doesn't have 10 containers
            
            # Check if 10 containers are available during this stage
            absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start
            absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end, duration)
            
            available_count = sum(1 for c in containers if self._check_container_available(c.name, absolute_start, absolute_end))
            
            if available_count < 10:
                return False  # Not enough available containers in this hall
        
        return True  # Station has capacity for all needed stages
    
    def _allocate_sea_rings(self, areas, preferred_area_idx, batch_index, batch_start, duration):
        """
        Allocate sea rings with adaptive allocation (8-20 rings per batch).
        
        Strategy for high saturation (5-day stagger):
        - Try 8 rings first (allows 107 batches @ 860 rings)
        - Fall back to 10, 12, 15, or 20 based on availability
        - Adaptive: takes what's available to maximize saturation
        """
        
        # Adult stage timing
        adult_start_day = sum([90, 90, 90, 90, 90])  # After all FW stages
        adult_end_day = min(adult_start_day + self.adult_duration, duration)
        
        # Only allocate if Adult stage is reached
        if duration < adult_start_day:
            return None  # Batch doesn't reach Adult stage
        
        # Try preferred area first (round-robin), then all others
        for offset in range(len(areas)):
            area_idx = (preferred_area_idx + offset) % len(areas)
            area = areas[area_idx]
            
            # Get all 20 rings in this area
            rings = list(Container.objects.filter(area=area).order_by('name'))
            
            if len(rings) != 20:
                continue  # Skip areas that don't have 20 rings
            
            # Try to allocate rings: 8 → 10 → 12 → 15 → 20 (adaptive, prefer smaller)
            # Also try minimum viable (6 rings) as last resort
            for ring_count in [8, 10, 12, 15, 20, 6]:
                available_rings = []
                for ring in rings:
                    if self._check_rings_available([ring], batch_start, adult_start_day, adult_end_day):
                        available_rings.append(ring)
                    if len(available_rings) == ring_count:
                        break
                
                if len(available_rings) >= ring_count:
                    # Found enough rings! Use exactly ring_count
                    selected_rings = available_rings[:ring_count]
                    self._mark_rings_occupied(selected_rings, batch_start, adult_start_day, adult_end_day, batch_index)
                    
                    note = None
                    if ring_count == 20:
                        note = 'Full area'
                    elif ring_count >= 15:
                        note = f'Large allocation ({ring_count}/20 rings)'
                    elif ring_count >= 10:
                        note = f'Standard allocation ({ring_count}/20 rings)'
                    else:
                        note = f'Minimal allocation ({ring_count}/20 rings)'
                    
                    return {
                        'area': area.name,
                        'rings': [r.name for r in selected_rings],
                        'rings_count': ring_count,
                        'start_day': adult_start_day,
                        'end_day': adult_end_day,
                        'note': note
                    }
        
        # No space found - provide helpful diagnostic
        total_rings = sum(len(list(Container.objects.filter(area=a))) for a in areas)
        occupied_count = sum(1 for ring_name in self.occupancy.keys() 
                           if any(area.name in ring_name for area in areas))
        
        raise Exception(
            f"No available rings for batch {batch_index}! "
            f"Total rings: {total_rings}, Occupied: {occupied_count}. "
            f"Consider reducing batch count or increasing stagger."
        )
    
    def _check_rings_available(self, rings, batch_start, adult_start_day, adult_end_day):
        """Check if rings are available during Adult stage period."""
        absolute_start = (batch_start - date(2018, 1, 1)).days + adult_start_day
        absolute_end = (batch_start - date(2018, 1, 1)).days + adult_end_day
        
        for ring in rings:
            occupied_periods = self.occupancy.get(ring.name, [])
            for occ_start, occ_end, _ in occupied_periods:
                # Check for overlap
                if not (absolute_end <= occ_start or absolute_start >= occ_end):
                    return False  # Conflict detected
        
        return True  # All rings available
    
    def _mark_rings_occupied(self, rings, batch_start, adult_start_day, adult_end_day, batch_index):
        """Mark rings as occupied in occupancy tracker."""
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
        
        # Check for container overlaps
        for container_name, periods in self.occupancy.items():
            # Sort by start time
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
            print(f"❌ Reduce batch count or adjust allocation")
        
        return conflicts == 0
    
    def print_statistics(self):
        """Print schedule statistics."""
        print("\n" + "="*80)
        print("SCHEDULE STATISTICS")
        print("="*80 + "\n")
        
        total_batches = len(self.schedule)
        
        # Ring allocation distribution
        ring_counts = [b['sea']['rings_count'] for b in self.schedule if b.get('sea')]
        full_area_batches = sum(1 for r in ring_counts if r == 20)
        partial_batches = sum(1 for r in ring_counts if r == 10)
        
        print(f"Total Batches: {total_batches}")
        print(f"  Faroe Islands: {sum(1 for b in self.schedule if 'Faroe' in b['geography'])}")
        print(f"  Scotland: {sum(1 for b in self.schedule if 'Scotland' in b['geography'])}")
        print()
        
        print(f"Sea Ring Allocation:")
        print(f"  Full area (20 rings): {full_area_batches} batches")
        print(f"  Partial area (10 rings): {partial_batches} batches")
        if ring_counts:
            avg_rings = sum(ring_counts) / len(ring_counts)
            total_rings_used = sum(ring_counts)
            print(f"  Average rings/batch: {avg_rings:.1f}")
            print(f"  Total ring occupancy: {total_rings_used} ring-periods")
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
        
        # Partition schedule into worker groups (chronological chunks)
        # Each worker gets a contiguous time slice with no overlap
        worker_partitions = self._partition_for_workers(num_workers=14)
        
        schedule_data = {
            'metadata': {
                'generated_date': str(date.today()),
                'total_batches': len(self.schedule),
                'batches_per_geography': self.batches_per_geo,
                'target_saturation': self.target_saturation,
                'stagger_days': self.stagger_days,
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
            print(f"   Worker {worker_id}: Batches {info['batch_range']} ({info['count']} batches)")
        print()
    
    def _partition_for_workers(self, num_workers=14):
        """
        Partition schedule into worker groups based on chronological time slices.
        
        Key insight: Batches that start far apart in time won't compete for containers.
        Group batches into time windows and assign each window to a worker.
        
        Returns dict mapping worker_id to batch indices.
        """
        if len(self.schedule) < num_workers:
            # Fewer batches than workers, one batch per worker
            return {
                f"worker_{i+1}": {
                    'batch_indices': [i],
                    'batch_range': f"{i+1}",
                    'count': 1
                }
                for i in range(len(self.schedule))
            }
        
        # Calculate batches per worker (roughly equal distribution)
        batches_per_worker = len(self.schedule) // num_workers
        remainder = len(self.schedule) % num_workers
        
        partitions = {}
        start_idx = 0
        
        for worker_num in range(num_workers):
            # Give first 'remainder' workers one extra batch
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
        description='Generate deterministic batch generation schedule'
    )
    parser.add_argument(
        '--batches',
        type=int,
        default=None,
        help='Number of batches per geography (if not specified, calculated from --years and --stagger)'
    )
    parser.add_argument(
        '--years',
        type=float,
        default=4.0,
        help='Years of historical data to generate (default: 4.0)'
    )
    parser.add_argument(
        '--saturation',
        type=float,
        default=0.85,
        help='Target infrastructure saturation (default: 0.85)'
    )
    parser.add_argument(
        '--stagger',
        type=int,
        default=5,
        help='Days between batch starts (default: 5 for high saturation)'
    )
    parser.add_argument(
        '--adult-duration',
        type=int,
        default=450,
        help='Adult stage duration in days (default: 450)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='config/batch_generation_schedule.yaml',
        help='Output YAML file path'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate and validate schedule but don\'t save'
    )
    
    args = parser.parse_args()
    
    # Calculate batches_per_geo from years and stagger if not explicitly provided
    if args.batches is None:
        # Calculate maximum batches from BOTH time and infrastructure constraints
        total_days = int(args.years * 365)
        
        # Time constraint: How many batches fit in the timespan?
        total_batch_starts = total_days // args.stagger
        max_from_time = total_batch_starts // 2  # Per geography
        
        # Infrastructure constraint: Sea rings are the bottleneck
        # Scotland: 400 rings, Faroe: 460 rings (Scotland is limiting)
        # At 85% saturation with 8 rings/batch: (400 × 0.85) / 8 = 42 batches in Adult simultaneously
        # With 450-day Adult stage and 5-day stagger: 450/5 = 90 batches would overlap
        # This is IMPOSSIBLE - so we need to find the sustainable batch count
        
        # Conservative estimate: Start with half of time-based max and let planner validate
        max_from_infrastructure = max_from_time // 2
        
        # Use the lesser of the two constraints
        batches_per_geo = min(max_from_time, max_from_infrastructure)
        
        print(f"\n📊 Auto-calculating batch count from constraints:")
        print(f"   Target: {args.years} years, {args.saturation*100:.0f}% saturation, {args.stagger}-day stagger")
        print(f"   Time constraint: {max_from_time} batches/geo (fits in {total_days} days)")
        print(f"   Infrastructure constraint: {max_from_infrastructure} batches/geo (400 Scotland rings)")
        print(f"   Limiting factor: {'TIME' if batches_per_geo == max_from_time else 'INFRASTRUCTURE'}")
        print(f"   Selected: {batches_per_geo} batches per geography")
        print(f"   Total batches: {batches_per_geo * 2}\n")
    else:
        batches_per_geo = args.batches
        calculated_years = (batches_per_geo * 2 * args.stagger) / 365
        print(f"\n📊 Using specified batch count:")
        print(f"   Batches per geography: {batches_per_geo}")
        print(f"   Total batches: {batches_per_geo * 2}")
        print(f"   With {args.stagger}-day stagger: ~{calculated_years:.1f} years of data\n")
    
    try:
        planner = BatchSchedulePlanner(
            batches_per_geo=batches_per_geo,
            target_saturation=args.saturation,
            stagger_days=args.stagger,
            adult_duration=args.adult_duration
        )
        
        # Generate schedule
        schedule = planner.generate_schedule()
        
        # Validate
        valid = planner.validate_schedule()
        
        # Statistics
        planner.print_statistics()
        
        if not valid:
            print("\n❌ Schedule validation failed!")
            return 1
        
        # Save (unless dry-run)
        if args.dry_run:
            print("\n🏃 DRY RUN MODE - Schedule not saved")
            print(f"   Would save to: {args.output}")
        else:
            planner.save_schedule(args.output)
            print("\n✅ Schedule generation complete!")
            print(f"\nExecute with:")
            print(f"  python scripts/data_generation/execute_batch_schedule.py {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())