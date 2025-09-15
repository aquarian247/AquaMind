"""
Management command to generate audit trail test data.

This command creates a handful of real audit trail records across multiple models
to visually validate the audit trail frontend. It performs create/update/delete
operations on various tracked models using test users to generate history events.

Models covered:
- infrastructure_geography (Geography)
- infrastructure_area (Area)
- infrastructure_freshwaterstation (FreshwaterStation)
- batch_batch (Batch)
- inventory_feed (Feed)

Creates 30-50 history records across 2-3 test users.
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

# Infrastructure models
from apps.infrastructure.models import Geography, Area, FreshwaterStation

# Batch models
from apps.batch.models import Batch, Species, LifeCycleStage

# Inventory models
from apps.inventory.models import Feed

# Health models
from apps.health.models import JournalEntry


class Command(BaseCommand):
    help = 'Generate audit trail test data across multiple models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of history records to create (default: 50)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        count = options['count']
        force = options['force']

        self.stdout.write(
            self.style.WARNING(
                f'This command will generate ~{count} audit trail records across multiple models.'
            )
        )
        self.stdout.write(
            'Models affected: Geography, Area, FreshwaterStation, Batch, Feed, JournalEntry'
        )
        self.stdout.write('Test users will be created/used for history attribution.')
        self.stdout.write('')

        if not force:
            confirm = input('Proceed? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write('Cancelled.')
                return

        # Create test users
        users = self._create_test_users()

        # Generate audit trail data
        self._generate_infrastructure_data(users)
        self._generate_batch_data(users)
        self._generate_inventory_data(users)
        self._generate_health_data(users)

        # Generate some updates and deletions for more diverse history
        self._generate_updates_and_deletes(users)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated audit trail test data!'
            )
        )
        self.stdout.write(
            'Run history API endpoints to verify records were created.'
        )

    def _create_test_users(self):
        """Create or get test users for history attribution."""
        self.stdout.write('Creating test users...')

        users = []
        user_data = [
            ('audit_user1', 'Audit User One'),
            ('audit_user2', 'Audit User Two'),
            ('audit_admin', 'Audit Administrator'),
        ]

        for username, full_name in user_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': full_name.split()[0],
                    'last_name': ' '.join(full_name.split()[1:]),
                    'email': f'{username}@example.com',
                    'is_staff': True,
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'  Created user: {username}')

            # Ensure user has a profile for history tracking
            if not hasattr(user, 'profile'):
                from apps.users.models import UserProfile
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': 'OPR',  # Operator role
                        'geography': 'FO',  # Faroe Islands
                        'subsidiary': 'FW',  # Freshwater
                    }
                )

            users.append(user)

        return users

    def _generate_infrastructure_data(self, users):
        """Generate infrastructure-related audit events."""
        self.stdout.write('Generating infrastructure audit data...')

        # Create geographies
        geographies = []
        geo_names = ['Faroe Islands', 'Scotland', 'Norway', 'Denmark']

        for name in geo_names:
            geo, created = Geography.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'Aquaculture region: {name}',
                }
            )
            geographies.append(geo)
            if created:
                self.stdout.write(f'  Created geography: {name}')

        # Create areas
        areas = []
        for geo in geographies:
            for i in range(1, 4):  # 3 areas per geography
                area_name = f"{geo.name} Area {i}"
                area, created = Area.objects.get_or_create(
                    name=area_name,
                    geography=geo,
                    defaults={
                        'latitude': Decimal(str(60.0 + random.uniform(-5, 5))),
                        'longitude': Decimal(str(-5.0 + random.uniform(-5, 5))),
                        'max_biomass': Decimal(str(random.uniform(50000, 200000))),
                        'active': True,
                    }
                )
                areas.append(area)
                if created:
                    self.stdout.write(f'  Created area: {area_name}')

        # Create freshwater stations
        stations = []
        for area in areas[:6]:  # First 6 areas
            station_name = f"{area.name} Station"
            station, created = FreshwaterStation.objects.get_or_create(
                name=station_name,
                defaults={
                    'geography': area.geography,
                    'station_type': 'FRESHWATER',
                    'latitude': area.latitude + Decimal(str(random.uniform(-0.1, 0.1))),
                    'longitude': area.longitude + Decimal(str(random.uniform(-0.1, 0.1))),
                    'description': f'Freshwater station for {area.name}',
                    'active': True,
                }
            )
            stations.append(station)
            if created:
                self.stdout.write(f'  Created station: {station_name}')

        # Update some records to create ~ and - history types
        for geo in geographies[:2]:
            original_desc = geo.description
            geo.description = f"{original_desc} (updated)"
            geo.save()
            self.stdout.write(f'  Updated geography: {geo.name}')

        return geographies, areas, stations

    def _generate_batch_data(self, users):
        """Generate batch-related audit events."""
        self.stdout.write('Generating batch audit data...')

        # Ensure we have species and lifecycle stages
        species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={
                'scientific_name': 'Salmo salar',
            }
        )

        stages = []
        stage_names = ['Egg', 'Alevin', 'Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']
        for i, name in enumerate(stage_names):
            stage, _ = LifeCycleStage.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'{name} lifecycle stage',
                    'order': i,
                }
            )
            stages.append(stage)

        # Create batches
        batches = []
        batch_types = ['STANDARD', 'EXPERIMENTAL']
        statuses = ['ACTIVE', 'PLANNED', 'INACTIVE']

        for i in range(1, 11):  # 10 batches
            batch_number = f"BATCH-{i:03d}"
            batch, created = Batch.objects.get_or_create(
                batch_number=batch_number,
                defaults={
                    'species': species,
                    'lifecycle_stage': random.choice(stages),
                    'status': random.choice(statuses),
                    'batch_type': random.choice(batch_types),
                    'start_date': date.today() - timedelta(days=random.randint(0, 365)),
                    'expected_end_date': date.today() + timedelta(days=random.randint(30, 365)),
                    'notes': f'Test batch {i} for audit trail validation',
                }
            )
            batches.append(batch)
            if created:
                self.stdout.write(f'  Created batch: {batch_number}')

        # Update some batches
        for batch in batches[:3]:
            batch.status = 'ACTIVE' if batch.status == 'PLANNED' else 'INACTIVE'
            batch.save()
            self.stdout.write(f'  Updated batch: {batch.batch_number}')

        return batches

    def _generate_inventory_data(self, users):
        """Generate inventory-related audit events."""
        self.stdout.write('Generating inventory audit data...')

        # Create feed types
        feeds = []
        feed_data = [
            ('Premium Salmon Feed', 'BrandA', 'MEDIUM', 3.0, 45.0, 15.0, 25.0),
            ('Growth Accelerator', 'BrandB', 'LARGE', 4.0, 50.0, 18.0, 20.0),
            ('Starter Feed', 'BrandA', 'MICRO', 1.5, 55.0, 12.0, 22.0),
            ('Finisher Feed', 'BrandC', 'LARGE', 5.0, 40.0, 20.0, 30.0),
        ]

        for name, brand, size, pellet, protein, fat, carb in feed_data:
            feed, created = Feed.objects.get_or_create(
                name=name,
                defaults={
                    'brand': brand,
                    'size_category': size,
                    'pellet_size_mm': Decimal(str(pellet)),
                    'protein_percentage': Decimal(str(protein)),
                    'fat_percentage': Decimal(str(fat)),
                    'carbohydrate_percentage': Decimal(str(carb)),
                    'description': f'{name} - {brand}',
                    'is_active': True,
                }
            )
            feeds.append(feed)
            if created:
                self.stdout.write(f'  Created feed: {name}')

        # Update some feeds
        for feed in feeds[:2]:
            feed.protein_percentage += Decimal(str(random.uniform(1, 3)))
            feed.save()
            self.stdout.write(f'  Updated feed: {feed.name}')

        return feeds

    def _generate_health_data(self, users):
        """Generate health-related audit events."""
        self.stdout.write('Generating health audit data...')

        # Get some batches for journal entries
        batches = list(Batch.objects.all()[:5])
        if not batches:
            self.stdout.write('  Skipping health data - no batches available')
            return []

        journal_entries = []
        categories = ['observation', 'issue', 'action', 'diagnosis', 'treatment']
        severities = ['low', 'medium', 'high']

        for i in range(1, 8):  # 7 journal entries
            entry, created = JournalEntry.objects.get_or_create(
                batch=random.choice(batches),
                entry_date=timezone.now() - timedelta(days=random.randint(0, 30)),
                defaults={
                    'user': random.choice(users),
                    'category': random.choice(categories),
                    'severity': random.choice(severities),
                    'description': f'Test journal entry {i} for audit trail validation',
                    'resolution_status': random.choice([True, False]),
                }
            )
            journal_entries.append(entry)
            if created:
                self.stdout.write(f'  Created journal entry: {i}')

        return journal_entries

    def _generate_updates_and_deletes(self, users):
        """Generate some updates and deletes for diverse history types."""
        self.stdout.write('Generating updates and deletes for diverse history...')

        # Update some areas
        areas = list(Area.objects.all()[:3])
        for area in areas:
            area.max_biomass += Decimal(str(random.uniform(1000, 5000)))
            area.save()
            self.stdout.write(f'  Updated area: {area.name}')

        # Update some batches
        batches = list(Batch.objects.all()[:3])
        for batch in batches:
            batch.notes = f"{batch.notes} (updated for audit trail testing)"
            batch.save()
            self.stdout.write(f'  Updated batch notes: {batch.batch_number}')

        # Update some journal entries
        entries = list(JournalEntry.objects.all()[:2])
        for entry in entries:
            entry.resolution_status = not entry.resolution_status
            entry.save()
            self.stdout.write(f'  Updated journal entry resolution status')
