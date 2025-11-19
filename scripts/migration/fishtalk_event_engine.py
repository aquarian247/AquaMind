#!/usr/bin/env python3
"""
FishTalk to AquaMind Migration Event Engine
Adapts the test data generation event engine to migrate real FishTalk data

This script reads batch lifecycle data from FishTalk and replays it chronologically
into AquaMind, creating proper audit trails and maintaining data integrity.
"""

import os, sys, django, json, random, argparse, pyodbc
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from collections import defaultdict

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

User = get_user_model()

class FishTalkEventEngine:
    """
    Migration event engine that adapts test data generation patterns
    to migrate real FishTalk data chronologically.
    """

    def __init__(self, fishtalk_config, batch_id=None):
        self.fishtalk_config = fishtalk_config
        self.batch_id = batch_id  # FishTalk PopulationID to migrate
        self.fishtalk_conn = None
        self.stats = {'days': 0, 'env': 0, 'feed': 0, 'mort': 0, 'growth': 0, 'purchases': 0, 'lice': 0, 'scenarios': 0, 'finance_facts': 0}

        # Migration mappings
        self.batch_mapping = {}  # FishTalk PopulationID -> AquaMind Batch ID
        self.container_mapping = {}  # FishTalk ContainerID -> AquaMind Container ID
        self.user_mapping = {}  # FishTalk UserID -> AquaMind User ID

    def connect_fishtalk(self):
        """Establish FishTalk database connection (or use mock data for testing)"""
        try:
            # For development/demo, use mock data instead of real connection
            if os.environ.get('USE_MOCK_FISHTALK', 'true').lower() == 'true':
                print(f"🧪 Using mock FishTalk data for development")
                self.fishtalk_conn = 'mock'
                return True

            # Real connection
            conn_str = (
                f"DRIVER={self.fishtalk_config['driver']};"
                f"SERVER={self.fishtalk_config['server']};"
                f"DATABASE={self.fishtalk_config['database']};"
                f"UID={self.fishtalk_config['uid']};"
                f"PWD={self.fishtalk_config['pwd']};"
                f"PORT={self.fishtalk_config.get('port', 1433)}"
            )

            self.fishtalk_conn = pyodbc.connect(conn_str)
            print(f"✅ Connected to FishTalk database")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to FishTalk: {e}")
            return False

    def disconnect_fishtalk(self):
        """Close FishTalk connection"""
        if self.fishtalk_conn and self.fishtalk_conn != 'mock':
            self.fishtalk_conn.close()
            print("🔌 Disconnected from FishTalk database")

    def _get_mock_batches(self):
        """Return mock FishTalk batch data for testing"""
        from datetime import datetime

        return [
            # (pop_id, pop_name, species_id, start_time, status, prod_stage, exp_end, actual_end, notes, year_class)
            (1001, 'FI-2024-001', 1, datetime(2024, 1, 1), 'Active', 'Fry', None, None, 'Mock batch 1', 2024),
            (1002, 'FI-2024-002', 1, datetime(2024, 2, 15), 'Active', 'Parr', None, None, 'Mock batch 2', 2024),
        ]

    def _get_mock_assignments(self, population_id):
        """Return mock assignment data for a population"""
        from datetime import date

        # Mock assignments for batch progression
        mock_data = {
            1001: [  # FI-2024-001: Egg&Alevin -> Fry -> Parr
                (2001, 3001, 'Egg', 35000, 0.1, 3.5, date(2024, 1, 1), date(2024, 4, 1), False, None),
                (2002, 3002, 'Fry', 34800, 5.2, 180.0, date(2024, 4, 1), date(2024, 7, 1), False, date(2024, 6, 15)),
                (2003, 3003, 'Parr', 34600, 52.5, 1800.0, date(2024, 7, 1), None, True, date(2024, 10, 1)),
            ],
            1002: [  # FI-2024-002: Fry -> Parr -> Smolt
                (2004, 3004, 'Fry', 32000, 8.5, 280.0, date(2024, 2, 15), date(2024, 5, 15), False, None),
                (2005, 3005, 'Parr', 31800, 55.0, 1750.0, date(2024, 5, 15), date(2024, 8, 15), False, None),
                (2006, 3006, 'Smolt', 31500, 148.7, 4700.0, date(2024, 8, 15), None, True, date(2024, 11, 1)),
            ]
        }

        return mock_data.get(population_id, [])

    def _get_mock_feeding_events(self, population_id):
        """Return mock feeding events"""
        from datetime import datetime

        # Note: Population ID in the data structure should match what gets stored in batch_mapping
        # The population_id here is the FishTalk ID (1001, 1002), but the lookup uses the stored mapping
        mock_data = {
            1001: [  # Some feeding events for FI-2024-001
                (4001, 3002, 5001, datetime(2024, 4, 15, 8, 0), 25.5, 180.0, 1.2, 'AUTOMATIC', 'Morning feed'),
                (4002, 3002, 5001, datetime(2024, 4, 15, 16, 0), 26.0, 185.0, 1.2, 'AUTOMATIC', 'Evening feed'),
                (4003, 3003, 5002, datetime(2024, 7, 15, 8, 0), 45.0, 1800.0, 1.5, 'AUTOMATIC', 'Morning feed'),
            ],
            1002: [  # Some feeding events for FI-2024-002
                (4004, 3005, 5002, datetime(2024, 6, 1, 8, 0), 38.0, 1750.0, 1.4, 'AUTOMATIC', 'Morning feed'),
                (4005, 3006, 5003, datetime(2024, 9, 1, 8, 0), 52.0, 4700.0, 1.3, 'AUTOMATIC', 'Morning feed'),
            ]
        }

        return mock_data.get(population_id, [])

    def _get_mock_mortality_events(self, population_id):
        """Return mock mortality events"""
        from datetime import date

        mock_data = {
            1001: [
                (6001, 3002, date(2024, 5, 1), 50, 'Disease', 'Gill disease outbreak'),
                (6002, 3003, date(2024, 8, 1), 30, 'Stress', 'Temperature stress'),
            ],
            1002: [
                (6003, 3005, date(2024, 6, 15), 25, 'Predation', 'Bird predation'),
            ]
        }

        return mock_data.get(population_id, [])

    def _get_mock_growth_samples(self, population_id):
        """Return mock growth samples"""
        from datetime import date

        mock_data = {
            1001: [
                (7001, 3002, date(2024, 6, 15), 5.2, 0.3, 4.8, 5.8, 50),
                (7002, 3003, date(2024, 10, 1), 52.5, 5.2, 45.0, 62.0, 45),
            ],
            1002: [
                (7003, 3005, date(2024, 7, 1), 55.0, 6.1, 48.0, 65.0, 40),
                (7004, 3006, date(2024, 11, 1), 148.7, 12.5, 130.0, 170.0, 35),
            ]
        }

        return mock_data.get(population_id, [])

    def _get_mock_health_events(self, population_id):
        """Return mock health events"""
        from datetime import date

        mock_data = {
            1001: [
                (8001, 3002, date(2024, 6, 1), 'Gill Check', 1, 85.0, 'Good gill condition'),
                (8002, 3003, date(2024, 9, 1), 'Parasite Check', 2, 92.0, 'Low parasite load'),
            ],
            1002: [
                (8003, 3005, date(2024, 7, 15), 'Skin Check', 1, 88.0, 'Healthy skin'),
            ]
        }

        return mock_data.get(population_id, [])

    def get_fishtalk_batches(self):
        """Get active batches from FishTalk"""
        if self.fishtalk_conn == 'mock':
            # Use mock data
            batches = self._get_mock_batches()
        else:
            # Real database connection
            cursor = self.fishtalk_conn.cursor()

            if self.batch_id:
                # Single batch migration
                cursor.execute("""
                    SELECT p.PopulationID, p.PopulationName, p.SpeciesID,
                           p.StartTime, pp.Status, pa.ProductionStage,
                           pp.ExpectedEndDate, pp.ActualEndDate,
                           prop.Notes, pa.YearClass
                    FROM Populations p
                    LEFT JOIN PublicPlanPopulation pp ON p.PopulationID = pp.PopulationID
                    LEFT JOIN PopulationAttributes pa ON p.PopulationID = pa.PopulationID
                    LEFT JOIN PopulationProperty prop ON p.PopulationID = prop.PopulationID
                    WHERE p.PopulationID = ?
                """, self.batch_id)
            else:
                # All active batches
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
                    ORDER BY p.StartTime
                """)

            batches = cursor.fetchall()

        print(f"📋 Found {len(batches)} batch(es) to migrate")
        return batches

    def migrate_batch(self, fishtalk_batch):
        """
        Migrate a single FishTalk batch to AquaMind

        Args:
            fishtalk_batch: Tuple from FishTalk query
        """
        (pop_id, pop_name, species_id, start_time, status, prod_stage,
         exp_end, actual_end, notes, year_class) = fishtalk_batch

        print(f"\n🐟 Migrating batch: {pop_name} (ID: {pop_id})")

        # Create AquaMind batch
        batch = self._create_batch_from_fishtalk(fishtalk_batch)
        self.batch_mapping[str(pop_id)] = batch.id

        # Get assignment timeline from FishTalk
        assignments = self._get_fishtalk_assignments(pop_id)

        # Replay assignments chronologically
        self._replay_assignments(batch, assignments)

        # Replay operational events
        self._replay_feeding_events(batch)
        self._replay_mortality_events(batch)
        self._replay_growth_samples(batch)
        self._replay_health_events(batch)

        # Create transfer workflows for stage transitions
        self._create_transfer_workflows(batch)

        print(f"✅ Completed migration of batch {pop_name}")

    def _create_batch_from_fishtalk(self, fishtalk_batch):
        """Create AquaMind batch from FishTalk data"""
        (pop_id, pop_name, species_id, start_time, status, prod_stage,
         exp_end, actual_end, notes, year_class) = fishtalk_batch

        # Map FishTalk status to AquaMind status
        status_mapping = {
            'Active': 'ACTIVE',
            'Running': 'ACTIVE',
            'InProduction': 'ACTIVE',
            'Completed': 'CLOSED',
            'Inactive': 'INACTIVE'
        }
        aquamind_status = status_mapping.get(status, 'ACTIVE')

        # Get species (default to Atlantic Salmon)
        species = Species.objects.filter(name='Atlantic Salmon').first()

        # Map lifecycle stage
        stage_mapping = {
            'Egg': 'Egg&Alevin',
            'Alevin': 'Egg&Alevin',
            'Fry': 'Fry',
            'Parr': 'Parr',
            'Smolt': 'Smolt',
            'Post-Smolt': 'Post-Smolt',
            'Grower': 'Adult',
            'Harvest': 'Adult'
        }
        stage_name = stage_mapping.get(prod_stage, 'Fry')
        lifecycle_stage = LifeCycleStage.objects.filter(name=stage_name).first()

        # Prepare batch notes
        full_notes = notes or ''
        if year_class:
            full_notes += f"\nYear Class: {year_class}"
        full_notes += f"\nMigrated from FishTalk PopulationID: {pop_id}"

        batch = Batch.objects.create(
            batch_number=f"FT-{pop_name}",
            species=species,
            lifecycle_stage=lifecycle_stage,
            status=aquamind_status,
            batch_type='STANDARD',
            start_date=start_time.date() if start_time else timezone.now().date(),
            expected_end_date=exp_end,
            actual_end_date=actual_end,
            notes=full_notes.strip(),
            created_at=timezone.now(),
            updated_at=timezone.now()
        )

        # Set history user for audit trail
        admin_user = User.objects.filter(username='system_admin').first()
        batch._history_user = admin_user
        batch.save()

        print(f"  📝 Created batch: {batch.batch_number}")
        return batch

    def _get_fishtalk_assignments(self, population_id):
        """Get container assignment timeline from FishTalk"""
        if self.fishtalk_conn == 'mock':
            return self._get_mock_assignments(population_id)
        else:
            cursor = self.fishtalk_conn.cursor()

            cursor.execute("""
                SELECT pp.PlanPopulationID, pc.ContainerID, pa.ProductionStage,
                       pp.Count, pp.AvgWeight, pp.Biomass, pc.StartDate, pc.EndDate,
                       pc.IsActive, us.SampleDate
                FROM PlanPopulation pp
                JOIN PlanContainer pc ON pp.PlanContainerID = pc.PlanContainerID
                LEFT JOIN PopulationAttributes pa ON pp.PopulationID = pa.PopulationID
                LEFT JOIN (
                    SELECT PopulationID, MAX(SampleDate) as SampleDate
                    FROM UserSample
                    GROUP BY PopulationID
                ) us ON pp.PopulationID = us.PopulationID
                WHERE pp.PopulationID = ?
                  AND (pc.IsActive = 1 OR pc.EndDate IS NULL OR pc.EndDate > GETDATE())
                ORDER BY pc.StartDate
            """, population_id)

            return cursor.fetchall()

    def _replay_assignments(self, batch, fishtalk_assignments):
        """Replay container assignments chronologically"""
        print(f"  🏠 Replaying {len(fishtalk_assignments)} container assignments")

        for assignment_data in fishtalk_assignments:
            (plan_pop_id, container_id, prod_stage, count, avg_weight,
             biomass, start_date, end_date, is_active, last_sample) = assignment_data

            # Map lifecycle stage
            stage_mapping = {
                'Egg': 'Egg&Alevin',
                'Alevin': 'Egg&Alevin',
                'Fry': 'Fry',
                'Parr': 'Parr',
                'Smolt': 'Smolt',
                'Post-Smolt': 'Post-Smolt',
                'Grower': 'Adult',
                'Harvest': 'Adult'
            }
            stage_name = stage_mapping.get(prod_stage, 'Fry')
            lifecycle_stage = LifeCycleStage.objects.filter(name=stage_name).first()

            # For now, create placeholder containers (will be replaced with real infrastructure)
            container = self._get_or_create_container(container_id, lifecycle_stage)

            # Convert FishTalk weight (likely kg) to grams for AquaMind
            avg_weight_g = (avg_weight * 1000) if avg_weight else None

            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=lifecycle_stage,
                population_count=count or 0,
                avg_weight_g=avg_weight_g,
                biomass_kg=Decimal(str(biomass)) if biomass else Decimal('0'),
                assignment_date=start_date or timezone.now().date(),
                departure_date=end_date,
                is_active=bool(is_active),
                last_weighing_date=last_sample,
                notes=f"Migrated from FishTalk PlanPopulationID: {plan_pop_id}",
                created_at=timezone.now(),
                updated_at=timezone.now()
            )

            print(f"    ✓ Assigned to {container.name} ({lifecycle_stage.name})")

    def _get_or_create_container(self, fishtalk_container_id, lifecycle_stage):
        """Get or create container mapping with proper infrastructure"""
        container_name = f"FT-Container-{fishtalk_container_id}"

        # Determine container type based on stage
        type_mapping = {
            'Egg&Alevin': 'Egg & Alevin Trays',
            'Fry': 'Fry Tanks',
            'Parr': 'Parr Tanks',
            'Smolt': 'Smolt Tanks',
            'Post-Smolt': 'Post-Smolt Tanks',
            'Adult': 'Adult Sea Cages'
        }

        container_type_name = type_mapping.get(lifecycle_stage.name, 'Fry Tanks')
        container_type = ContainerType.objects.filter(name=container_type_name).first()

        # Check if container already exists
        container = Container.objects.filter(name=container_name).first()
        if container:
            return container

        # Create container with proper location based on stage
        if lifecycle_stage.name in ['Egg&Alevin', 'Fry', 'Parr', 'Smolt', 'Post-Smolt']:
            # Freshwater - needs hall
            hall = self._get_or_create_hall_for_stage(lifecycle_stage)
            container = Container.objects.create(
                name=container_name,
                container_type=container_type,
                hall=hall,
                volume_m3=10.0,
                max_biomass_kg=1000.0,
                active=True
            )
        else:
            # Adult - needs sea area
            sea_area = self._get_or_create_sea_area()
            container = Container.objects.create(
                name=container_name,
                container_type=container_type,
                area=sea_area,
                volume_m3=1000.0,
                max_biomass_kg=10000.0,
                active=True
            )

        return container

    def _get_or_create_hall_for_stage(self, lifecycle_stage):
        """Create a hall for freshwater stages"""
        hall_name = f"FT-{lifecycle_stage.name}-Hall"

        # Get Faroe Islands geography
        geography = Geography.objects.filter(name='Faroe Islands').first()
        if not geography:
            geography = Geography.objects.filter(name__icontains='Faroe').first()
            if not geography:
                geography = Geography.objects.first()

        # Create station if needed
        station, _ = FreshwaterStation.objects.get_or_create(
            name=f"FT-Freshwater-Station",
            defaults={
                'geography': geography,
                'station_type': 'HATCHERY',
                'latitude': 62.0,  # Faroe Islands approximate
                'longitude': -7.0,
                'active': True
            }
        )

        # Create hall
        hall, _ = Hall.objects.get_or_create(
            name=hall_name,
            defaults={
                'freshwater_station': station,
                'description': f"Hall for {lifecycle_stage.name} stage",
                'area_sqm': 100.0,
                'active': True
            }
        )

        return hall

    def _get_or_create_sea_area(self):
        """Create a sea area for adult stages"""
        area_name = "FT-Sea-Area"

        # Get Faroe Islands geography
        geography = Geography.objects.filter(name='Faroe Islands').first()
        if not geography:
            geography = Geography.objects.filter(name__icontains='Faroe').first()
            if not geography:
                geography = Geography.objects.first()

        # Create sea area
        area, _ = Area.objects.get_or_create(
            name=area_name,
            geography=geography,
            defaults={
                'latitude': 62.0,  # Faroe Islands approximate
                'longitude': -7.0,
                'max_biomass': 50000.0,
                'active': True
            }
        )

        return area

    def _replay_feeding_events(self, batch):
        """Replay feeding events from FishTalk"""
        if self.fishtalk_conn == 'mock':
            fishtalk_pop_id = list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)]
            feeding_events = self._get_mock_feeding_events(fishtalk_pop_id)
        else:
            cursor = self.fishtalk_conn.cursor()

            # Get feeding events for this batch
            cursor.execute("""
                SELECT f.FeedingID, f.ContainerID, f.FeedBatchID, f.FeedingTime,
                       f.FeedAmount, pfu.Biomass, f.FeedPercent, f.Method, f.Notes
                FROM Feeding f
                LEFT JOIN PlanStatusFeedUse pfu ON f.PopulationID = pfu.PopulationID
                    AND CAST(f.FeedingTime as DATE) = pfu.Date
                WHERE f.PopulationID = ?
                ORDER BY f.FeedingTime
            """, list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)])

            feeding_events = cursor.fetchall()

        print(f"  🍽️  Replaying {len(feeding_events)} feeding events")

        for feed_data in feeding_events:
            (feeding_id, container_id, feed_batch_id, feeding_time,
             feed_amount, biomass, feed_percent, method, notes) = feed_data

            # Get or create feed type (placeholder)
            feed = self._get_or_create_feed(feed_batch_id)

            # Get container assignment (active at feeding time)
            assignment = self._get_assignment_at_time(batch, feeding_time)

            if assignment:
                feeding_event = FeedingEvent.objects.create(
                    batch=batch,
                    container=assignment.container,
                    batch_assignment=assignment,
                    feed=feed,
                    feeding_date=feeding_time.date(),
                    feeding_time=feeding_time.time(),
                    amount_kg=Decimal(str(feed_amount)) if feed_amount else Decimal('0'),
                    batch_biomass_kg=Decimal(str(biomass)) if biomass else Decimal('0'),
                    feeding_percentage=Decimal(str(feed_percent)) if feed_percent else None,
                    method=method or 'MANUAL',
                    notes=notes or f"Migrated from FishTalk FeedingID: {feeding_id}"
                )
                self.stats['feed'] += 1

    def _get_or_create_feed(self, fishtalk_feed_batch_id):
        """Get or create feed type from FishTalk feed batch"""
        feed_name = f"FT-Feed-{fishtalk_feed_batch_id}"
        feed, created = Feed.objects.get_or_create(
            name=feed_name,
            defaults={
                'brand': 'FishTalk Import',
                'size_category': 'MEDIUM',
                'protein_percentage': 45.0,
                'fat_percentage': 20.0,
                'is_active': True
            }
        )
        return feed

    def _get_assignment_at_time(self, batch, datetime_point):
        """Get the active container assignment at a specific point in time"""
        return BatchContainerAssignment.objects.filter(
            batch=batch,
            assignment_date__lte=datetime_point.date(),
            is_active=True
        ).first()

    def _replay_mortality_events(self, batch):
        """Replay mortality events from FishTalk"""
        if self.fishtalk_conn == 'mock':
            fishtalk_pop_id = list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)]
            mortality_events = self._get_mock_mortality_events(fishtalk_pop_id)
        else:
            cursor = self.fishtalk_conn.cursor()

            cursor.execute("""
                SELECT m.MortalityID, m.ContainerID, m.MortalityDate, m.Count,
                       m.Cause, m.Description
                FROM Mortality m
                WHERE m.PopulationID = ?
                ORDER BY m.MortalityDate
            """, list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)])

            mortality_events = cursor.fetchall()

        print(f"  💀 Replaying {len(mortality_events)} mortality events")

        for mort_data in mortality_events:
            (mort_id, container_id, mort_date, count, cause, description) = mort_data

            assignment = self._get_assignment_at_time(batch, mort_date)

            if assignment:
                mortality = MortalityEvent.objects.create(
                    batch=batch,
                    assignment=assignment,
                    event_date=mort_date,
                    count=count or 0,
                    cause=cause or 'Unknown',
                    description=description or f"Migrated from FishTalk MortalityID: {mort_id}"
                )
                self.stats['mort'] += 1

    def _replay_growth_samples(self, batch):
        """Replay growth samples from FishTalk"""
        if self.fishtalk_conn == 'mock':
            fishtalk_pop_id = list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)]
            growth_samples = self._get_mock_growth_samples(fishtalk_pop_id)
        else:
            cursor = self.fishtalk_conn.cursor()

            cursor.execute("""
                SELECT ws.SampleID, ws.ContainerID, ws.SampleDate, ws.AvgWeight,
                       ws.StdDev, ws.MinWeight, ws.MaxWeight, ws.SampleSize
                FROM PublicWeightSamples ws
                WHERE ws.PopulationID = ?
                ORDER BY ws.SampleDate
            """, list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)])

            growth_samples = cursor.fetchall()

        print(f"  📏 Replaying {len(growth_samples)} growth samples")

        for sample_data in growth_samples:
            (sample_id, container_id, sample_date, avg_weight, std_dev,
             min_weight, max_weight, sample_size) = sample_data

            assignment = self._get_assignment_at_time(batch, sample_date)

            if assignment:
                growth_sample = GrowthSample.objects.create(
                    assignment=assignment,
                    sample_date=sample_date,
                    sample_size=sample_size or 0,
                    avg_weight_g=Decimal(str(avg_weight * 1000)) if avg_weight else None,
                    std_deviation_weight=Decimal(str(std_dev * 1000)) if std_dev else None,
                    min_weight_g=Decimal(str(min_weight * 1000)) if min_weight else None,
                    max_weight_g=Decimal(str(max_weight * 1000)) if max_weight else None,
                    notes=f"Migrated from FishTalk SampleID: {sample_id}"
                )
                self.stats['growth'] += 1

    def _replay_health_events(self, batch):
        """Replay health events from FishTalk"""
        if self.fishtalk_conn == 'mock':
            fishtalk_pop_id = list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)]
            health_events = self._get_mock_health_events(fishtalk_pop_id)
        else:
            cursor = self.fishtalk_conn.cursor()

            # User samples (health observations)
            cursor.execute("""
                SELECT us.SampleID, us.ContainerID, us.SampleDate, us.SampleType,
                       uspv.ParameterID, uspv.Value, us.Notes
                FROM UserSample us
                LEFT JOIN UserSampleParameterValue uspv ON us.SampleID = uspv.SampleID
                WHERE us.PopulationID = ?
                ORDER BY us.SampleDate
            """, list(self.batch_mapping.keys())[list(self.batch_mapping.values()).index(batch.id)])

            health_events = cursor.fetchall()

        print(f"  🏥 Replaying {len(health_events)} health events")

        for health_data in health_events:
            (sample_id, container_id, sample_date, sample_type,
             param_id, value, notes) = health_data

            assignment = self._get_assignment_at_time(batch, sample_date)

            if assignment:
                # Create journal entry for health observation
                journal = JournalEntry.objects.create(
                    batch=batch,
                    container=assignment.container,
                    user=User.objects.filter(username='system_admin').first(),
                    entry_date=sample_date,
                    category='observation',
                    severity='low',
                    description=f"Health observation - {sample_type}: {value}",
                    resolution_status=True,
                    resolution_notes=notes or f"Migrated from FishTalk SampleID: {sample_id}"
                )

    def _create_transfer_workflows(self, batch):
        """Create transfer workflows for stage transitions"""
        print(f"  🔄 Creating transfer workflows")

        # Find stage transitions in assignment history
        assignments = batch.batch_assignments.order_by('assignment_date')

        # Group consecutive assignments by date to find transfers
        transfer_groups = defaultdict(list)

        for assignment in assignments:
            # Use assignment date as transfer key
            key = assignment.assignment_date
            transfer_groups[key].append(assignment)

        # Create workflows for multi-assignment transfers
        for transfer_date, assignments_on_date in transfer_groups.items():
            if len(assignments_on_date) > 1:
                # This is a transfer day with multiple assignments
                self._create_workflow_for_transfer(batch, assignments_on_date, transfer_date)

    def _create_workflow_for_transfer(self, batch, assignments, transfer_date):
        """Create a transfer workflow for a batch of assignments"""
        # Get source and destination stages
        source_assignments = [a for a in assignments if a.departure_date == transfer_date]
        dest_assignments = [a for a in assignments if a.assignment_date == transfer_date]

        if source_assignments and dest_assignments:
            workflow = BatchTransferWorkflow.objects.create(
                workflow_number=f"TRF-{batch.batch_number}-{transfer_date.strftime('%Y%m%d')}",
                batch=batch,
                workflow_type='LIFECYCLE_TRANSITION',
                status='COMPLETED',
                planned_start_date=transfer_date,
                actual_start_date=transfer_date,
                actual_completion_date=transfer_date,
                total_actions_planned=len(source_assignments),
                actions_completed=len(source_assignments),
                completion_percentage=100.0,
                initiated_by=User.objects.filter(username='system_admin').first(),
                notes=f"Auto-generated workflow for FishTalk migration"
            )

            # Create transfer actions
            for i, (source, dest) in enumerate(zip(source_assignments, dest_assignments), 1):
                TransferAction.objects.create(
                    workflow=workflow,
                    action_number=i,
                    status='COMPLETED',
                    source_assignment=source,
                    dest_assignment=dest,
                    source_population_before=source.population_count,
                    transferred_count=min(source.population_count, dest.population_count),
                    transferred_biomass_kg=min(source.biomass_kg, dest.biomass_kg),
                    execution_duration_minutes=30,  # Estimate
                    actual_execution_date=transfer_date,
                    executed_by=User.objects.filter(username='system_admin').first(),
                    notes=f"Migrated transfer action"
                )

            print(f"    ✓ Created workflow with {len(source_assignments)} actions")

    def run_migration(self):
        """Run the complete migration"""
        print("=" * 80)
        print("🐟 FishTalk to AquaMind Migration Engine")
        print("=" * 80)

        try:
            # Connect to FishTalk
            if not self.connect_fishtalk():
                return False

            # Get batches to migrate
            fishtalk_batches = self.get_fishtalk_batches()

            if not fishtalk_batches:
                print("❌ No batches found to migrate")
                return False

            # Migrate each batch
            for fishtalk_batch in fishtalk_batches:
                with transaction.atomic():
                    self.migrate_batch(fishtalk_batch)

            # Print summary
            print("\n" + "=" * 80)
            print("📊 Migration Summary")
            print("=" * 80)
            print(f"Batches Migrated: {len(fishtalk_batches)}")
            print(f"Feeding Events: {self.stats['feed']}")
            print(f"Mortality Events: {self.stats['mort']}")
            print(f"Growth Samples: {self.stats['growth']}")
            print(f"✅ Migration completed successfully!")
            print("=" * 80)

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.disconnect_fishtalk()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='FishTalk to AquaMind Migration')
    parser.add_argument('--config', default='../migration/migration_config.json',
                       help='Path to migration config file')
    parser.add_argument('--batch-id', type=str,
                       help='Specific FishTalk PopulationID to migrate')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without doing it')

    args = parser.parse_args()

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), args.config)
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return 1

    # Create migration engine
    engine = FishTalkEventEngine(config['fishtalk'], args.batch_id)

    # Run migration
    success = engine.run_migration()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
