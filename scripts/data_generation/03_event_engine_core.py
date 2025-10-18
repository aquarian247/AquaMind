#!/usr/bin/env python3
"""
AquaMind Phase 3: Core Event Generation Logic
Compact implementation focusing on essential features
"""
import os, sys, django, json, random, argparse, numpy as np
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.batch.models import *
from apps.infrastructure.models import *
from apps.environmental.models import *
from apps.inventory.models import *
from apps.health.models import *
from apps.harvest.models import HarvestEvent, HarvestLot, ProductGrade

User = get_user_model()

PROGRESS_DIR = Path(project_root) / 'aquamind' / 'docs' / 'progress' / 'test_data'
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

class EventEngine:
    def __init__(self, start_date, eggs, geography, duration=650):
        self.start_date = start_date
        self.current_date = start_date
        self.initial_eggs = eggs
        self.duration = duration
        self.geography_name = geography
        self.stats = {'days': 0, 'env': 0, 'feed': 0, 'mort': 0, 'growth': 0, 'purchases': 0, 'lice': 0}
        self.current_stage_start_day = 0
        # Realistic lifecycle stage durations (total: ~900 days)
        self.stage_durations = {
            'Egg&Alevin': 90,   # 90 days, no feed
            'Fry': 90,          # 90 days
            'Parr': 90,         # 90 days
            'Smolt': 90,        # 90 days
            'Post-Smolt': 90,   # 90 days
            'Adult': 450        # 450 days (major change from implicit infinite)
        }
        
    def init(self):
        print(f"\n{'='*80}")
        print("Initializing Event Engine")
        print(f"{'='*80}\n")
        
        self.geo = Geography.objects.get(name=self.geography_name)
        self.station = FreshwaterStation.objects.filter(geography=self.geo).first()
        self.sea_area = Area.objects.filter(geography=self.geo).first()
        self.species = Species.objects.get(name="Atlantic Salmon")
        self.stages = list(LifeCycleStage.objects.filter(species=self.species).order_by('order'))
        self.user = User.objects.filter(username='system_admin').first() or User.objects.first()
        self.env_params = list(EnvironmentalParameter.objects.all())
        
        print(f"✓ Geography: {self.geo.name}")
        print(f"✓ Station: {self.station.name}")
        print(f"✓ Sea Area: {self.sea_area.name}")
        print(f"✓ Duration: {self.duration} days\n")
    
    def find_available_containers(self, hall=None, geography=None, count=10):
        """
        Find available (unoccupied) containers in a hall or across all sea areas in a geography.
        Thread-safe for parallel execution using row-level locks.
        
        Args:
            hall: Hall object to search in (for freshwater stages)
            geography: Geography object to search ALL sea areas (for Adult stage)
            count: Number of containers needed
            
        Returns:
            List of available Container objects, or empty list if insufficient
        """
        from django.db import transaction
        
        # CRITICAL: Must be called within an atomic transaction to use select_for_update
        # Get occupied container IDs with row-level lock to prevent concurrent access
        occupied_ids = set(
            BatchContainerAssignment.objects.select_for_update(skip_locked=True).filter(
                is_active=True
            ).values_list('container_id', flat=True)
        )
        
        # Find available containers with lock to prevent race condition
        if hall:
            available = Container.objects.select_for_update(skip_locked=True).filter(
                hall=hall,
                active=True
            ).exclude(
                id__in=occupied_ids
            ).order_by('name')[:count * 2]  # Get extra to account for simultaneous claims
        elif geography:
            # For sea stage: search across ALL sea areas in this geography
            available = Container.objects.select_for_update(skip_locked=True).filter(
                area__geography=geography,
                active=True
            ).exclude(
                id__in=occupied_ids
            ).order_by('area__name', 'name')[:count * 2]  # Get extra to account for simultaneous claims
        else:
            return []
        
        available_list = list(available)[:count]  # Take only what we need
        
        if len(available_list) < count:
            # Not enough available containers
            return []
        
        return available_list
        
    def create_batch(self):
        print(f"{'='*80}")
        print("Creating Batch")
        print(f"{'='*80}\n")
        
        prefix = "FI" if "Faroe" in self.geography_name else "SCO"
        year = self.start_date.year
        existing = Batch.objects.filter(batch_number__startswith=f"{prefix}-{year}").count()
        batch_name = f"{prefix}-{year}-{existing + 1:03d}"
        
        self.batch = Batch.objects.create(
            batch_number=batch_name,
            species=self.species,
            lifecycle_stage=self.stages[0],
            start_date=self.start_date,
            notes=f"Generated {datetime.now().date()}"
        )
        
        hall_a = Hall.objects.filter(freshwater_station=self.station, name__contains="-Hall-A").first()
        
        # Use database transaction with row-level locking to prevent race conditions
        from django.db import transaction
        
        with transaction.atomic():
            containers = self.find_available_containers(hall=hall_a, count=10)
            
            if not containers:
                raise Exception(f"Insufficient available containers in {hall_a.name}. Need 10, infrastructure may be saturated.")
            
            eggs_per = self.initial_eggs // 10
            
            self.assignments = []
            for cont in containers:
                a = BatchContainerAssignment.objects.create(
                    batch=self.batch, container=cont, lifecycle_stage=self.stages[0],
                    assignment_date=self.start_date, population_count=eggs_per,
                    avg_weight_g=Decimal('0.1'), biomass_kg=Decimal(str(eggs_per * 0.1 / 1000)),
                    is_active=True
                )
                self.assignments.append(a)
        
        print(f"✓ Batch: {self.batch.batch_number}")
        print(f"✓ {len(self.assignments)} assignments ({eggs_per:,} eggs each)\n")
        
    def process_day(self):
        self.assignments = list(BatchContainerAssignment.objects.filter(batch=self.batch, is_active=True))
        if not self.assignments: return
        
        # Check for stage transition BEFORE processing events
        self.check_stage_transition()
        
        # 6 readings per day (optimized bulk insert)
        self.env_readings_bulk([6, 8, 10, 14, 16, 18])
        self.feed_events(8)
        self.mortality_check()
        self.feed_events(16)
        self.growth_update()
        self.lice_update()  # Weekly lice sampling (Adult stage only)
        
        if self.stats['days'] % 30 == 0:
            self.health_journal()
        
        self.stats['days'] += 1
        if self.stats['days'] % 50 == 0:
            print(f"  Day {self.stats['days']}/{self.duration}: {self.batch.lifecycle_stage.name}, "
                  f"Pop: {sum(a.population_count for a in self.assignments):,}, "
                  f"Avg: {self.assignments[0].avg_weight_g}g")
        
    def env_readings_bulk(self, hours):
        """Bulk create environmental readings for performance (M4 Max optimized)"""
        readings = []
        for hour in hours:
            for a in self.assignments:
                for param in self.env_params:
                    val = self.gen_env_value(param.name)
                    sensor = a.container.sensors.filter(sensor_type=param.name).first()
                    if sensor:
                        readings.append(EnvironmentalReading(
                            reading_time=timezone.make_aware(datetime.combine(self.current_date, time(hour=hour))),
                            sensor=sensor, parameter=param, value=val,
                            container=a.container, batch=self.batch, is_manual=False
                        ))
        
        # Bulk insert (100x faster than individual creates)
        if readings:
            EnvironmentalReading.objects.bulk_create(readings, batch_size=500)
            self.stats['env'] += len(readings)
    
    def gen_env_value(self, name):
        vals = {'Dissolved Oxygen': 90, 'CO2': 8, 'pH': 7.2, 'Temperature': 12,
                'NO2': 0.05, 'NO3': 20, 'NH4': 0.01}
        base = vals.get(name, 10)
        return Decimal(str(round(base + base * 0.1 * (random.random() * 2 - 1), 2)))
    
    def feed_events(self, hour):
        for a in self.assignments:
            if 'Egg' in a.lifecycle_stage.name: continue
            
            biomass = float(a.biomass_kg)
            if biomass <= 0: continue
            
            rates = {'Fry': 3, 'Parr': 2.5, 'Smolt': 2, 'Post-Smolt': 1.5, 'Adult': 1}
            rate = rates.get(a.lifecycle_stage.name, 1.5)
            amount = biomass * (rate / 100) / 2
            
            feed = self.get_feed(a.lifecycle_stage)
            fc = FeedContainer.objects.filter(hall=a.container.hall).first() if a.container.hall else \
                 FeedContainer.objects.filter(area=a.container.area).first()
            
            if fc and feed:
                cost = self.consume_fifo(fc, feed, amount)
                FeedingEvent.objects.create(
                    batch=self.batch, container=a.container, batch_assignment=a, feed=feed,
                    feeding_date=self.current_date, feeding_time=time(hour=hour),
                    amount_kg=Decimal(str(amount)), batch_biomass_kg=a.biomass_kg,
                    feeding_percentage=Decimal(str(amount / biomass * 100)) if biomass > 0 else Decimal('0'),
                    feed_cost=cost, method='AUTOMATIC'
                )
                self.stats['feed'] += 1
    
    def get_feed(self, stage):
        feeds = {'Fry': 'Starter Feed 0.5mm', 'Parr': 'Starter Feed 1.0mm',
                 'Smolt': 'Grower Feed 2.0mm', 'Post-Smolt': 'Grower Feed 3.0mm',
                 'Adult': 'Finisher Feed 4.5mm'}
        return Feed.objects.filter(name=feeds.get(stage.name, 'Starter Feed 0.5mm')).first()
    
    def consume_fifo(self, fc, feed, amt):
        stocks = FeedContainerStock.objects.filter(
            feed_container=fc, feed_purchase__feed=feed, quantity_kg__gt=0
        ).order_by('entry_date')
        
        rem = Decimal(str(amt))
        cost = Decimal('0')
        
        for s in stocks:
            if rem <= 0: break
            cons = min(s.quantity_kg, rem)
            cost += cons * s.feed_purchase.cost_per_kg
            s.quantity_kg -= cons
            s.save()
            rem -= cons
        
        # Check reorder (only if below 20% capacity)
        total = FeedContainerStock.objects.filter(
            feed_container=fc, feed_purchase__feed=feed
        ).aggregate(t=django.db.models.Sum('quantity_kg'))['t'] or Decimal('0')
        
        threshold = fc.capacity_kg * Decimal('0.2')
        
        if total < threshold:
            # Calculate reorder amount (don't exceed capacity)
            reorder_qty = min(fc.capacity_kg - total, fc.capacity_kg * Decimal('0.8'))
            if reorder_qty > 100:  # Only reorder if meaningful amount
                self.reorder_feed(fc, feed, reorder_qty)
        
        return cost
    
    def reorder_feed(self, fc, feed, qty):
        p = FeedPurchase.objects.create(
            feed=feed, purchase_date=self.current_date, supplier='BioMar',
            batch_number=f"AUTO-{self.current_date.strftime('%Y%m%d')}-{random.randint(1000,9999)}",
            quantity_kg=qty, cost_per_kg=Decimal('2.30'),
            expiry_date=self.current_date + timedelta(days=365)
        )
        FeedContainerStock.objects.create(
            feed_container=fc, feed_purchase=p, quantity_kg=qty,
            entry_date=timezone.make_aware(datetime.combine(
                self.current_date + timedelta(days=3), datetime.min.time()
            ))
        )
        self.stats['purchases'] += 1
    
    def mortality_check(self):
        rates = {'Egg&Alevin': 0.0015, 'Fry': 0.0005, 'Parr': 0.0003,
                 'Smolt': 0.0002, 'Post-Smolt': 0.00015, 'Adult': 0.0001}
        
        for a in self.assignments:
            rate = rates.get(a.lifecycle_stage.name, 0.0001)
            exp = a.population_count * rate
            act = np.random.poisson(exp)
            
            if act > 0:
                biomass_lost = Decimal(str(act * float(a.avg_weight_g) / 1000))
                
                MortalityEvent.objects.create(
                    batch=self.batch,
                    event_date=self.current_date,
                    count=act,
                    biomass_kg=biomass_lost,
                    cause='UNKNOWN',
                    description=f'Daily check {a.lifecycle_stage.name}'
                )
                a.population_count -= act
                a.biomass_kg = Decimal(str(a.population_count * float(a.avg_weight_g) / 1000))
                a.save()
                self.stats['mort'] += 1
    
    def growth_update(self):
        # TGC values from industry data (per 1000 degree-days, so divide by 1000)
        # Egg&Alevin: no growth (feed from yolk sac)
        # Fry: 2.0-2.5, Parr: 2.5-3.0, Smolt: 2.5-3.0
        # Post-Smolt: 3.0-3.5, Adult: 3.0-3.2
        tgc = {
            'Egg&Alevin': 0,
            'Fry': 0.00225,      # 2.25/1000
            'Parr': 0.00275,     # 2.75/1000
            'Smolt': 0.00275,    # 2.75/1000
            'Post-Smolt': 0.00325,  # 3.25/1000
            'Adult': 0.0031      # 3.1/1000
        }
        
        for a in self.assignments:
            t = tgc.get(a.lifecycle_stage.name, 0)
            if t == 0:  # No growth for Egg&Alevin
                continue
            
            # Temperature varies by stage (freshwater ~12°C, seawater ~8-10°C)
            if a.lifecycle_stage.name in ['Fry', 'Parr', 'Smolt']:
                temp = 12.0  # Freshwater
            else:
                temp = 9.0   # Seawater
            
            w = float(a.avg_weight_g)
            
            # TGC formula: W_final^(1/3) = W_initial^(1/3) + (TGC * temp * days) / 1000
            # Already divided TGC by 1000, so: W_f^(1/3) = W_i^(1/3) + TGC * temp * days
            new_w = ((w ** (1/3)) + t * temp * 1) ** 3
            
            # Cap at realistic max weights per stage
            stage_caps = {
                'Fry': 6,        # 0.05g -> ~5g
                'Parr': 60,      # 5g -> ~50g
                'Smolt': 180,    # 50g -> ~150g
                'Post-Smolt': 500,  # 150g -> ~450g
                'Adult': 7000    # 450g -> 5-7kg
            }
            max_weight = stage_caps.get(a.lifecycle_stage.name, 7000)
            new_w = min(new_w, max_weight)
            
            a.avg_weight_g = Decimal(str(round(new_w, 2)))
            a.biomass_kg = Decimal(str(round(a.population_count * new_w / 1000, 2)))
            a.save()
            
            if self.stats['days'] % 7 == 0:
                GrowthSample.objects.create(
                    assignment=a, sample_date=self.current_date, sample_size=30,
                    avg_weight_g=a.avg_weight_g,
                    avg_length_cm=Decimal(str(round((new_w ** 0.33) * 5, 1)))
                )
                self.stats['growth'] += 1
    
    def lice_update(self):
        """
        Generate lice counts for Adult stage batches in sea cages.
        Uses normalized format (lice_type + count_value) with realistic distributions.
        Sampling frequency: Every 7 days (weekly monitoring)
        """
        # Only track lice in Adult stage (sea cages)
        if self.batch.lifecycle_stage.name != 'Adult':
            return
        
        # Sample weekly (every 7 days)
        if self.stats['days'] % 7 != 0:
            return
        
        # Get all lice types from database (should be 15 types)
        lice_types = list(LiceType.objects.all())
        if not lice_types:
            return  # Skip if lice types not populated
        
        # Organize lice types by species and stage for realistic distribution
        lsalmonis_types = [lt for lt in lice_types if lt.species == 'Lepeophtheirus salmonis']
        caligus_types = [lt for lt in lice_types if lt.species == 'Caligus elongatus']
        
        # Sample 20 fish per container (industry standard)
        fish_sampled = 20
        
        # Detection methods with weights (manual microscopy most common)
        detection_methods = ['manual', 'visual', 'automated', 'camera']
        detection_weights = [0.7, 0.2, 0.05, 0.05]
        
        # Generate counts for each active assignment (container)
        for a in self.assignments:
            # Realistic lice pressure scenarios based on stage timing
            days_in_adult = self.stats['days'] - self.current_stage_start_day
            
            # Lice pressure increases over time in Adult stage
            if days_in_adult < 90:  # First 3 months - low pressure
                pressure_multiplier = 0.5
            elif days_in_adult < 180:  # Months 3-6 - moderate pressure
                pressure_multiplier = 1.0
            elif days_in_adult < 360:  # Months 6-12 - high pressure
                pressure_multiplier = 1.8
            else:  # After 12 months - very high pressure
                pressure_multiplier = 2.5
            
            # Select detection method for this sampling
            detection_method = random.choices(detection_methods, weights=detection_weights)[0]
            
            # Confidence levels by method
            confidence_map = {'automated': 0.98, 'manual': 0.95, 'camera': 0.90, 'visual': 0.75}
            confidence = Decimal(str(confidence_map[detection_method]))
            
            # Generate L. salmonis counts (primary species, ~85% of total lice)
            # Focus on adult females (regulatory concern)
            lsalmonis_adult_female = next((lt for lt in lsalmonis_types 
                                          if lt.gender == 'female' and lt.development_stage == 'adult'), None)
            lsalmonis_adult_male = next((lt for lt in lsalmonis_types 
                                        if lt.gender == 'male' and lt.development_stage == 'adult'), None)
            lsalmonis_chalimus = next((lt for lt in lsalmonis_types 
                                      if lt.development_stage == 'chalimus'), None)
            lsalmonis_preadult = next((lt for lt in lsalmonis_types 
                                      if lt.development_stage == 'pre-adult'), None)
            
            # Generate realistic counts (average 0.3-2.0 lice per fish depending on pressure)
            base_count_per_fish = 0.3 + (random.random() * 1.7) * pressure_multiplier
            total_lice = int(base_count_per_fish * fish_sampled)
            
            # Distribute across life stages (typical ratios)
            adult_female_count = int(total_lice * 0.35)  # 35% - Regulatory focus
            adult_male_count = int(total_lice * 0.25)    # 25%
            chalimus_count = int(total_lice * 0.30)      # 30% - Juveniles
            preadult_count = int(total_lice * 0.10)      # 10%
            
            # Create lice count records (normalized format)
            lice_records = []
            
            if adult_female_count > 0 and lsalmonis_adult_female:
                lice_records.append((lsalmonis_adult_female, adult_female_count))
            
            if adult_male_count > 0 and lsalmonis_adult_male:
                lice_records.append((lsalmonis_adult_male, adult_male_count))
            
            if chalimus_count > 0 and lsalmonis_chalimus:
                lice_records.append((lsalmonis_chalimus, chalimus_count))
            
            if preadult_count > 0 and lsalmonis_preadult:
                lice_records.append((lsalmonis_preadult, preadult_count))
            
            # Add occasional Caligus elongatus (secondary species, ~15% of samples)
            if random.random() < 0.15 and caligus_types:
                caligus_adult = random.choice(caligus_types)
                caligus_count = random.randint(1, int(total_lice * 0.20))
                lice_records.append((caligus_adult, caligus_count))
            
            # Bulk create all lice count records for this sample
            for lice_type, count_value in lice_records:
                LiceCount.objects.create(
                    batch=self.batch,
                    container=a.container,
                    user=self.user,
                    count_date=timezone.make_aware(datetime.combine(self.current_date, time(hour=10))),
                    lice_type=lice_type,
                    count_value=count_value,
                    detection_method=detection_method,
                    confidence_level=confidence,
                    fish_sampled=fish_sampled,
                    notes=f"Weekly monitoring - Day {self.stats['days']}"
                )
                self.stats['lice'] += 1
    
    def check_stage_transition(self):
        """Check if batch should transition to next lifecycle stage"""
        days_in_stage = self.stats['days'] - self.current_stage_start_day
        current_stage_name = self.batch.lifecycle_stage.name
        target_duration = self.stage_durations.get(current_stage_name, 999999)
        
        if days_in_stage >= target_duration:
            # Get next stage
            current_idx = None
            for i, stage in enumerate(self.stages):
                if stage.id == self.batch.lifecycle_stage.id:
                    current_idx = i
                    break
            
            if current_idx is not None and current_idx < len(self.stages) - 1:
                next_stage = self.stages[current_idx + 1]
                print(f"\n  → Stage Transition: {current_stage_name} → {next_stage.name}")
                
                # Map stage to hall letter (halls are specialized by stage)
                stage_to_hall = {
                    'Egg&Alevin': 'A',
                    'Fry': 'B',
                    'Parr': 'C',
                    'Smolt': 'D',
                    'Post-Smolt': 'E',
                    'Adult': None  # Sea cages, not halls
                }
                
                # Close out old assignments
                old_assignments = list(self.assignments)
                for a in old_assignments:
                    a.is_active = False
                    a.departure_date = self.current_date
                    a.save()
                
                # Move to new containers based on stage
                new_hall_letter = stage_to_hall.get(next_stage.name)
                
                if new_hall_letter:
                    # Freshwater stage - find appropriate hall
                    new_hall = Hall.objects.filter(
                        freshwater_station=self.station,
                        name__contains=f"-Hall-{new_hall_letter}"
                    ).first()
                    
                    if new_hall:
                        # Use transaction for atomic container allocation
                        from django.db import transaction
                        with transaction.atomic():
                            new_containers = self.find_available_containers(hall=new_hall, count=10)
                            
                            if not new_containers:
                                raise Exception(f"Insufficient available containers in {new_hall.name} for stage transition to {next_stage.name}")
                            
                            # Create new assignments in new hall
                            fish_per_container = old_assignments[0].population_count
                            avg_weight = old_assignments[0].avg_weight_g
                            
                            self.assignments = []
                            for cont in new_containers:
                                new_assignment = BatchContainerAssignment.objects.create(
                                    batch=self.batch,
                                    container=cont,
                                    lifecycle_stage=next_stage,
                                    assignment_date=self.current_date,
                                    population_count=fish_per_container,
                                    avg_weight_g=avg_weight,
                                    biomass_kg=Decimal(str(fish_per_container * float(avg_weight) / 1000)),
                                    is_active=True
                                )
                                self.assignments.append(new_assignment)
                        
                        print(f"  → Moved to {new_hall.name} ({len(self.assignments)} containers)")
                else:
                    # Adult stage - move to sea cages across ALL areas in geography
                    from django.db import transaction
                    with transaction.atomic():
                        sea_containers = self.find_available_containers(geography=self.geo, count=10)
                        
                        if not sea_containers:
                            raise Exception(f"Insufficient available sea cages in {self.geo.name} for stage transition to {next_stage.name}")
                        
                        fish_per_container = old_assignments[0].population_count
                        avg_weight = old_assignments[0].avg_weight_g
                        
                        self.assignments = []
                        for cont in sea_containers:
                            new_assignment = BatchContainerAssignment.objects.create(
                                batch=self.batch,
                                container=cont,
                                lifecycle_stage=next_stage,
                                assignment_date=self.current_date,
                                population_count=fish_per_container,
                                avg_weight_g=avg_weight,
                                biomass_kg=Decimal(str(fish_per_container * float(avg_weight) / 1000)),
                                is_active=True
                            )
                            self.assignments.append(new_assignment)
                    
                    # Show which sea areas were used
                    areas_used = set(a.container.area.name for a in self.assignments)
                    print(f"  → Moved to Sea Cages in {self.geo.name} ({len(self.assignments)} containers across {len(areas_used)} areas)")
                
                # Update batch stage
                self.batch.lifecycle_stage = next_stage
                self.batch.save()
                
                self.current_stage_start_day = self.stats['days']
    
    def health_journal(self):
        if not self.assignments: return
        a = random.choice(self.assignments)
        JournalEntry.objects.create(
            batch=self.batch, container=a.container, user=self.user,
            entry_date=timezone.make_aware(datetime.combine(self.current_date, time(hour=14))),
            category='observation', severity='low',
            description=f'Routine observation {a.lifecycle_stage.name}',
            resolution_status=False
        )
    
    def harvest_batch(self):
        """Harvest the batch if it's in Adult stage and ready"""
        if not self.assignments:
            return
        
        # Check if in Adult stage and average weight > 4kg
        is_adult = 'Adult' in self.batch.lifecycle_stage.name
        avg_weight = self.assignments[0].avg_weight_g
        
        if not is_adult or avg_weight < 4000:
            print(f"\n⚠ Batch not ready for harvest:")
            print(f"  Stage: {self.batch.lifecycle_stage.name} (need: Adult)")
            print(f"  Avg Weight: {avg_weight}g (need: >4000g)")
            return
        
        print(f"\n{'='*80}")
        print("HARVESTING BATCH")
        print(f"{'='*80}\n")
        
        # Get product grades
        grades = {g.code: g for g in ProductGrade.objects.all()}
        if not grades:
            print("✗ No product grades found. Run Phase 2 first!")
            return
        
        total_harvested = 0
        harvest_count = 0
        
        # Harvest each active assignment
        for a in self.assignments:
            if a.population_count == 0:
                continue
            
            # Create harvest event
            event = HarvestEvent.objects.create(
                event_date=timezone.make_aware(datetime.combine(
                    self.current_date, time(hour=10)
                )),
                batch=self.batch,
                assignment=a,
                dest_geography=self.geo,
                document_ref=f"HRV-{self.batch.batch_number}-{a.container.name}"
            )
            
            # Grade fish by weight (simplified distribution)
            fish_count = a.population_count
            avg_w = float(a.avg_weight_g)
            
            # Distribution: Superior(10%), A(40%), B(35%), C(12%), Reject(3%)
            distributions = [
                ('SUPERIOR', 0.10, avg_w * 1.15),  # 15% above average
                ('GRADE_A', 0.40, avg_w * 1.05),   # 5% above average
                ('GRADE_B', 0.35, avg_w),          # average
                ('GRADE_C', 0.12, avg_w * 0.85),   # 15% below average
                ('REJECT', 0.03, avg_w * 0.60),    # 40% below average
            ]
            
            for grade_code, pct, weight_g in distributions:
                count = int(fish_count * pct)
                if count == 0:
                    continue
                
                grade = grades.get(grade_code)
                if not grade:
                    continue
                
                live_weight = Decimal(str(count * weight_g / 1000))  # kg
                gutted_weight = live_weight * Decimal('0.85')  # 85% yield
                fillet_weight = live_weight * Decimal('0.55')  # 55% yield
                
                HarvestLot.objects.create(
                    event=event,
                    product_grade=grade,
                    live_weight_kg=live_weight,
                    gutted_weight_kg=gutted_weight,
                    fillet_weight_kg=fillet_weight,
                    unit_count=count
                )
            
            total_harvested += fish_count
            harvest_count += 1
            
            # Mark assignment as harvested (inactive)
            a.is_active = False
            a.save()
        
        print(f"✓ Harvested {harvest_count} containers")
        print(f"✓ Total fish harvested: {total_harvested:,}")
        print(f"✓ Average weight: {avg_weight:.0f}g")
        print(f"✓ Total biomass: {sum(a.biomass_kg for a in self.assignments):,.0f}kg\n")
    
    def run(self):
        try:
            self.init()
            self.create_batch()
            
            print(f"{'='*80}")
            print(f"Processing {self.duration} Days")
            print(f"{'='*80}\n")
            
            for _ in range(self.duration):
                self.process_day()
                self.current_date += timedelta(days=1)
            
            # Check if batch is ready for harvest
            self.harvest_batch()
            
            print(f"\n{'='*80}")
            print("Complete!")
            print(f"{'='*80}\n")
            print(f"Batch: {self.batch.batch_number}")
            print(f"Final Stage: {self.batch.lifecycle_stage.name}")
            print(f"Days: {self.stats['days']}")
            print(f"\nEvent Counts:")
            print(f"  Environmental: {self.stats['env']:,} (6 readings/day/sensor)")
            print(f"  Feeding: {self.stats['feed']:,}")
            print(f"  Mortality: {self.stats['mort']:,}")
            print(f"  Growth Samples: {self.stats['growth']:,}")
            print(f"  Lice Counts: {self.stats['lice']:,} (Adult stage weekly)")
            print(f"  Feed Purchases: {self.stats['purchases']:,}")
            
            # Final batch stats
            final_pop = sum(a.population_count for a in self.assignments)
            final_weight = self.assignments[0].avg_weight_g if self.assignments else 0
            final_biomass = sum(a.biomass_kg for a in self.assignments)
            
            print(f"\nFinal Batch Status:")
            print(f"  Population: {final_pop:,} fish")
            print(f"  Avg Weight: {final_weight}g")
            print(f"  Total Biomass: {final_biomass:,.2f}kg")
            print(f"\nTotal Events: {sum(self.stats.values()):,}\n")
            return 0
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', required=True)
    parser.add_argument('--eggs', type=int, required=True)
    parser.add_argument('--geography', required=True)
    parser.add_argument('--duration', type=int, default=650)
    args = parser.parse_args()
    
    start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  Phase 3: Chronological Event Engine".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "═" * 78 + "╝\n")
    
    engine = EventEngine(start, args.eggs, args.geography, args.duration)
    return engine.run()

if __name__ == '__main__':
    sys.exit(main())
