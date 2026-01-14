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
from apps.finance.models import FactHarvest, DimCompany, DimSite
from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, MortalityModel, 
    TemperatureProfile, TemperatureReading,
    FCRModelStage, ScenarioProjection
)
# Explicit import to avoid ambiguity (FeedContainer is in infrastructure)
from apps.infrastructure.models import FeedContainer
from apps.infrastructure.models import Container
from apps.batch.models import BatchContainerAssignment, TransferAction, BatchTransferWorkflow
from django.db.models import Q

User = get_user_model()

PROGRESS_DIR = Path(project_root) / 'aquamind' / 'docs' / 'progress' / 'test_data'
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

class EventEngine:
    def __init__(self, start_date, eggs, geography, duration=900, station_name=None, batch_number=None, event_feed=None):
        self.start_date = start_date
        self.current_date = start_date
        self.initial_eggs = eggs
        self.duration = duration
        self.geography_name = geography
        self.event_feed = event_feed
        self.assigned_station_name = station_name  # DETERMINISTIC: Pre-assigned station
        self.assigned_batch_number = batch_number  # DETERMINISTIC: Pre-assigned batch number from schedule
        self.stats = {
            'days': 0, 'env': 0, 'feed': 0, 'mort': 0, 'growth': 0, 
            'purchases': 0, 'lice': 0, 'scenarios': 0, 'finance_facts': 0, 
            'transfer_workflows': 0, 'health_sampling_events': 0, 
            'fish_observations': 0, 'parameter_scores': 0, 'treatments': 0
        }
        self.current_stage_start_day = 0
        # Realistic lifecycle stage durations by order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
        # Total lifecycle: 90×5 + 450 = 900 days
        self.stage_durations = [90, 90, 90, 90, 90, 450]  # Indexed by order-1
        
        # Check if using pre-allocated schedule
        self.use_schedule = os.environ.get('USE_SCHEDULE') == '1'
        if self.use_schedule:
            self.container_schedule = json.loads(os.environ.get('CONTAINER_SCHEDULE', '{}'))
            self.sea_schedule = json.loads(os.environ.get('SEA_SCHEDULE', '{}'))
        
        # Track when treatments were last applied (prevent duplicate treatments)
        self.lice_treatments_applied = 0  # Counter for lice treatments (max 2 per batch)
        self.target_rings_per_batch = 20  # Configurable for sea stages

        # Use deterministic harvest target if provided (from scheduler)
        harvest_target_env = os.environ.get('HARVEST_TARGET_KG')
        if harvest_target_env:
            self.deterministic_harvest_target = Decimal(harvest_target_env)
            print(f"✓ DETERMINISTIC: Using harvest target {self.deterministic_harvest_target}kg from schedule")
        else:
            self.deterministic_harvest_target = None
        
    def init(self):
        print(f"\n{'='*80}")
        print("Initializing Event Engine")
        print(f"{'='*80}\n")
        
        self.geo = Geography.objects.get(name=self.geography_name)
        
        # DETERMINISTIC: Use pre-assigned station (if provided) or first available
        if self.assigned_station_name:
            # Deterministic mode: Use specific pre-assigned station
            self.station = FreshwaterStation.objects.get(
                name=self.assigned_station_name,
                geography=self.geo
            )
            print(f"✓ DETERMINISTIC: Using pre-assigned station {self.station.name}")
        else:
            # Fallback: Use first station (for single-batch testing)
            self.station = FreshwaterStation.objects.filter(geography=self.geo).first()
            print(f"⚠️  NON-DETERMINISTIC: Using first available station {self.station.name}")
        
        self.sea_area = Area.objects.filter(geography=self.geo).first()
        self.species = Species.objects.get(name="Atlantic Salmon")
        self.stages = list(LifeCycleStage.objects.filter(species=self.species).order_by('order'))
        self.user = User.objects.filter(username='system_admin').first() or User.objects.first()
        self.env_params = list(EnvironmentalParameter.objects.all())
        
        # Initialize scenario models (shared across batches)
        self._init_scenario_models()
        
        # Get finance dimensions
        self._init_finance_dimensions()
        
        # Ensure feed inventory exists (auto-initialize if empty)
        self._ensure_feed_inventory()
        
        print(f"✓ Geography: {self.geo.name}")
        print(f"✓ Station: {self.station.name}")
        print(f"✓ Sea Area: {self.sea_area.name}")
        print(f"✓ Duration: {self.duration} days\n")
        if self.event_feed and hasattr(self.event_feed, 'on_init'):
            self.event_feed.on_init(self)
    
    def _init_finance_dimensions(self):
        """Initialize finance company and site dimensions."""
        try:
            # Get or create company for this geography
            # Simplified: use geography + farming subsidiary (FM = 3-char code)
            self.finance_company, _ = DimCompany.objects.get_or_create(
                geography=self.geo,
                subsidiary='FM',  # FIX: Use 3-char code, not full name
                defaults={
                    'display_name': f'{self.geo.name} Farming',
                    'currency': 'EUR' if 'Faroe' in self.geo.name else 'GBP'
                }
            )
            
            # Get or create site for freshwater station
            if self.station:
                self.finance_site_freshwater, _ = DimSite.objects.get_or_create(
                    source_model='STATION',
                    source_pk=self.station.id,
                    defaults={
                        'company': self.finance_company,
                        'site_name': self.station.name
                    }
                )
            
            # Get or create site for sea area
            if self.sea_area:
                self.finance_site_sea, _ = DimSite.objects.get_or_create(
                    source_model='AREA',
                    source_pk=self.sea_area.id,
                    defaults={
                        'company': self.finance_company,
                        'site_name': self.sea_area.name
                    }
                )
            
            print(f"✓ Finance dimensions ready: {self.finance_company.display_name}")
            
        except Exception as e:
            print(f"⚠ Finance dimension setup failed: {e}")
            self.finance_company = None
            self.finance_site_freshwater = None
            self.finance_site_sea = None
    
    def _ensure_feed_inventory(self):
        """
        Ensure feed containers have initial stock.
        Auto-initializes if database is empty (first batch scenario).
        Idempotent: only runs once per database.
        """
        from django.db.models import Sum
        
        # Check total feed stock across all containers
        total_stock = FeedContainerStock.objects.aggregate(
            total=Sum('quantity_kg')
        )['total'] or Decimal('0')
        
        if total_stock > 0:
            # Already initialized, skip
            return
        
        print(f"  🔄 Feed inventory empty - auto-initializing with ~3,730 tonnes...")
        
        # Get all active feed containers
        feed_containers = FeedContainer.objects.filter(active=True)
        if feed_containers.count() == 0:
            print(f"  ⚠️  No feed containers found - skipping feed initialization")
            return
        
        # Get feed types
        feed_types = Feed.objects.filter(is_active=True)
        if feed_types.count() == 0:
            print(f"  ⚠️  No feed types found - skipping feed initialization")
            return
        
        # Purchase date: 30 days ago
        purchase_date = date.today() - timedelta(days=30)
        suppliers = ['BioMar', 'Skretting', 'Cargill', 'Aller Aqua']
        
        created_purchases = 0
        created_stock = 0
        
        # Pre-stock all feed containers
        for idx, container in enumerate(feed_containers, 1):
            # Select feed type based on container location
            if 'Silo' in container.name or container.container_type == 'SILO':
                # Freshwater silos: starter/grower feeds
                feed = feed_types.filter(name__contains='Starter').first() or feed_types.first()
                quantity_kg = Decimal('5000.0')  # 5 tonnes per silo
                cost_per_kg = Decimal('2.50')
            else:  # BARGE
                # Sea barges: finisher feeds
                feed = feed_types.filter(name__contains='Finisher').first() or feed_types.last()
                quantity_kg = Decimal('25000.0')  # 25 tonnes per barge
                cost_per_kg = Decimal('2.00')
            
            # Create purchase
            supplier = suppliers[idx % len(suppliers)]
            purchase = FeedPurchase.objects.create(
                feed=feed,
                purchase_date=purchase_date,
                supplier=supplier,
                batch_number=f"INIT-{purchase_date.strftime('%Y%m%d')}-{idx:04d}",
                quantity_kg=quantity_kg,
                cost_per_kg=cost_per_kg,
                expiry_date=purchase_date + timedelta(days=365),
                notes=f'Auto-initialized inventory for {container.name}'
            )
            created_purchases += 1
            
            # Create stock entry
            FeedContainerStock.objects.create(
                feed_container=container,
                feed_purchase=purchase,
                quantity_kg=quantity_kg,
                entry_date=timezone.make_aware(
                    datetime.combine(purchase_date, datetime.min.time())
                )
            )
            created_stock += 1
        
        # Calculate total
        total_inventory = FeedContainerStock.objects.aggregate(
            total=Sum('quantity_kg')
        )['total'] or Decimal('0')
        
        print(f"  ✅ Feed inventory initialized: {total_inventory/1000:.0f} tonnes ({created_purchases} purchases)")
    
    def _init_scenario_models(self):
        """
        Initialize shared scenario models (TGC, FCR, Mortality, Temperature).
        These are reused across all batches to avoid duplication.
        """
        is_faroe = 'Faroe' in self.geography_name
        
        # 1. Create temperature profiles (geography-specific for sea temps)
        self.temp_profile = self._get_or_create_temperature_profile()
        
        # 2. Create/get TGC model
        self.tgc_model, _ = TGCModel.objects.get_or_create(
            name=f'{self.geography_name} Standard TGC',
            defaults={
                'location': self.geography_name,
                'release_period': 'Year-round',
                'tgc_value': 0.00245 if is_faroe else 0.00235,  # Faroe slightly better growth
                'exponent_n': 0.33,  # Temperature exponent
                'exponent_m': 0.66,  # Weight exponent
                'profile': self.temp_profile
            }
        )
        
        # 3. Create/get FCR model with stage-specific values
        self.fcr_model, created = FCRModel.objects.get_or_create(
            name='Standard Atlantic Salmon FCR',
            defaults={}
        )
        
        if created:
            # Add stage-specific FCR values
            for stage in self.stages:
                fcr_values = {
                    'Egg&Alevin': (0.0, 90),   # No feed
                    'Fry': (1.0, 90),
                    'Parr': (1.1, 90),
                    'Smolt': (1.0, 90),
                    'Post-Smolt': (1.1, 90),
                    'Adult': (1.2, 450)
                }
                fcr, duration = fcr_values.get(stage.name, (1.2, 90))
                
                FCRModelStage.objects.get_or_create(
                    model=self.fcr_model,
                    stage=stage,
                    defaults={
                        'fcr_value': fcr,
                        'duration_days': duration
                    }
                )
        
        # 4. Create/get mortality model
        self.mortality_model, _ = MortalityModel.objects.get_or_create(
            name='Standard Mortality',
            defaults={
                'frequency': 'daily',
                'rate': 0.03  # 0.03% daily (realistic avg)
            }
        )
        
        print(f"✓ Scenario models ready: TGC={self.tgc_model.tgc_value}, FCR=Standard, Mortality={self.mortality_model.rate}%")
    
    def _get_or_create_temperature_profile(self):
        """
        Create geography-specific temperature profile for sea stages.
        Faroe Islands: Stable 8-11°C (Gulf Stream influence)
        Scotland: Variable 6-14°C (more seasonal variation)
        """
        is_faroe = 'Faroe' in self.geography_name
        profile_name = f'{self.geography_name} Sea Temperature'
        
        # Check if profile exists
        profile = TemperatureProfile.objects.filter(name=profile_name).first()
        if profile:
            return profile
        
        # Create new profile with daily temps for 450-day Adult stage
        profile = TemperatureProfile.objects.create(name=profile_name)
        
        # Generate realistic temperature curve
        temps = []
        for day in range(450):
            if is_faroe:
                # Faroe: Stable Gulf Stream temps (8-11°C, subtle seasonal)
                base = 9.5
                seasonal = 1.0 * np.sin(2 * np.pi * day / 365)
                daily_var = random.uniform(-0.3, 0.3)
                temp = base + seasonal + daily_var
            else:
                # Scotland: More variable (6-14°C, stronger seasonal)
                base = 10.0
                seasonal = 3.0 * np.sin(2 * np.pi * (day - 90) / 365)  # Peak in summer
                daily_var = random.uniform(-0.5, 0.5)
                temp = base + seasonal + daily_var
            
            temps.append(max(6.0, min(14.0, temp)))  # Clamp to realistic range
        
        # Bulk create temperature readings
        readings = [
            TemperatureReading(
                profile=profile,
                day_number=i + 1,  # Use relative day numbers (1-450)
                temperature=temps[i]
            )
            for i in range(450)
        ]
        TemperatureReading.objects.bulk_create(readings, batch_size=500)
        
        avg_temp = sum(temps) / len(temps)
        print(f"✓ Created temperature profile: {profile_name} (avg: {avg_temp:.1f}°C)")
        
        return profile
    
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
        """
        Create batch using BatchCreationWorkflow for full audit trail.
        Simulates real user workflow: supplier → delivery → egg placement
        """
        print(f"{'='*80}")
        print("Creating Batch via Creation Workflow")
        print(f"{'='*80}\n")
        
        from apps.batch.models import BatchCreationWorkflow, CreationAction
        from apps.broodstock.models import EggSupplier
        
        # Extract year for workflow numbering
        year = self.start_date.year
        
        # Use pre-assigned batch number from schedule (if provided) to avoid race conditions
        if self.assigned_batch_number:
            batch_name = self.assigned_batch_number
            print(f"✓ DETERMINISTIC: Using pre-assigned batch number {batch_name}")
        else:
            # Fallback: Generate batch number (may have race condition in parallel execution)
            prefix = "FI" if "Faroe" in self.geography_name else "SCO"
            existing = Batch.objects.filter(batch_number__startswith=f"{prefix}-{year}").count()
            batch_name = f"{prefix}-{year}-{existing + 1:03d}"
            print(f"⚠️  NON-DETERMINISTIC: Generated batch number {batch_name} (may conflict in parallel)")
        
        # Get or create egg supplier
        supplier, _ = EggSupplier.objects.get_or_create(
            name='AquaGen Norway' if 'Faroe' in self.geography_name else 'Marine Harvest Scotland',
            defaults={
                'contact_details': 'eggs@supplier.com',
                'certifications': 'ASC Certified'
            }
        )
        
        # Create batch (initially PLANNED status)
        self.batch = Batch.objects.create(
            batch_number=batch_name,
            species=self.species,
            lifecycle_stage=self.stages[0],
            start_date=self.start_date,
            status='PLANNED',  # Start as planned, will be ACTIVE after actions executed
            notes=f"Generated {datetime.now().date()}"
        )
        
        # Generate workflow number (deterministic based on batch number to avoid race conditions)
        # Batch: FAR-2020-001 → Workflow: CRT-FAR-2020-001
        workflow_number = f'CRT-{batch_name}'
        
        # Create creation workflow
        creation_workflow = BatchCreationWorkflow.objects.create(
            workflow_number=workflow_number,
            batch=self.batch,
            egg_source_type='EXTERNAL',
            external_supplier=supplier,
            total_eggs_planned=self.initial_eggs,
            status='IN_PROGRESS',  # Start in progress
            planned_start_date=self.start_date,
            planned_completion_date=self.start_date,
            actual_start_date=self.start_date,
            created_by=self.user,
            notes=f'Automated batch creation: {batch_name}'
        )
        
        # Find Hall-A (handle both "FI-FW-01-Hall-A" and "Hall A" naming)
        hall_a = Hall.objects.filter(
            freshwater_station=self.station
        ).filter(
            models.Q(name__contains="-Hall-A") | models.Q(name__contains="Hall A")
        ).first()
        
        # Use database transaction with row-level locking to prevent race conditions
        from django.db import transaction
        
        with transaction.atomic():
            if self.use_schedule:
                # Use pre-allocated containers from schedule
                hall_name = self.container_schedule['egg_alevin']['hall']
                container_names = self.container_schedule['egg_alevin']['containers']
                containers = list(Container.objects.filter(name__in=container_names))
            else:
                containers = self.find_available_containers(hall=hall_a, count=10)
            
            if not containers:
                raise Exception(f"Insufficient available containers in {hall_a.name}. Need 10, infrastructure may be saturated.")
            
            eggs_per = self.initial_eggs // 10
            
            self.assignments = []
            action_number = 1
            
            for cont in containers:
                # Create assignment
                assignment = BatchContainerAssignment.objects.create(
                    batch=self.batch, container=cont, lifecycle_stage=self.stages[0],
                    assignment_date=self.start_date, population_count=eggs_per,
                    avg_weight_g=Decimal('0.1'), biomass_kg=Decimal(str(eggs_per * 0.1 / 1000)),
                    is_active=True
                )
                self.assignments.append(assignment)
                
                # Create creation action (documents egg delivery to this container)
                CreationAction.objects.create(
                    workflow=creation_workflow,
                    action_number=action_number,
                    dest_assignment=assignment,
                    egg_count_planned=eggs_per,
                    egg_count_actual=eggs_per,
                    mortality_on_arrival=0,  # Healthy delivery
                    status='COMPLETED',  # Auto-executed
                    expected_delivery_date=self.start_date,
                    actual_delivery_date=self.start_date,
                    executed_by=self.user,
                    delivery_method='TRANSPORT',
                    egg_quality_score=5,  # Excellent quality
                    notes=f'Egg delivery to {cont.name}'
                )
                action_number += 1
        
        # Update workflow status
        creation_workflow.total_actions = len(self.assignments)
        creation_workflow.actions_completed = len(self.assignments)
        creation_workflow.total_eggs_received = self.initial_eggs
        creation_workflow.status = 'COMPLETED'
        creation_workflow.actual_completion_date = self.start_date
        creation_workflow.progress_percentage = Decimal('100.00')
        creation_workflow.save()
        
        # Update batch to ACTIVE now that eggs are placed
        self.batch.status = 'ACTIVE'
        self.batch.save()
        
        print(f"✓ Creation Workflow: {workflow_number} ({len(self.assignments)} actions)")
        print(f"✓ Batch: {self.batch.batch_number} (supplier: {supplier.name})")
        print(f"✓ {len(self.assignments)} assignments ({eggs_per:,} eggs each)\n")
        if self.event_feed and hasattr(self.event_feed, 'on_batch_created'):
            self.event_feed.on_batch_created(self.batch, self.assignments)
        
        # Create scenario immediately after batch creation (for growth analysis)
        self._create_initial_scenario()
        
    def process_day(self):
        self.assignments = list(BatchContainerAssignment.objects.filter(batch=self.batch, is_active=True))
        if not self.assignments: return

        if self.event_feed and hasattr(self.event_feed, 'process_day'):
            handled = self.event_feed.process_day(self)
            if handled:
                self.stats['days'] += 1
                return

        # Check for stage transition BEFORE processing events
        self.check_stage_transition()
        
        # 6 readings per day (optimized bulk insert)
        self.env_readings_bulk([6, 8, 10, 14, 16, 18])
        self.feed_events(8)
        self.mortality_check()
        self.feed_events(16)
        self.growth_update()
        self.lice_update()  # Weekly lice sampling (Adult stage only)
        self.health_sampling()  # Monthly health sampling (Post-Smolt/Adult, 75 fish)
        self.vaccination_events()  # Vaccinations at Smolt (180, 210) and Post-Smolt (280, 310)
        self.lice_treatment_events()  # Lice treatments in Adult stage (2x per batch)
        
        if self.stats['days'] % 30 == 0:
            self.health_journal()
        
        self.stats['days'] += 1
        if self.stats['days'] % 50 == 0:
            print(f"  Day {self.stats['days']}/{self.duration}: {self.batch.lifecycle_stage.name}, "
                  f"Pop: {sum(a.population_count for a in self.assignments):,}, "
                  f"Avg: {self.assignments[0].avg_weight_g}g")

        if self.event_feed and hasattr(self.event_feed, 'after_day'):
            self.event_feed.after_day(self)

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
                            container=a.container, batch=self.batch,
                            batch_container_assignment=a,  # ← FIXED: Populate assignment FK
                            is_manual=False
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
            # Egg&Alevin stage (order=1) doesn't feed - uses yolk sac
            if a.lifecycle_stage.order == 1: continue
            
            biomass = float(a.biomass_kg)
            if biomass <= 0: continue
            
            # Feeding rates by stage order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
            feeding_rates = [0, 3, 2.5, 2, 1.5, 1]  # % of biomass per day
            rate = feeding_rates[a.lifecycle_stage.order - 1] if a.lifecycle_stage.order <= 6 else 1.5
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
        # Feed types by stage order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
        feed_names = [
            None,  # Egg&Alevin don't feed
            'Starter Feed 0.5mm',   # Fry
            'Starter Feed 1.0mm',   # Parr
            'Grower Feed 2.0mm',    # Smolt
            'Grower Feed 3.0mm',    # Post-Smolt
            'Finisher Feed 4.5mm'   # Adult
        ]
        feed_name = feed_names[stage.order - 1] if stage.order <= 6 else 'Starter Feed 0.5mm'
        return Feed.objects.filter(name=feed_name).first() if feed_name else None
    
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
        # Daily mortality rates by stage order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
        mortality_rates = [0.0015, 0.0005, 0.0003, 0.0002, 0.00015, 0.0001]
        
        for a in self.assignments:
            rate = mortality_rates[a.lifecycle_stage.order - 1] if a.lifecycle_stage.order <= 6 else 0.0001
            exp = a.population_count * rate
            act = np.random.poisson(exp)
            
            if act > 0:
                biomass_lost = Decimal(str(act * float(a.avg_weight_g) / 1000))
                
                MortalityEvent.objects.create(
                    batch=self.batch,
                    assignment=a,  # ← FIXED: Container-specific mortality tracking
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
        # TGC values from industry data by stage order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
        # Values are per 1000 degree-days, already divided by 1000
        tgc_values = [
            0,          # Egg&Alevin: no growth (feed from yolk sac)
            0.00225,    # Fry: 2.25/1000
            0.00275,    # Parr: 2.75/1000
            0.00275,    # Smolt: 2.75/1000
            0.00325,    # Post-Smolt: 3.25/1000
            0.0031      # Adult: 3.1/1000
        ]
        
        for a in self.assignments:
            t = tgc_values[a.lifecycle_stage.order - 1] if a.lifecycle_stage.order <= 6 else 0
            if t == 0:  # No growth for Egg&Alevin
                continue
            
            # Temperature varies by stage (freshwater ~12°C, seawater ~8-10°C)
            # Orders 2-4 (Fry, Parr, Smolt) are freshwater, 5-6 (Post-Smolt, Adult) are seawater
            if 2 <= a.lifecycle_stage.order <= 4:
                temp = 12.0  # Freshwater stages
            else:
                temp = 9.0   # Seawater stages
            
            w = float(a.avg_weight_g)
            
            # TGC formula: W_final^(1/3) = W_initial^(1/3) + (TGC * temp * days) / 1000
            # Already divided TGC by 1000, so: W_f^(1/3) = W_i^(1/3) + TGC * temp * days
            new_w = ((w ** (1/3)) + t * temp * 1) ** 3
            
            # Cap at realistic max weights per stage order: [Egg&Alevin, Fry, Parr, Smolt, Post-Smolt, Adult]
            max_weights = [
                0.1,    # Egg&Alevin: egg weight
                6,      # Fry: 0.05g -> ~5g
                60,     # Parr: 5g -> ~50g
                180,    # Smolt: 50g -> ~150g
                500,    # Post-Smolt: 150g -> ~450g
                7000    # Adult: 450g -> 5-7kg
            ]
            max_weight = max_weights[a.lifecycle_stage.order - 1] if a.lifecycle_stage.order <= 6 else 7000
            new_w = min(new_w, max_weight)
            
            a.avg_weight_g = Decimal(str(round(new_w, 2)))
            a.biomass_kg = Decimal(str(round(a.population_count * new_w / 1000, 2)))
            a.save()
            
            # Weekly growth sampling (with individual fish observations)
            if self.stats['days'] % 7 == 0:
                from apps.batch.models import IndividualGrowthObservation
                from random import uniform
                
                # Create growth sample (initially with placeholder values)
                growth_sample = GrowthSample.objects.create(
                    assignment=a,
                    sample_date=self.current_date,
                    sample_size=0,  # Will be recalculated
                    avg_weight_g=Decimal('0.0'),  # Will be recalculated
                )
                
                # Generate individual fish observations (30 fish sample)
                num_fish = 30
                base_weight = float(new_w)
                base_length = float((new_w ** 0.33) * 5)
                
                for fish_num in range(1, num_fish + 1):
                    # Add realistic variation around batch average
                    # Weight: ±15% variation
                    fish_weight = base_weight * uniform(0.85, 1.15)
                    # Length: ±10% variation
                    fish_length = base_length * uniform(0.90, 1.10)
                    
                    IndividualGrowthObservation.objects.create(
                        growth_sample=growth_sample,
                        fish_identifier=str(fish_num),
                        weight_g=Decimal(str(round(fish_weight, 2))),
                        length_cm=Decimal(str(round(fish_length, 2)))
                    )
                
                # Calculate aggregates from individual observations
                growth_sample.calculate_aggregates()
                self.stats['growth'] += 1
    
    def lice_update(self):
        """
        Generate lice counts for Adult stage batches in sea cages.
        Uses normalized format (lice_type + count_value) with realistic distributions.
        Sampling frequency: Every 7 days (weekly monitoring)
        """
        # Only track lice in Adult stage (order=6, sea cages)
        if self.batch.lifecycle_stage.order != 6:
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
        current_stage_order = self.batch.lifecycle_stage.order
        # Get duration for current stage (order-1 indexed)
        target_duration = self.stage_durations[current_stage_order - 1] if current_stage_order <= 6 else 999999
        
        if days_in_stage >= target_duration:
            # Get next stage
            current_idx = None
            for i, stage in enumerate(self.stages):
                if stage.id == self.batch.lifecycle_stage.id:
                    current_idx = i
                    break
            
            if current_idx is not None and current_idx < len(self.stages) - 1:
                next_stage = self.stages[current_idx + 1]
                current_stage = self.stages[current_idx]
                print(f"\n  → Stage Transition: {current_stage.name} → {next_stage.name}")
                
                # Map stage order to hall letter (halls are specialized by stage)
                # Order 1-5 → Halls A-E, Order 6 (Adult) → Sea cages (no hall)
                hall_letters = ['A', 'B', 'C', 'D', 'E', None]  # Index by order-1
                
                # Close out old assignments (will be linked to transfer workflow)
                old_assignments = list(self.assignments)
                for a in old_assignments:
                    a.is_active = False
                    a.departure_date = self.current_date
                    a.save()
                
                # Move to new containers based on stage order
                new_hall_letter = hall_letters[next_stage.order - 1] if next_stage.order <= 6 else None
                
                if new_hall_letter:
                    # Freshwater stage - find appropriate hall (handle both naming formats)
                    new_hall = Hall.objects.filter(
                        freshwater_station=self.station
                    ).filter(
                        models.Q(name__contains=f"-Hall-{new_hall_letter}") | 
                        models.Q(name__contains=f"Hall {new_hall_letter}")
                    ).first()
                    
                    if new_hall:
                        # Use transaction for atomic container allocation
                        from django.db import transaction
                        with transaction.atomic():
                            if self.use_schedule:
                                # Use next stage from schedule
                                # Key format in schedule is lowercase with underscores: egg_alevin, fry, etc.
                                schedule_key = next_stage.name.lower().replace('&', '_').replace('-', '_')
                                next_stage_config = self.container_schedule.get(schedule_key)
                                if not next_stage_config:
                                     # Try explicit lookup for mismatch keys
                                     if 'post' in schedule_key: schedule_key = 'post_smolt'
                                     next_stage_config = self.container_schedule.get(schedule_key)
                                
                                if not next_stage_config:
                                    raise Exception(f"Schedule missing configuration for stage {next_stage.name} (key: {schedule_key})")
                                    
                                container_names = next_stage_config['containers']
                                new_containers = list(Container.objects.filter(name__in=container_names))
                            else:
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
                                    population_count=fish_per_container,  # Pre-populate for event engine
                                    avg_weight_g=avg_weight,
                                    biomass_kg=Decimal(str(fish_per_container * float(avg_weight) / 1000)),
                                    is_active=True
                                )
                                self.assignments.append(new_assignment)
                        
                        print(f"  → Moved to {new_hall.name} ({len(self.assignments)} containers)")
                else:
                    # Adult stage - move to sea cages
                    from django.db import transaction
                    with transaction.atomic():
                        # Calculate total fish from all old assignments
                        total_fish = sum(a.population_count for a in old_assignments)
                        avg_weight = old_assignments[0].avg_weight_g

                        # Check if using pre-allocated schedule (deterministic mode)
                        if self.use_schedule and self.sea_schedule:
                            # Use pre-allocated sea containers from schedule
                            container_names = self.sea_schedule['rings']
                            sea_containers = list(Container.objects.filter(name__in=container_names))
                            
                            if len(sea_containers) < len(container_names):
                                raise Exception(
                                    f"Schedule specifies {len(container_names)} sea rings, but only {len(sea_containers)} found in database"
                                )
                            
                            print(f"  → Using scheduled sea allocation: {len(sea_containers)} rings in {self.sea_schedule.get('area', 'unknown')}")
                        else:
                            # Dynamic allocation (fallback for standalone execution)
                            # Estimate containers needed (target ~200,000 fish per container for adult salmon)
                            target_fish_per_container = 200000
                            containers_needed = max(10, (total_fish + target_fish_per_container - 1) // target_fish_per_container)

                            # SELECT SINGLE AREA using round-robin (batches rarely span multiple areas)
                            # Count batches in Adult stage (order=6)
                            existing_adult_batches = Batch.objects.filter(
                                lifecycle_stage__order=6,
                                batch_assignments__container__area__geography=self.geo
                            ).distinct().count()
                            
                            all_areas = list(Area.objects.filter(geography=self.geo).order_by('name'))
                            if not all_areas:
                                raise Exception(f"No sea areas found in {self.geo.name}")
                            
                            area_idx = existing_adult_batches % len(all_areas)
                            target_area = all_areas[area_idx]
                            print(f"  → Selected area {area_idx + 1}/{len(all_areas)}: {target_area.name}")

                            # Find available containers IN SELECTED AREA ONLY
                            occupied_ids = set(
                                BatchContainerAssignment.objects.select_for_update(skip_locked=True).filter(
                                    is_active=True
                                ).values_list('container_id', flat=True)
                            )

                            # Get ALL available containers in the area, not just the first N
                            # Convert to list immediately to avoid N database queries on indexing
                            all_available_containers = list(
                                Container.objects.select_for_update(skip_locked=True).filter(
                                    area=target_area,
                                    active=True
                                ).exclude(
                                    id__in=occupied_ids
                                )
                            )

                            # If we need more containers than available, use all available
                            # Otherwise, distribute evenly across all rings (not just first N)
                            if len(all_available_containers) <= containers_needed:
                                sea_containers = all_available_containers
                            else:
                                # Distribute across ALL rings by taking every Nth container
                                # This ensures even distribution across the entire area
                                step = len(all_available_containers) // containers_needed
                                sea_containers = []
                                for i in range(containers_needed):
                                    idx = (i * step) % len(all_available_containers)
                                    sea_containers.append(all_available_containers[idx])

                            if len(sea_containers) < containers_needed:
                                raise Exception(
                                    f"Insufficient available sea cages in {target_area.name}. "
                                    f"Need {containers_needed}, found {len(sea_containers)}"
                                )

                        # Distribute fish evenly across containers
                        fish_per_container = total_fish // len(sea_containers)
                        remainder = total_fish % len(sea_containers)

                        self.assignments = []
                        for i, cont in enumerate(sea_containers):
                            # Add one extra fish to first 'remainder' containers for even distribution
                            container_fish = fish_per_container + (1 if i < remainder else 0)

                            new_assignment = BatchContainerAssignment.objects.create(
                                batch=self.batch,
                                container=cont,
                                lifecycle_stage=next_stage,
                                assignment_date=self.current_date,
                                population_count=container_fish,  # Pre-populate for event engine
                                avg_weight_g=avg_weight,
                                biomass_kg=Decimal(str(container_fish * float(avg_weight) / 1000)),
                                is_active=True
                            )
                            self.assignments.append(new_assignment)
                    
                    # Get area name from first container
                    area_name = self.assignments[0].container.area.name if self.assignments and self.assignments[0].container.area else "Unknown"
                    print(f"  → Moved to {area_name} ({len(self.assignments)} sea containers)")
                
                # Create transfer workflow to document this transition (auditable action)
                self._create_transfer_workflow(old_assignments, self.assignments, next_stage)
                
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
    
    def health_sampling(self):
        """
        Create monthly health sampling events with 75 fish per sample.
        Scores 9 health parameters per fish (675 total scores per event).
        
        Frequency: Every 30 days
        Sample size: 75 fish
        Parameters: Gill, Eye, Wounds, Fin, Body, Swimming, Appetite, Mucous, Color
        Stages: Post-Smolt and Adult only
        
        Based on veterinary feedback for comprehensive welfare monitoring.
        """
        # Only sample Post-Smolt (order=5) and Adult (order=6) stages
        if self.batch.lifecycle_stage.order < 5:
            return
        
        # Monthly sampling
        if self.stats['days'] % 30 != 0:
            return
        
        # Select random assignment to sample
        if not self.assignments:
            return
        
        assignment = random.choice(self.assignments)
        
        # Get all active health parameters
        health_params = list(HealthParameter.objects.filter(is_active=True))
        if not health_params:
            return  # Skip if no health parameters configured
        
        # Create sampling event
        sampling_event = HealthSamplingEvent.objects.create(
            assignment=assignment,
            sampling_date=self.current_date,
            number_of_fish_sampled=75,
            sampled_by=self.user,
            notes=f'Monthly health assessment - {self.batch.lifecycle_stage.name} stage'
        )
        
        self.stats['health_sampling_events'] += 1
        
        # Create 75 individual fish observations with measurements
        avg_weight = float(assignment.avg_weight_g)  # Convert to float for calculations
        
        # Calculate avg length from weight (simplified allometric relationship)
        # Length (cm) ≈ (Weight(g) * 1000)^(1/3) * 1.5
        avg_length = ((avg_weight * 1000) ** (1/3)) * 1.5
        
        # Track aggregate stats for event summary
        all_weights = []
        all_lengths = []
        
        fish_observations = []
        for fish_num in range(1, 76):  # 75 fish
            # Add realistic variation (±15% for weight, ±10% for length)
            fish_weight = random.gauss(avg_weight, avg_weight * 0.15)
            fish_weight = max(avg_weight * 0.5, min(avg_weight * 1.5, fish_weight))
            
            fish_length = random.gauss(avg_length, avg_length * 0.10)
            fish_length = max(avg_length * 0.7, min(avg_length * 1.3, fish_length))
            
            all_weights.append(fish_weight)
            all_lengths.append(fish_length)
            
            # Create observation (bulk create later for performance)
            fish_observations.append(
                IndividualFishObservation(
                    sampling_event=sampling_event,
                    fish_identifier=f"F{fish_num:03d}",
                    weight_g=Decimal(str(round(fish_weight, 2))),
                    length_cm=Decimal(str(round(fish_length, 2))),
                )
            )
        
        # Bulk create fish observations
        created_observations = IndividualFishObservation.objects.bulk_create(fish_observations, batch_size=100)
        self.stats['fish_observations'] += len(created_observations)
        
        # Update sampling event with aggregate statistics
        sampling_event.avg_weight_g = Decimal(str(round(sum(all_weights) / len(all_weights), 2)))
        sampling_event.avg_length_cm = Decimal(str(round(sum(all_lengths) / len(all_lengths), 2)))
        sampling_event.std_dev_weight_g = Decimal(str(round(np.std(all_weights), 2)))
        sampling_event.std_dev_length_cm = Decimal(str(round(np.std(all_lengths), 2)))
        sampling_event.min_weight_g = Decimal(str(round(min(all_weights), 2)))
        sampling_event.max_weight_g = Decimal(str(round(max(all_weights), 2)))
        sampling_event.min_length_cm = Decimal(str(round(min(all_lengths), 2)))
        sampling_event.max_length_cm = Decimal(str(round(max(all_lengths), 2)))
        sampling_event.calculated_sample_size = 75
        
        # Calculate avg K-factor (Fulton's condition factor)
        k_factors = [
            100 * (w / (l ** 3)) for w, l in zip(all_weights, all_lengths) if l > 0
        ]
        if k_factors:
            sampling_event.avg_k_factor = Decimal(str(round(sum(k_factors) / len(k_factors), 4)))
        
        sampling_event.save()
        
        # Create parameter scores for each fish
        # Score distribution: Weighted toward healthy (60% Great, 30% Fair, 8% Poor, 2% Critical)
        score_weights = [60, 30, 8, 2]  # For scores 0, 1, 2, 3
        
        parameter_scores = []
        for fish_obs in created_observations:
            for param in health_params:
                # Generate weighted random score
                score = random.choices([0, 1, 2, 3], weights=score_weights)[0]
                
                parameter_scores.append(
                    FishParameterScore(
                        individual_fish_observation=fish_obs,
                        parameter=param,
                        score=score,
                    )
                )
        
        # Bulk create all parameter scores
        FishParameterScore.objects.bulk_create(parameter_scores, batch_size=500)
        self.stats['parameter_scores'] += len(parameter_scores)
    
    def vaccination_events(self):
        """
        Create vaccination events at key lifecycle milestones.
        
        Schedule (absolute days from batch start):
        - Day 180 (Smolt stage): First vaccination
        - Day 210 (Smolt stage): Second vaccination
        - Day 280 (Post-Smolt stage): Third vaccination
        - Day 310 (Post-Smolt stage): Fourth vaccination
        
        Vaccination types (rotate): Combined, Furunculosis, IPNV, PD
        Withholding period: 21 days
        """
        day = self.stats['days']
        
        # Define vaccination schedule (absolute days from batch start)
        vaccination_days = [180, 210, 280, 310]
        
        # Check if this is a vaccination day
        if day not in vaccination_days:
            return
        
        # Get vaccination types (rotate through available types)
        vacc_types = list(VaccinationType.objects.all().order_by('name'))
        if not vacc_types:
            return  # Skip if no vaccination types configured
        
        # Select vaccination type based on which vaccination this is (0-3)
        vacc_number = vaccination_days.index(day)
        vacc_type = vacc_types[vacc_number % len(vacc_types)]
        
        stage = self.batch.lifecycle_stage.name
        
        # Vaccinate all active assignments
        for assignment in self.assignments:
            Treatment.objects.create(
                batch=self.batch,
                container=assignment.container,
                batch_assignment=assignment,
                user=self.user,
                treatment_date=timezone.make_aware(datetime.combine(
                    self.current_date, time(hour=10)
                )),
                treatment_type='vaccination',
                vaccination_type=vacc_type,
                description=f'{vacc_type.name} vaccination - {stage} stage (Day {day})',
                dosage=vacc_type.dosage or 'Standard dose',
                duration_days=1,  # Vaccination is single-day event
                withholding_period_days=21,
                outcome='successful',
            )
            
            self.stats['treatments'] += 1
        
        print(f"  ✓ Vaccinations: {vacc_type.name} administered to {len(self.assignments)} containers (Day {day})")
    
    def lice_treatment_events(self):
        """
        Create lice treatment events for Adult stage batches in sea cages.
        
        Schedule: Exactly 2 treatments per batch (Adult stage only)
        Location: Sea cages only (never freshwater)
        Timing: ~150 days and ~270 days into Adult stage
        Duration: 7 days
        Withholding: 42 days
        """
        # Only treat lice in Adult stage (order=6, sea cages)
        if self.batch.lifecycle_stage.order != 6:
            return
        
        # Check if we're at sea (not freshwater)
        if self.assignments and self.assignments[0].container.hall_id is not None:
            return  # This is freshwater, skip lice treatment
        
        # Check if we've already done 2 treatments (limit per batch)
        if self.lice_treatments_applied >= 2:
            return
        
        # Treatment days (relative to Adult stage start, not batch start)
        days_in_adult = self.stats['days'] - self.current_stage_start_day
        
        # Schedule 2 treatments: ~150 days and ~270 days into Adult stage
        # (Adult stage is ~450 days, so this gives good coverage)
        treatment_days = [150, 270]
        
        if days_in_adult not in treatment_days:
            return
        
        # Treat all active assignments (all sea cages in batch)
        treatment_count = 0
        for assignment in self.assignments:
            Treatment.objects.create(
                batch=self.batch,
                container=assignment.container,
                batch_assignment=assignment,
                user=self.user,
                treatment_date=timezone.make_aware(datetime.combine(
                    self.current_date, time(hour=9)
                )),
                treatment_type='physical',  # Lice treatment is physical treatment
                description=f'Lice treatment #{self.lice_treatments_applied + 1} - Adult stage (Day {self.stats["days"]}, Adult day {days_in_adult})',
                dosage='Bath treatment - standard concentration',
                duration_days=7,
                withholding_period_days=42,
                outcome='successful',
            )
            
            treatment_count += 1
            self.stats['treatments'] += 1
        
        self.lice_treatments_applied += 1
        print(f"  ✓ Lice Treatment #{self.lice_treatments_applied}: Applied to {treatment_count} containers (Adult day {days_in_adult})")
    
    def _generate_finance_harvest_facts(self):
        """
        Generate finance fact table entries from harvest events.
        Creates FactHarvest records for financial reporting and BI.
        """
        if not hasattr(self, 'harvest_events') or not self.harvest_events:
            return
        
        if not self.finance_company or not self.finance_site_sea:
            print("  ⚠ Finance dimensions not available, skipping fact generation")
            return
        
        try:
            facts_created = 0
            for event in self.harvest_events:
                for lot in event.lots.all():
                    FactHarvest.objects.create(
                        event_date=event.event_date,
                        quantity_kg=lot.live_weight_kg,
                        unit_count=lot.unit_count,
                        dim_batch_id=event.batch.id,
                        dim_company=self.finance_company,
                        dim_site=self.finance_site_sea,  # Harvest happens at sea
                        event=event,
                        lot=lot,
                        product_grade=lot.product_grade
                    )
                    facts_created += 1
            
            print(f"✓ Generated {facts_created} finance harvest facts")
            self.stats['finance_facts'] += facts_created
            
        except Exception as e:
            print(f"  ⚠ Finance fact generation failed: {e}")
            # Don't block harvest if finance fails
    
    def _create_transfer_workflow(self, source_assignments, dest_assignments, dest_stage):
        """
        Create BatchTransferWorkflow to document the stage transition.
        Creates auditable record with TransferAction entries for each container movement.
        
        This simulates what a user would do through the UI and provides:
        - Audit trail for regulatory compliance
        - Data for Transfers tab in batch details
        - Test data for transfer workflow features
        """
        try:
            from apps.batch.models import BatchTransferWorkflow, TransferAction
            
            # Get source stage from old assignments
            source_stage = source_assignments[0].lifecycle_stage
            
            # Generate workflow number (deterministic to avoid race conditions)
            # Use batch number + stage transition info
            # Example: FAR-2020-001 at day 90 → TRF-FAR-2020-001-D90
            workflow_number = f'TRF-{self.batch.batch_number}-D{self.stats["days"]:03d}'
            
            # Create workflow
            workflow = BatchTransferWorkflow.objects.create(
                workflow_number=workflow_number,
                batch=self.batch,
                workflow_type='LIFECYCLE_TRANSITION',
                source_lifecycle_stage=source_stage,
                dest_lifecycle_stage=dest_stage,
                status='COMPLETED',  # Auto-executed, already complete
                planned_start_date=self.current_date,
                planned_completion_date=self.current_date,
                actual_start_date=self.current_date,
                actual_completion_date=self.current_date,
                initiated_by=self.user,
                completed_by=self.user,
                notes=f'Automatic stage transition: {source_stage.name} → {dest_stage.name}',
            )
            
            # Create transfer actions (pair source and dest containers)
            # Sort both lists for consistent pairing
            source_sorted = sorted(source_assignments, key=lambda a: a.container.name)
            dest_sorted = sorted(dest_assignments, key=lambda a: a.container.name)
            
            # Pair containers (handle different counts)
            action_number = 1
            for i in range(max(len(source_sorted), len(dest_sorted))):
                source_a = source_sorted[i] if i < len(source_sorted) else None
                dest_a = dest_sorted[i] if i < len(dest_sorted) else None
                
                if source_a and dest_a:
                    # Calculate mortality during transfer (population difference)
                    source_pop = source_a.population_count
                    transferred = dest_a.population_count
                    mortality = max(0, source_pop - transferred)
                    
                    TransferAction.objects.create(
                        workflow=workflow,
                        action_number=action_number,
                        source_assignment=source_a,
                        dest_assignment=dest_a,
                        source_population_before=source_pop,
                        transferred_count=transferred,
                        mortality_during_transfer=mortality,
                        transferred_biomass_kg=dest_a.biomass_kg,
                        status='COMPLETED',
                        planned_date=self.current_date,
                        actual_execution_date=self.current_date,
                        executed_by=self.user,
                        transfer_method='PUMP',  # Standard for stage transitions
                        notes=f'Automated transfer {source_a.container.name} → {dest_a.container.name}',
                    )
                    action_number += 1
            
            # Update workflow totals
            workflow.total_actions_planned = action_number - 1
            workflow.actions_completed = action_number - 1
            workflow.completion_percentage = Decimal('100.00')
            workflow.save()
            
            # Detect intercompany (will set is_intercompany, source_subsidiary, dest_subsidiary)
            workflow.detect_intercompany()
            workflow.refresh_from_db()
            
            # Create finance transaction if intercompany (Post-Smolt → Adult)
            if workflow.is_intercompany:
                try:
                    workflow._create_intercompany_transaction()
                    if workflow.finance_transaction:
                        print(f"  ✓ Finance transaction: {workflow.finance_transaction.tx_id}")
                except Exception as e:
                    print(f"  ⚠ Finance transaction failed: {e}")
            
            print(f"  ✓ Transfer workflow: {workflow_number} ({action_number - 1} actions)")
            self.stats['transfer_workflows'] += 1
            
        except Exception as e:
            print(f"  ⚠ Transfer workflow creation failed: {e}")
            # Don't block transition if workflow creation fails
    
    def _create_initial_scenario(self):
        """
        Create initial growth forecast scenario immediately after batch creation.
        
        This provides the baseline projection that will be compared against actual growth
        in the Growth Analysis feature. Created at batch start with initial egg count.
        
        Required for: Growth Analysis feature (Actual vs Projected comparison)
        """
        try:
            # Get initial batch state
            if not self.assignments:
                print(f"  ⚠ Cannot create initial scenario: no assignments")
                return
            
            initial_pop = sum(a.population_count for a in self.assignments)
            initial_weight = self.assignments[0].avg_weight_g
            
            # Create scenario covering full lifecycle (900 days to harvest)
            scenario = Scenario.objects.create(
                name=f"Baseline Projection - {self.batch.batch_number}",
                start_date=self.start_date,
                duration_days=900,  # Full lifecycle to harvest (~3 years)
                initial_count=initial_pop,
                initial_weight=float(initial_weight),
                genotype=f"Standard {self.geography_name}",
                supplier="External",
                batch=self.batch,
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
            
            print(f"  ✓ Created baseline scenario: {scenario.name}")
            print(f"    Initial: {initial_pop:,} eggs @ {float(initial_weight):.2f}g")
            print(f"    Duration: 900 days (full lifecycle to harvest)")
            
            # Compute projection data
            try:
                from apps.scenario.services.calculations.projection_engine import ProjectionEngine
                
                print(f"    Computing projection data...")
                engine = ProjectionEngine(scenario)
                result = engine.run_projection(save_results=True)
                
                if result['success']:
                    proj_count = ScenarioProjection.objects.filter(scenario=scenario).count()
                    print(f"    ✓ Computed {proj_count} projection days")
                    
                    # Show expected harvest
                    final_proj = ScenarioProjection.objects.filter(scenario=scenario).order_by('-day_number').first()
                    if final_proj:
                        print(f"    Projected harvest: {final_proj.average_weight:.0f}g, {final_proj.population:,.0f} fish")
                else:
                    print(f"    ⚠ Projection failed: {result.get('errors', [])}")
                    
            except Exception as proj_error:
                print(f"    ⚠ Projection computation failed: {proj_error}")
            
            self.stats['scenarios'] += 1
            
            # Pin scenario to batch (required for Growth Analysis GUI)
            self.batch.pinned_scenario = scenario
            self.batch.save(update_fields=['pinned_scenario'])
            print(f"    ✓ Pinned scenario to batch")
            
        except Exception as e:
            print(f"  ⚠ Initial scenario creation failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_from_batch_scenario(self, stage_name="Parr"):
        """
        Create "from batch" style growth forecast scenario at mid-lifecycle.
        
        Uses CURRENT batch state (not historical egg state) to project FORWARD.
        This matches the "from_batch" API pattern and provides meaningful growth analysis.
        
        Called when batch reaches Parr stage (Day 180) - gives users a realistic
        "mid-lifecycle forecast" showing projected growth to harvest.
        
        Args:
            stage_name: Lifecycle stage name when scenario is created
        
        Required for Growth Analysis feature (Issue #112).
        """
        try:
            # Get current batch state from active assignments
            if not self.assignments:
                return
            
            current_pop = sum(a.population_count for a in self.assignments)
            current_weight = self.assignments[0].avg_weight_g
            
            if current_pop == 0 or not current_weight:
                print(f"  ⚠ Cannot create from-batch scenario: no population or weight data")
                return
            
            # Calculate remaining duration (to end of lifecycle)
            days_elapsed = self.stats['days']
            days_remaining = 900 - days_elapsed
            
            if days_remaining <= 0:
                return  # Batch lifecycle complete
            
            # Create scenario starting from CURRENT state, projecting FORWARD
            scenario = Scenario.objects.create(
                name=f"From Batch ({stage_name}) - {self.batch.batch_number}",
                start_date=self.current_date,  # Today, not batch start!
                duration_days=days_remaining,   # Remaining lifecycle only
                initial_count=current_pop,      # Current population
                initial_weight=float(current_weight),  # Current weight
                genotype=f"Standard {self.geography_name}",
                supplier="Internal Broodstock",
                batch=self.batch,
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
            
            print(f"  ✓ Created from-batch scenario: {scenario.name}")
            print(f"    Starting from: {current_pop:,} fish @ {float(current_weight):.1f}g ({stage_name})")
            print(f"    Duration: {days_remaining} days (to harvest)")
            
            # Compute projection data
            try:
                from apps.scenario.services.calculations.projection_engine import ProjectionEngine
                
                print(f"    Computing projection data...")
                engine = ProjectionEngine(scenario)
                result = engine.run_projection(save_results=True)
                
                if result['success']:
                    proj_count = ScenarioProjection.objects.filter(scenario=scenario).count()
                    print(f"    ✓ Computed {proj_count} projection days")
                    
                    # Show expected harvest
                    final_proj = ScenarioProjection.objects.filter(scenario=scenario).order_by('-day_number').first()
                    if final_proj:
                        print(f"    Projected harvest: {final_proj.average_weight:.0f}g, {final_proj.population:,.0f} fish")
                else:
                    print(f"    ⚠ Projection failed: {result.get('errors', [])}")
                    
            except Exception as proj_error:
                print(f"    ⚠ Projection computation failed: {proj_error}")
            
            self.stats['scenarios'] += 1
            
        except Exception as e:
            print(f"  ⚠ From-batch scenario creation failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_sea_transition_scenario(self, transition_date):
        """
        Create a growth forecast scenario when batch transitions to Adult (sea) stage.
        This gives users a realistic "From Batch" scenario at the key decision point.
        
        Uses shared models (TGC, FCR, Mortality, Temperature) to avoid duplication.
        """
        try:
            # Get current batch metrics
            current_pop = sum(a.population_count for a in self.assignments) if self.assignments else 0
            current_weight = self.assignments[0].avg_weight_g if self.assignments else 0
            
            if current_pop == 0 or current_weight == 0:
                print("  ⚠ Cannot create scenario: no population or weight data")
                return
            
            # Create scenario linked to batch
            scenario = Scenario.objects.create(
                name=f"Sea Growth Forecast - {self.batch.batch_number}",
                start_date=transition_date,
                duration_days=450,  # Adult stage duration
                initial_count=current_pop,
                initial_weight=float(current_weight),
                genotype=f"Standard {self.geography_name}",
                supplier="Internal",
                batch=self.batch,
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
            
            print(f"  ✓ Created scenario: {scenario.name}")
            print(f"    Initial: {current_pop:,} fish @ {current_weight:.0f}g")
            print(f"    Duration: 450 days (Adult stage)")
            print(f"    Models: {self.tgc_model.name}, {self.fcr_model.name}")
            
            # Compute scenario projection data
            try:
                from apps.scenario.services.calculations.projection_engine import ProjectionEngine
                
                print(f"    Computing projection data...")
                engine = ProjectionEngine(scenario)
                result = engine.run_projection(save_results=True)
                
                if result['success']:
                    print(f"    ✓ Computed {result['summary']['total_days']} projection days")
                else:
                    print(f"    ⚠ Projection failed: {result.get('errors', [])}")
                    
            except Exception as proj_error:
                print(f"    ⚠ Projection computation failed: {proj_error}")
            
            self.stats['scenarios'] += 1
            
        except Exception as e:
            print(f"  ⚠ Scenario creation failed: {e}")
            # Don't block stage transition if scenario fails
    
    def _recompute_growth_analysis(self):
        """
        Recompute ActualDailyAssignmentState for Growth Analysis.

        For test data generation, we SKIP this entirely since:
        - Orchestrator handles batch-level recomputation at the end
        - Avoids Celery/async processing during bulk generation
        - Prevents 600x slowdown in test data generation

        This generates the orange "Actual Daily State" line on Growth Analysis chart.
        """
        import os

        # SKIP during test data generation (orchestrator handles this)
        if os.environ.get('SKIP_CELERY_SIGNALS') == '1':
            print(f"\n  → Skipping individual Growth Analysis recompute (handled by orchestrator)")
            return

        try:
            from apps.batch.services.growth_assimilation import recompute_batch_assignments

            print(f"\n{'='*80}")
            print("Recomputing Growth Analysis (Actual Daily States)")
            print(f"{'='*80}\n")

            print(f"Computing ActualDailyAssignmentState records for {self.batch.batch_number}...")

            result = recompute_batch_assignments(
                batch_id=self.batch.id,
                start_date=self.batch.start_date,
                end_date=self.current_date
            )

            if result.get('total_errors', 0) == 0:
                print(f"✓ Growth Analysis computed successfully")
                print(f"  States created: {result.get('states_created', 0):,}")
                print(f"  Assignments processed: {result.get('assignments_processed', 0)}")
            else:
                print(f"⚠ Growth Analysis computation had issues:")
                for error in result.get('errors', []):
                    print(f"  - {error}")

        except Exception as e:
            print(f"\n⚠ Growth Analysis computation failed: {e}")
            print(f"   This is non-blocking - batch data is still valid")
            print(f"   Can recompute manually later via API")
    
    def should_harvest(self):
        """
        Check if batch is ready for harvest (realistic criteria).
        
        Real farms harvest based on:
        - Target weight (4-6kg for Atlantic salmon)
        - Market conditions
        - Environmental factors
        
        NOT based on fixed day count (more realistic for test data).
        """
        if not self.assignments:
            return False
        
        # Only harvest in Adult stage (order=6, final stage)
        if self.batch.lifecycle_stage.order != 6:
            return False
        
        avg_weight = self.assignments[0].avg_weight_g
        days_in_adult = self.stats['days'] - self.current_stage_start_day
        
        # Each batch has slightly different target weight (4.5-6.5kg)
        # This creates variation in harvest timing (more realistic)
        if not hasattr(self, 'target_harvest_weight'):
            if self.deterministic_harvest_target:
                # Use deterministic target from scheduler (converted to grams)
                self.target_harvest_weight = float(self.deterministic_harvest_target * 1000)
                print(f"✓ Using deterministic harvest target: {self.deterministic_harvest_target}kg ({self.target_harvest_weight}g)")
            else:
                # Generate random target for standalone execution
                self.target_harvest_weight = random.uniform(4500, 6500)
        
        # Harvest when:
        # 1. Weight reaches target (primary trigger)
        # 2. OR 450 days in Adult (max duration, force harvest)
        return (avg_weight >= self.target_harvest_weight) or (days_in_adult >= 450)
    
    def harvest_batch(self):
        """Harvest the batch (called when should_harvest() returns True)"""
        if not self.assignments:
            return
        
        avg_weight = self.assignments[0].avg_weight_g
        days_in_adult = self.stats['days'] - self.current_stage_start_day
        
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
            
            # Store harvest event for finance fact generation
            if not hasattr(self, 'harvest_events'):
                self.harvest_events = []
            self.harvest_events.append(event)
        
        # Set actual_end_date to stop age counter in UI
        self.batch.actual_end_date = self.current_date
        # Set batch status to COMPLETED (critical for GUI filtering!)
        self.batch.status = 'COMPLETED'
        self.batch.save()
        
        print(f"✓ Harvested {harvest_count} containers")
        print(f"✓ Total fish harvested: {total_harvested:,}")
        print(f"✓ Average weight: {avg_weight:.0f}g")
        print(f"✓ Total biomass: {sum(a.biomass_kg for a in self.assignments):,.0f}kg")
        print(f"✓ Batch age at harvest: {(self.current_date - self.batch.start_date).days} days")
        print(f"✓ Batch status: COMPLETED")
        
        # Generate finance harvest facts
        self._generate_finance_harvest_facts()
        print()
    
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
                
                # Check harvest readiness DAILY (weight-based trigger)
                if self.should_harvest():
                    print(f"\n  → Harvest trigger: Weight={self.assignments[0].avg_weight_g:.0f}g (target={self.target_harvest_weight:.0f}g)")
                    
                    # Recompute growth analysis BEFORE harvest (while assignments active)
                    self._recompute_growth_analysis()
                    
                    # Harvest
                    self.harvest_batch()
                    break  # Stop processing after harvest
            
            # Compute Growth Analysis if not already done
            # (harvest_batch() computes it before harvest, but non-harvested batches need it here)
            has_growth_analysis = ActualDailyAssignmentState.objects.filter(batch=self.batch).exists()
            if not has_growth_analysis:
                print(f"\n  → Computing final Growth Analysis...")
                self._recompute_growth_analysis()
            else:
                print(f"\n  → Growth Analysis already computed ({self.batch.daily_states.count()} states)")
            
            # NOTE: Growth Analysis recompute happens at orchestrator level
            # for all active batches, not per-batch (avoids duplicate work)
            
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
            print(f"  Health Sampling Events: {self.stats['health_sampling_events']:,} (monthly, 75 fish)")
            print(f"  Fish Observations: {self.stats['fish_observations']:,}")
            print(f"  Parameter Scores: {self.stats['parameter_scores']:,} (9 params per fish)")
            print(f"  Treatments: {self.stats['treatments']:,} (vaccinations + delousing)")
            print(f"  Feed Purchases: {self.stats['purchases']:,}")
            print(f"  Transfer Workflows: {self.stats['transfer_workflows']:,} (stage transitions)")
            print(f"  Scenarios: {self.stats['scenarios']:,} (sea transition forecast)")
            print(f"  Finance Facts: {self.stats['finance_facts']:,} (harvest facts)")
            
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
    parser.add_argument('--station', type=str, default=None,
                       help='DETERMINISTIC: Specific station name to use (eliminates race conditions)')
    parser.add_argument('--batch-number', type=str, default=None,
                       help='DETERMINISTIC: Pre-assigned batch number from schedule (eliminates race conditions)')
    parser.add_argument('--use-schedule', action='store_true',
                       help='Use pre-allocated containers from CONTAINER_SCHEDULE env var')
    args = parser.parse_args()

    start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  Phase 3: Chronological Event Engine".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "═" * 78 + "╝\n")
    
    engine = EventEngine(start, args.eggs, args.geography, args.duration, args.station, args.batch_number)
    return engine.run()

if __name__ == '__main__':
    sys.exit(main())
