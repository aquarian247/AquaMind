#!/usr/bin/env python
"""
FishTalk to AquaMind Migration Script
Version: 1.0
Date: December 2024

This script handles the migration of data from FishTalk to AquaMind,
focusing on active batches and related operational data.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import pyodbc

# Add parent directory to path for Django imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django
django.setup()
assert_default_db_is_migration_db()

from django.db import transaction, connection
from django.utils import timezone
from django.contrib.auth.models import User

# Import AquaMind models
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, 
    Container, ContainerType, Sensor, FeedContainer
)
from apps.batch.models import (
    Batch, Species, LifeCycleStage, BatchContainerAssignment,
    MortalityEvent, GrowthSample, BatchTransfer
)
from apps.inventory.models import (
    Feed, FeedingEvent, FeedStock, FeedPurchase,
    BatchFeedingSummary
)
from apps.health.models import (
    JournalEntry, MortalityRecord, Treatment, 
    VaccinationType, LiceCount, HealthLabSample
)
from apps.environmental.models import (
    EnvironmentalParameter, EnvironmentalReading
)
from apps.users.models import UserProfile
from apps.broodstock.models import (
    BroodstockFish, BreedingPair, EggProduction
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FishTalkMigration:
    """Main migration class for FishTalk to AquaMind data transfer"""
    
    def __init__(self, config_file='migration_config.json'):
        """Initialize migration with configuration"""
        self.config = self.load_config(config_file)
        self.fishtalk_conn = None
        self.mapping_cache = {}
        self.error_log = []
        self.stats = {
            'total_records': 0,
            'migrated': 0,
            'errors': 0,
            'warnings': 0
        }
        
    def load_config(self, config_file):
        """Load migration configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            'fishtalk': {
                'driver': '{ODBC Driver 17 for SQL Server}',
                'server': 'localhost',
                'database': 'FishTalk',
                'uid': 'sa',
                'pwd': 'password'
            },
            'batch_size': 1000,
            'active_only': True,
            'cutoff_date': '2023-01-01',
            'dry_run': False
        }
    
    def connect_fishtalk(self):
        """Establish connection to FishTalk SQL Server database"""
        try:
            conn_str = (
                f"DRIVER={self.config['fishtalk']['driver']};"
                f"SERVER={self.config['fishtalk']['server']};"
                f"DATABASE={self.config['fishtalk']['database']};"
                f"UID={self.config['fishtalk']['uid']};"
                f"PWD={self.config['fishtalk']['pwd']}"
            )
            self.fishtalk_conn = pyodbc.connect(conn_str)
            logger.info("Successfully connected to FishTalk database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FishTalk: {e}")
            return False
    
    def disconnect_fishtalk(self):
        """Close FishTalk database connection"""
        if self.fishtalk_conn:
            self.fishtalk_conn.close()
            logger.info("Disconnected from FishTalk database")
    
    # =================== MAPPING FUNCTIONS ===================
    
    def map_status(self, fishtalk_status):
        """Map FishTalk status to AquaMind status"""
        status_map = {
            'Active': 'ACTIVE',
            'Inactive': 'INACTIVE',
            'Planned': 'PLANNED',
            'Completed': 'CLOSED',
            'Terminated': 'CLOSED',
            'OnHold': 'INACTIVE'
        }
        return status_map.get(fishtalk_status, 'INACTIVE')
    
    def map_lifecycle_stage(self, fishtalk_stage):
        """Map FishTalk lifecycle stage to AquaMind stage"""
        stage_map = {
            'Egg': 'Egg',
            'Alevin': 'Fry',
            'Fry': 'Fry',
            'Parr': 'Parr',
            'Smolt': 'Smolt',
            'Post-Smolt': 'Post-Smolt',
            'Grower': 'Adult',
            'Harvest': 'Adult'
        }
        mapped_stage = stage_map.get(fishtalk_stage, 'Fry')
        
        # Get or create the stage
        stage, created = LifeCycleStage.objects.get_or_create(
            name=mapped_stage,
            defaults={'description': f'Migrated from FishTalk: {fishtalk_stage}'}
        )
        return stage
    
    def map_container_type(self, fishtalk_type):
        """Map FishTalk unit type to AquaMind container type"""
        type_map = {
            'Tank': 'TANK',
            'Pen': 'PEN',
            'Cage': 'PEN',
            'Tray': 'TRAY',
            'Incubator': 'TRAY',
            'Other': 'OTHER'
        }
        category = type_map.get(fishtalk_type, 'OTHER')
        
        # Get or create container type
        container_type, created = ContainerType.objects.get_or_create(
            name=fishtalk_type,
            defaults={
                'category': category,
                'description': f'Migrated from FishTalk'
            }
        )
        return container_type
    
    def convert_to_utc(self, dt_value, source_tz='Europe/London'):
        """Convert FishTalk datetime to UTC"""
        if not dt_value:
            return None
        if isinstance(dt_value, str):
            dt_value = datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
        # Add timezone awareness and convert to UTC
        from zoneinfo import ZoneInfo
        local_dt = dt_value.replace(tzinfo=ZoneInfo(source_tz))
        return local_dt.astimezone(ZoneInfo('UTC'))
    
    # =================== EXTRACTION FUNCTIONS ===================
    
    def extract_infrastructure(self):
        """Extract infrastructure data from FishTalk"""
        logger.info("Extracting infrastructure data...")
        cursor = self.fishtalk_conn.cursor()
        
        # Extract Sites from PlanSite
        cursor.execute("""
            SELECT DISTINCT ps.PlanSiteID, ps.SiteName, ps.Description, 
                   ps.OrgUnitID, ps.CreatedDate, ps.ModifiedDate
            FROM PlanSite ps
            WHERE ps.IsActive = 1
        """)
        sites = cursor.fetchall()
        logger.info(f"Found {len(sites)} active sites")
        
        # Extract Container data
        cursor.execute("""
            SELECT c.ContainerID, c.ContainerName, c.ContainerType, 
                   c.PlanSiteID, c.Capacity, c.Volume, c.IsActive
            FROM Containers c
            WHERE c.IsActive = 1 OR c.IsActive IS NULL
        """)
        containers = cursor.fetchall()
        logger.info(f"Found {len(containers)} containers")
        
        # Extract Plan Containers (current assignments)
        cursor.execute("""
            SELECT pc.PlanContainerID, pc.ContainerID, pc.PlanSiteID,
                   pc.StartDate, pc.EndDate
            FROM PlanContainer pc
            WHERE pc.EndDate IS NULL OR pc.EndDate > GETDATE()
        """)
        plan_containers = cursor.fetchall()
        logger.info(f"Found {len(plan_containers)} active plan containers")
        
        return {
            'sites': sites,
            'containers': containers,
            'plan_containers': plan_containers
        }
    
    def extract_active_batches(self):
        """Extract active batch data from FishTalk"""
        logger.info("Extracting active batch data...")
        cursor = self.fishtalk_conn.cursor()
        
        # Extract Populations (Batches) - Using Ext_Populations_v2 or fallback to Populations
        cursor.execute("""
            SELECT p.PopulationID, p.PopulationName, p.SpeciesID, 
                   p.StartTime, pp.Status, pa.ProductionStage,
                   pp.ExpectedEndDate, pp.ActualEndDate,
                   prop.Notes, pa.YearClass
            FROM Populations p
            LEFT JOIN PublicPlanPopulation pp ON p.PopulationID = pp.PopulationID
            LEFT JOIN PopulationAttributes pa ON p.PopulationID = pa.PopulationID
            LEFT JOIN PopulationProperty prop ON p.PopulationID = prop.PopulationID
            WHERE pp.Status IN ('Active', 'Running', 'InProduction')
               OR p.IsActive = 1
        """)
        populations = cursor.fetchall()
        logger.info(f"Found {len(populations)} active populations/batches")
        
        # Extract Plan Population assignments (Container Assignments)
        population_ids = [str(p[0]) for p in populations]  # Convert GUIDs to strings
        if population_ids:
            placeholders = ','.join(['?'] * len(population_ids))
            cursor.execute(f"""
                SELECT pp.PlanPopulationID, pp.PopulationID, pc.ContainerID,
                       pa.ProductionStage, pp.Count, pp.AvgWeight, 
                       pp.Biomass, pc.StartDate, pc.EndDate,
                       pc.IsActive, us.SampleDate
                FROM PlanPopulation pp
                JOIN PlanContainer pc ON pp.PlanContainerID = pc.PlanContainerID
                LEFT JOIN PopulationAttributes pa ON pp.PopulationID = pa.PopulationID
                LEFT JOIN (
                    SELECT PopulationID, MAX(SampleDate) as SampleDate
                    FROM UserSample
                    GROUP BY PopulationID
                ) us ON pp.PopulationID = us.PopulationID
                WHERE pp.PopulationID IN ({placeholders})
                  AND (pc.IsActive = 1 OR pc.EndDate IS NULL OR pc.EndDate > GETDATE())
            """, population_ids)
            assignments = cursor.fetchall()
            logger.info(f"Found {len(assignments)} active container assignments")
        else:
            assignments = []
        
        return {
            'populations': populations,
            'assignments': assignments
        }
    
    def extract_feed_data(self):
        """Extract feed and inventory data from FishTalk"""
        logger.info("Extracting feed data...")
        cursor = self.fishtalk_conn.cursor()
        
        # Note: Feed type master data may need to be manually configured
        # as FishTalk uses feed batch IDs rather than feed types
        
        # Extract Feeding Events from multiple sources (last 12 months)
        cutoff_date = self.config.get('migration', {}).get('cutoff_date', '2023-01-01')
        
        # Main feeding table
        cursor.execute("""
            SELECT f.FeedingID, f.PopulationID, f.ContainerID, 
                   f.FeedBatchID, f.FeedingTime, f.FeedAmount,
                   pfu.Biomass, f.FeedPercent, f.Method,
                   f.Notes, f.UserID
            FROM Feeding f
            LEFT JOIN PlanStatusFeedUse pfu ON f.PopulationID = pfu.PopulationID
                AND CAST(f.FeedingTime as DATE) = pfu.Date
            WHERE f.FeedingTime >= ?
        """, cutoff_date)
        feedings = cursor.fetchall()
        logger.info(f"Found {len(feedings)} feeding events since {cutoff_date}")
        
        # Hardware/Automatic feeding
        cursor.execute("""
            SELECT hw.FeedingID, hw.PopulationID, hw.HWUnitID as ContainerID,
                   hw.FeedBatchID, hw.FeedingTime, hw.FeedAmount,
                   NULL as Biomass, NULL as FeedPercent, 'AUTOMATIC' as Method,
                   hw.Notes, hw.UserID
            FROM HWFeeding hw
            WHERE hw.FeedingTime >= ?
        """, cutoff_date)
        hw_feedings = cursor.fetchall()
        logger.info(f"Found {len(hw_feedings)} hardware feeding events")
        
        return {
            'feedings': feedings,
            'hw_feedings': hw_feedings
        }
    
    def extract_health_data(self):
        """Extract health and medical data from FishTalk"""
        logger.info("Extracting health data...")
        cursor = self.fishtalk_conn.cursor()
        
        cutoff_date = self.config.get('migration', {}).get('cutoff_date', '2023-01-01')
        
        # Extract Mortality Records
        cursor.execute("""
            SELECT m.MortalityID, m.PopulationID, m.ContainerID, 
                   m.MortalityDate, m.Count, m.Cause, m.Description,
                   mr.ResponsibleParty
            FROM Mortality m
            LEFT JOIN MortalityResponsibility mr ON m.MortalityID = mr.MortalityID
            WHERE m.MortalityDate >= ?
        """, cutoff_date)
        mortality = cursor.fetchall()
        logger.info(f"Found {len(mortality)} mortality records")
        
        # Extract User Samples (health observations)
        cursor.execute("""
            SELECT us.SampleID, us.PopulationID, us.ContainerID,
                   us.SampleDate, us.SampleType, uspv.ParameterID,
                   uspv.Value, us.Notes, us.UserID
            FROM UserSample us
            LEFT JOIN UserSampleParameterValue uspv ON us.SampleID = uspv.SampleID
            WHERE us.SampleDate >= ?
        """, cutoff_date)
        samples = cursor.fetchall()
        logger.info(f"Found {len(samples)} user sample records")
        
        # Extract Lice Sample Data
        cursor.execute("""
            SELECT lsd.SampleID, lsd.PopulationID, lsd.ContainerID,
                   lsd.SampleDate, lsd.AdultFemale, lsd.AdultMale, 
                   lsd.Juvenile, lsd.FishSampled, lsd.Notes
            FROM PublicLiceSampleData lsd
            WHERE lsd.SampleDate >= ?
        """, cutoff_date)
        lice_samples = cursor.fetchall()
        logger.info(f"Found {len(lice_samples)} lice sample records")
        
        # Extract Weight Samples
        cursor.execute("""
            SELECT ws.SampleID, ws.PopulationID, ws.ContainerID,
                   ws.SampleDate, ws.AvgWeight, ws.StdDev, 
                   ws.MinWeight, ws.MaxWeight, ws.SampleSize
            FROM PublicWeightSamples ws
            WHERE ws.SampleDate >= ?
        """, cutoff_date)
        weight_samples = cursor.fetchall()
        logger.info(f"Found {len(weight_samples)} weight sample records")
        
        return {
            'mortality': mortality,
            'samples': samples,
            'lice_samples': lice_samples,
            'weight_samples': weight_samples
        }
    
    # =================== LOADING FUNCTIONS ===================
    
    @transaction.atomic
    def load_infrastructure(self, data):
        """Load infrastructure data into AquaMind"""
        logger.info("Loading infrastructure data...")
        
        # Load Sites as Geography
        for site in data['sites']:
            site_id, name, desc, country, created, modified = site
            
            geography, created = Geography.objects.get_or_create(
                name=name,
                defaults={
                    'description': f"{desc or ''}\nCountry: {country}" if country else desc,
                    'created_at': self.convert_to_utc(created) or timezone.now(),
                    'updated_at': self.convert_to_utc(modified) or timezone.now()
                }
            )
            self.mapping_cache[f'site_{site_id}'] = geography.id
            logger.debug(f"Loaded geography: {name}")
        
        # Load Locations as Areas
        for location in data['locations']:
            loc_id, name, site_id, lat, lon, max_bio, status = location
            
            area, created = Area.objects.get_or_create(
                name=name,
                geography_id=self.mapping_cache.get(f'site_{site_id}'),
                defaults={
                    'latitude': Decimal(str(lat)) if lat else None,
                    'longitude': Decimal(str(lon)) if lon else None,
                    'max_biomass': Decimal(str(max_bio)) if max_bio else None,
                    'active': status == 'Active'
                }
            )
            self.mapping_cache[f'location_{loc_id}'] = area.id
            logger.debug(f"Loaded area: {name}")
        
        # Load Units as Containers
        for unit in data['units']:
            unit_id, name, unit_type, hall, area, volume, max_bio, active = unit
            
            container_type = self.map_container_type(unit_type)
            
            container, created = Container.objects.get_or_create(
                name=name,
                defaults={
                    'container_type': container_type,
                    'area_id': self.mapping_cache.get(f'location_{area}') if area else None,
                    'volume_m3': Decimal(str(volume)) if volume else None,
                    'max_biomass_kg': Decimal(str(max_bio)) if max_bio else None,
                    'active': bool(active)
                }
            )
            self.mapping_cache[f'unit_{unit_id}'] = container.id
            logger.debug(f"Loaded container: {name}")
        
        logger.info(f"Loaded {len(data['sites'])} geographies, "
                   f"{len(data['locations'])} areas, "
                   f"{len(data['units'])} containers")
    
    @transaction.atomic
    def load_batches(self, data):
        """Load batch data into AquaMind"""
        logger.info("Loading batch data...")
        
        # Ensure we have a default species
        default_species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        
        # Load Projects as Batches
        for project in data['projects']:
            (proj_id, name, species_name, stage_name, status, batch_type,
             start_date, exp_end, actual_end, notes, year_class, created, modified) = project
            
            # Get or create species
            if species_name:
                species, _ = Species.objects.get_or_create(
                    name=species_name,
                    defaults={'scientific_name': species_name}
                )
            else:
                species = default_species
            
            # Map lifecycle stage
            stage = self.map_lifecycle_stage(stage_name)
            
            # Prepare notes with year class
            full_notes = notes or ''
            if year_class:
                full_notes += f"\nYear Class: {year_class}"
            
            # Create batch with FT- prefix
            batch_number = f"FT-{name}" if not name.startswith('FT-') else name
            
            batch, created = Batch.objects.get_or_create(
                batch_number=batch_number,
                defaults={
                    'species': species,
                    'lifecycle_stage': stage,
                    'status': self.map_status(status),
                    'batch_type': batch_type or 'STANDARD',
                    'start_date': start_date,
                    'expected_end_date': exp_end,
                    'actual_end_date': actual_end,
                    'notes': full_notes.strip(),
                    'created_at': self.convert_to_utc(created) or timezone.now(),
                    'updated_at': self.convert_to_utc(modified) or timezone.now()
                }
            )
            self.mapping_cache[f'project_{proj_id}'] = batch.id
            logger.debug(f"Loaded batch: {batch_number}")
        
        # Load Individuals as Container Assignments
        for individual in data['individuals']:
            (ind_id, proj_id, unit_id, stage_name, count, avg_weight,
             biomass, date_assigned, date_removed, active, last_weighing) = individual
            
            batch_id = self.mapping_cache.get(f'project_{proj_id}')
            container_id = self.mapping_cache.get(f'unit_{unit_id}')
            
            if not batch_id or not container_id:
                logger.warning(f"Skipping individual {ind_id}: missing batch or container mapping")
                continue
            
            stage = self.map_lifecycle_stage(stage_name)
            
            # Convert weight from kg to grams
            avg_weight_g = Decimal(str(avg_weight * 1000)) if avg_weight else None
            
            assignment = BatchContainerAssignment.objects.create(
                batch_id=batch_id,
                container_id=container_id,
                lifecycle_stage=stage,
                population_count=count or 0,
                avg_weight_g=avg_weight_g,
                biomass_kg=Decimal(str(biomass)) if biomass else Decimal('0'),
                assignment_date=date_assigned or timezone.now().date(),
                departure_date=date_removed,
                is_active=bool(active),
                last_weighing_date=last_weighing,
                notes=f"Migrated from FishTalk Individual ID: {ind_id}"
            )
            logger.debug(f"Created container assignment for batch {batch_id}")
        
        logger.info(f"Loaded {len(data['projects'])} batches, "
                   f"{len(data['individuals'])} container assignments")
    
    @transaction.atomic
    def load_feed_data(self, data):
        """Load feed and inventory data into AquaMind"""
        logger.info("Loading feed data...")
        
        # Load Feed Types
        for feed_type in data['feed_types']:
            (feed_id, name, brand, size, size_cat, protein,
             fat, carbs, desc, active) = feed_type
            
            # Map size category
            size_category_map = {
                'Micro': 'MICRO',
                'Small': 'SMALL',
                'Medium': 'MEDIUM',
                'Large': 'LARGE'
            }
            size_category = size_category_map.get(size_cat, 'MEDIUM')
            
            feed, created = Feed.objects.get_or_create(
                name=name,
                brand=brand or 'Unknown',
                defaults={
                    'size_category': size_category,
                    'pellet_size_mm': Decimal(str(size)) if size else None,
                    'protein_percentage': Decimal(str(protein)) if protein else None,
                    'fat_percentage': Decimal(str(fat)) if fat else None,
                    'carbohydrate_percentage': Decimal(str(carbs)) if carbs else None,
                    'description': desc or '',
                    'is_active': bool(active)
                }
            )
            self.mapping_cache[f'feed_{feed_id}'] = feed.id
            logger.debug(f"Loaded feed type: {name}")
        
        # Load Feeding Events
        for feeding in data['feedings']:
            (feeding_id, proj_id, unit_id, feed_id, feed_date,
             feed_time, amount, biomass, feed_percent, method,
             notes, recorded_by) = feeding
            
            batch_id = self.mapping_cache.get(f'project_{proj_id}')
            container_id = self.mapping_cache.get(f'unit_{unit_id}')
            feed_obj_id = self.mapping_cache.get(f'feed_{feed_id}')
            
            if not all([batch_id, container_id, feed_obj_id]):
                logger.warning(f"Skipping feeding {feeding_id}: missing references")
                continue
            
            # Map feeding method
            method_map = {
                'Manual': 'MANUAL',
                'Automatic': 'AUTOMATIC',
                'Broadcast': 'BROADCAST'
            }
            feeding_method = method_map.get(method, 'MANUAL')
            
            feeding_event = FeedingEvent.objects.create(
                batch_id=batch_id,
                container_id=container_id,
                feed_id=feed_obj_id,
                feeding_date=feed_date,
                feeding_time=feed_time or datetime.now().time(),
                amount_kg=Decimal(str(amount)) if amount else Decimal('0'),
                batch_biomass_kg=Decimal(str(biomass)) if biomass else Decimal('0'),
                feeding_percentage=Decimal(str(feed_percent)) if feed_percent else None,
                method=feeding_method,
                notes=notes or ''
            )
            logger.debug(f"Created feeding event for batch {batch_id}")
        
        logger.info(f"Loaded {len(data['feed_types'])} feed types, "
                   f"{len(data['feedings'])} feeding events")
    
    @transaction.atomic
    def load_health_data(self, data):
        """Load health and medical data into AquaMind"""
        logger.info("Loading health data...")
        
        # Load Health Journal Entries
        for health_log in data['health_logs']:
            (log_id, proj_id, unit_id, log_date, category,
             severity, description, resolution, res_notes, user_id) = health_log
            
            batch_id = self.mapping_cache.get(f'project_{proj_id}')
            container_id = self.mapping_cache.get(f'unit_{unit_id}')
            
            if not batch_id:
                logger.warning(f"Skipping health log {log_id}: missing batch")
                continue
            
            # Map category
            category_map = {
                'Observation': 'observation',
                'Issue': 'issue',
                'Action': 'action',
                'Diagnosis': 'diagnosis',
                'Treatment': 'treatment'
            }
            mapped_category = category_map.get(category, 'observation')
            
            # Map severity
            severity_map = {
                'Low': 'low',
                'Medium': 'medium',
                'High': 'high'
            }
            mapped_severity = severity_map.get(severity, 'low')
            
            # Get default user if not mapped
            default_user = User.objects.filter(is_superuser=True).first()
            
            journal = JournalEntry.objects.create(
                batch_id=batch_id,
                container_id=container_id,
                user=default_user,  # Will need proper user mapping
                entry_date=self.convert_to_utc(log_date) or timezone.now(),
                category=mapped_category,
                severity=mapped_severity,
                description=description or '',
                resolution_status=bool(resolution),
                resolution_notes=res_notes or ''
            )
            logger.debug(f"Created journal entry for batch {batch_id}")
        
        # Load Mortality Events
        for mort in data['mortality']:
            mort_id, proj_id, date, count, cause, description = mort
            
            batch_id = self.mapping_cache.get(f'project_{proj_id}')
            if not batch_id:
                logger.warning(f"Skipping mortality {mort_id}: missing batch")
                continue
            
            # Get active assignment for the batch
            active_assignment = BatchContainerAssignment.objects.filter(
                batch_id=batch_id,
                is_active=True
            ).first()
            
            if active_assignment:
                mortality = MortalityEvent.objects.create(
                    batch_id=batch_id,
                    assignment=active_assignment,
                    event_date=date,
                    count=count or 0,
                    cause=cause or 'Unknown',
                    description=description or ''
                )
            else:
                # Legacy support - create without assignment if no active assignment
                mortality = MortalityEvent.objects.create(
                    batch_id=batch_id,
                    assignment=None,
                    event_date=date,
                    count=count or 0,
                    cause=cause or 'Unknown',
                    description=description or ''
                )
            logger.debug(f"Created mortality event for batch {batch_id}")
        
        # Load Treatments
        for treatment in data['treatments']:
            (treat_id, proj_id, unit_id, treat_date, treat_type,
             description, dosage, duration, withdrawal) = treatment
            
            batch_id = self.mapping_cache.get(f'project_{proj_id}')
            container_id = self.mapping_cache.get(f'unit_{unit_id}')
            
            if not batch_id:
                logger.warning(f"Skipping treatment {treat_id}: missing batch")
                continue
            
            # Map treatment type
            type_map = {
                'Medication': 'medication',
                'Vaccination': 'vaccination',
                'Delicing': 'delicing',
                'Other': 'other'
            }
            treatment_type = type_map.get(treat_type, 'other')
            
            # Get default user
            default_user = User.objects.filter(is_superuser=True).first()
            
            treat_obj = Treatment.objects.create(
                batch_id=batch_id,
                container_id=container_id,
                user=default_user,
                treatment_date=self.convert_to_utc(treat_date) or timezone.now(),
                treatment_type=treatment_type,
                description=description or '',
                dosage=dosage or '',
                duration_days=duration or 0,
                withholding_period_days=withdrawal or 0
            )
            logger.debug(f"Created treatment for batch {batch_id}")
        
        logger.info(f"Loaded {len(data['health_logs'])} journal entries, "
                   f"{len(data['mortality'])} mortality events, "
                   f"{len(data['treatments'])} treatments")
    
    # =================== VALIDATION FUNCTIONS ===================
    
    def validate_migration(self):
        """Validate the migrated data"""
        logger.info("Validating migration...")
        
        validation_results = {
            'batch_count': Batch.objects.filter(batch_number__startswith='FT-').count(),
            'container_count': Container.objects.count(),
            'assignment_count': BatchContainerAssignment.objects.filter(
                batch__batch_number__startswith='FT-'
            ).count(),
            'feeding_count': FeedingEvent.objects.filter(
                batch__batch_number__startswith='FT-'
            ).count(),
            'health_count': JournalEntry.objects.filter(
                batch__batch_number__startswith='FT-'
            ).count()
        }
        
        logger.info("Validation Results:")
        for key, value in validation_results.items():
            logger.info(f"  {key}: {value}")
        
        return validation_results
    
    def generate_reconciliation_report(self):
        """Generate a reconciliation report"""
        logger.info("Generating reconciliation report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'errors': self.error_log,
            'validation': self.validate_migration()
        }
        
        # Save report to file
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Reconciliation report saved to {report_file}")
        return report
    
    # =================== MAIN EXECUTION ===================
    
    def run_migration(self):
        """Execute the complete migration process"""
        logger.info("=" * 80)
        logger.info("Starting FishTalk to AquaMind Migration")
        logger.info("=" * 80)
        
        try:
            # Connect to FishTalk
            if not self.connect_fishtalk():
                logger.error("Failed to connect to FishTalk. Aborting migration.")
                return False
            
            # Phase 1: Infrastructure
            logger.info("\nPhase 1: Infrastructure Migration")
            infrastructure_data = self.extract_infrastructure()
            if not self.config.get('dry_run'):
                self.load_infrastructure(infrastructure_data)
            
            # Phase 2: Active Batches
            logger.info("\nPhase 2: Active Batches Migration")
            batch_data = self.extract_active_batches()
            if not self.config.get('dry_run'):
                self.load_batches(batch_data)
            
            # Phase 3: Feed & Inventory
            logger.info("\nPhase 3: Feed & Inventory Migration")
            feed_data = self.extract_feed_data()
            if not self.config.get('dry_run'):
                self.load_feed_data(feed_data)
            
            # Phase 4: Health Records
            logger.info("\nPhase 4: Health Records Migration")
            health_data = self.extract_health_data()
            if not self.config.get('dry_run'):
                self.load_health_data(health_data)
            
            # Validation
            logger.info("\nPhase 5: Validation")
            self.validate_migration()
            
            # Generate report
            self.generate_reconciliation_report()
            
            logger.info("\n" + "=" * 80)
            logger.info("Migration completed successfully!")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False
        
        finally:
            self.disconnect_fishtalk()


def main():
    """Main entry point for the migration script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FishTalk to AquaMind Migration')
    parser.add_argument('--config', default='migration_config.json',
                      help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true',
                      help='Perform extraction only, no loading')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create migration instance
    migration = FishTalkMigration(args.config)
    
    if args.dry_run:
        migration.config['dry_run'] = True
        logger.info("Running in DRY RUN mode - no data will be loaded")
    
    # Run migration
    success = migration.run_migration()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
