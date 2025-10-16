#!/usr/bin/env python3
"""
AquaMind Phase 3: Core Event Generation Logic
Compact implementation focusing on essential features
"""
import os, sys, django, json, random, argparse, numpy as np
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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
        self.stats = {'days': 0, 'env': 0, 'feed': 0, 'mort': 0, 'growth': 0, 'purchases': 0}
        self.current_stage_start_day = 0
        self.stage_durations = {'Egg&Alevin': 90, 'Fry': 90, 'Parr': 90, 'Smolt': 90, 'Post-Smolt': 90}
        
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
        containers = Container.objects.filter(hall=hall_a).order_by('name')[:10]
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
                self.batch.lifecycle_stage = next_stage
                self.batch.save()
                
                # Update all assignments
                for a in self.assignments:
                    a.lifecycle_stage = next_stage
                    a.save()
                
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
