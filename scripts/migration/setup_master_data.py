#!/usr/bin/env python
"""
Set up master data for migration development database
Creates geographies, admin user, species, lifecycle stages, etc.
"""

import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()
django.setup()
assert_default_db_is_migration_db()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.infrastructure.models import Geography, Area, FreshwaterStation, Hall, Container, ContainerType
from apps.batch.models import Species, LifeCycleStage
from apps.environmental.models import EnvironmentalParameter
from apps.inventory.models import Feed
from apps.health.models import HealthParameter, SampleType, MortalityReason, VaccinationType
from apps.scenario.models import TemperatureProfile

User = get_user_model()

def create_geographies():
    """Create Faroe Islands and Scotland geographies"""
    print("Creating geographies...")

    faroe, created = Geography.objects.get_or_create(
        name='Faroe Islands',
        defaults={
            'description': 'Faroe Islands aquaculture operations',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
    )
    print(f"✓ {'Created' if created else 'Found'} Faroe Islands geography")

    scotland, created = Geography.objects.get_or_create(
        name='Scotland',
        defaults={
            'description': 'Scotland aquaculture operations',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
    )
    print(f"✓ {'Created' if created else 'Found'} Scotland geography")

    return {'faroe': faroe, 'scotland': scotland}

def create_admin_user():
    """Create system admin user"""
    print("Creating admin user...")

    user, created = User.objects.get_or_create(
        username='system_admin',
        defaults={
            'email': 'admin@aquamind.com',
            'first_name': 'System',
            'last_name': 'Administrator',
            'is_staff': True,
            'is_superuser': True
        }
    )

    if created:
        user.set_password('admin123')  # Simple password for development
        user.save()
        print("✓ Created system admin user")
    else:
        print("✓ Found existing system admin user")

    return user

def create_species():
    """Create Atlantic Salmon species"""
    print("Creating species...")

    salmon, created = Species.objects.get_or_create(
        name='Atlantic Salmon',
        defaults={
            'scientific_name': 'Salmo salar'
        }
    )
    print(f"✓ {'Created' if created else 'Found'} Atlantic Salmon species")

    return salmon

def create_lifecycle_stages(species):
    """Create salmon lifecycle stages"""
    print("Creating lifecycle stages...")

    stages_data = [
        {'name': 'Egg&Alevin', 'order': 1, 'description': 'Egg incubation and early larval stage'},
        {'name': 'Fry', 'order': 2, 'description': 'Early feeding stage'},
        {'name': 'Parr', 'order': 3, 'description': 'Juvenile freshwater stage'},
        {'name': 'Smolt', 'order': 4, 'description': 'Smoltification stage'},
        {'name': 'Post-Smolt', 'order': 5, 'description': 'Early seawater adaptation'},
        {'name': 'Adult', 'order': 6, 'description': 'Adult grow-out stage'},
    ]

    stages = []
    for stage_data in stages_data:
        stage, created = LifeCycleStage.objects.get_or_create(
            name=stage_data['name'],
            defaults={
                'species': species,
                'description': stage_data['description'],
                'order': stage_data['order']
            }
        )
        stages.append(stage)
        print(f"✓ {'Created' if created else 'Found'} {stage.name} stage")

    return stages

def create_environmental_parameters():
    """Create basic environmental parameters"""
    print("Creating environmental parameters...")

    params_data = [
        {'name': 'Temperature', 'unit': '°C'},
        {'name': 'Dissolved Oxygen', 'unit': 'mg/L'},
        {'name': 'Salinity', 'unit': 'ppt'},
        {'name': 'pH', 'unit': 'pH'},
        {'name': 'Ammonia', 'unit': 'mg/L'},
        {'name': 'Nitrite', 'unit': 'mg/L'},
        {'name': 'Nitrate', 'unit': 'mg/L'},
    ]

    params = []
    for param_data in params_data:
        param, created = EnvironmentalParameter.objects.get_or_create(
            name=param_data['name'],
            defaults={'unit': param_data['unit']}
        )
        params.append(param)
        print(f"✓ {'Created' if created else 'Found'} {param.name} parameter")

    return params

def create_health_master_data():
    """Create health-related master data"""
    print("Creating health master data...")

    # Sample types
    sample_types = ['Blood', 'Tissue', 'Water', 'Feed', 'Fecal']
    for sample_type in sample_types:
        st, created = SampleType.objects.get_or_create(
            name=sample_type,
            defaults={'description': f'{sample_type} sample for analysis'}
        )
        print(f"✓ {'Created' if created else 'Found'} {sample_type} sample type")

    # Mortality reasons
    mortality_reasons = [
        'Disease', 'Stress', 'Accident', 'Predation', 'Starvation', 'Unknown'
    ]
    for reason in mortality_reasons:
        mr, created = MortalityReason.objects.get_or_create(
            name=reason,
            defaults={'description': f'Mortality due to {reason.lower()}'}
        )
        print(f"✓ {'Created' if created else 'Found'} {reason} mortality reason")

    # Vaccination types
    vacc_types = ['IPNV', 'PD', 'Furunculosis', 'Combined']
    for vacc in vacc_types:
        vt, created = VaccinationType.objects.get_or_create(
            name=vacc,
            defaults={'description': f'{vacc} vaccination'}
        )
        print(f"✓ {'Created' if created else 'Found'} {vacc} vaccination type")

    # Health parameters
    health_params = [
        {'name': 'Gill Condition', 'min_score': 0, 'max_score': 3},
        {'name': 'Skin Condition', 'min_score': 0, 'max_score': 3},
        {'name': 'Fin Condition', 'min_score': 0, 'max_score': 3},
        {'name': 'Eye Condition', 'min_score': 0, 'max_score': 3},
    ]
    for param_data in health_params:
        hp, created = HealthParameter.objects.get_or_create(
            name=param_data['name'],
            defaults={
                'min_score': param_data['min_score'],
                'max_score': param_data['max_score'],
                'is_active': True
            }
        )
        print(f"✓ {'Created' if created else 'Found'} {param_data['name']} health parameter")

def create_basic_feeds():
    """Create basic feed types"""
    print("Creating basic feed types...")

    feeds_data = [
        {
            'name': 'Standard Fry Feed',
            'brand': 'TestBrand',
            'size_category': 'MICRO',
            'protein_percentage': 55.0,
            'fat_percentage': 15.0,
            'carbohydrate_percentage': 10.0,
            'pellet_size_mm': 1.5,
            'is_active': True
        },
        {
            'name': 'Standard Grower Feed',
            'brand': 'TestBrand',
            'size_category': 'MEDIUM',
            'protein_percentage': 45.0,
            'fat_percentage': 20.0,
            'carbohydrate_percentage': 15.0,
            'pellet_size_mm': 4.0,
            'is_active': True
        },
        {
            'name': 'Premium Adult Feed',
            'brand': 'TestBrand',
            'size_category': 'LARGE',
            'protein_percentage': 40.0,
            'fat_percentage': 25.0,
            'carbohydrate_percentage': 20.0,
            'pellet_size_mm': 8.0,
            'is_active': True
        }
    ]

    feeds = []
    for feed_data in feeds_data:
        feed, created = Feed.objects.get_or_create(
            name=feed_data['name'],
            brand=feed_data['brand'],
            defaults=feed_data
        )
        feeds.append(feed)
        print(f"✓ {'Created' if created else 'Found'} {feed.name} feed")

    return feeds

def create_temperature_profiles(geographies):
    """Create temperature profiles for each geography"""
    print("Creating temperature profiles...")

    profiles = {}
    for geo_name, geo in geographies.items():
        profile, created = TemperatureProfile.objects.get_or_create(
            name=f'{geo.name} Standard Temperatures'
        )
        profiles[geo_name] = profile
        print(f"✓ {'Created' if created else 'Found'} temperature profile for {geo.name}")

    return profiles

def create_basic_infrastructure(geographies):
    """Create minimal infrastructure for testing"""
    print("Creating basic infrastructure...")

    # Container types
    container_types_data = [
        {'name': 'Egg & Alevin Trays', 'category': 'TRAY', 'max_volume_m3': 1.0},
        {'name': 'Fry Tanks', 'category': 'TANK', 'max_volume_m3': 5.0},
        {'name': 'Parr Tanks', 'category': 'TANK', 'max_volume_m3': 20.0},
        {'name': 'Smolt Tanks', 'category': 'TANK', 'max_volume_m3': 50.0},
        {'name': 'Post-Smolt Tanks', 'category': 'TANK', 'max_volume_m3': 100.0},
        {'name': 'Adult Sea Cages', 'category': 'PEN', 'max_volume_m3': 1000.0},
    ]

    container_types = {}
    for ct_data in container_types_data:
        ct, created = ContainerType.objects.get_or_create(
            name=ct_data['name'],
            defaults={
                'category': ct_data['category'],
                'max_volume_m3': ct_data['max_volume_m3'],
                'description': f'Standard {ct_data["name"].lower()}'
            }
        )
        container_types[ct_data['name']] = ct
        print(f"✓ {'Created' if created else 'Found'} {ct.name} container type")

    return container_types

def main():
    """Set up all master data"""
    print("=" * 80)
    print("Setting up Master Data for Migration Development")
    print("=" * 80)

    try:
        # Create geographies
        geographies = create_geographies()
        print()

        # Create admin user
        admin_user = create_admin_user()
        print()

        # Create species and lifecycle stages
        species = create_species()
        stages = create_lifecycle_stages(species)
        print()

        # Create environmental parameters
        env_params = create_environmental_parameters()
        print()

        # Create health master data
        create_health_master_data()
        print()

        # Create feeds
        feeds = create_basic_feeds()
        print()

        # Create temperature profiles
        temp_profiles = create_temperature_profiles(geographies)
        print()

        # Create basic infrastructure
        container_types = create_basic_infrastructure(geographies)
        print()

        print("=" * 80)
        print("✅ Master data setup completed successfully!")
        print("=" * 80)

        print("\nSummary:")
        print(f"  Geographies: {len(geographies)}")
        print(f"  Admin user: {admin_user.username}")
        print(f"  Species: {species.name}")
        print(f"  Lifecycle stages: {len(stages)}")
        print(f"  Environmental parameters: {len(env_params)}")
        print(f"  Feed types: {len(feeds)}")
        print(f"  Temperature profiles: {len(temp_profiles)}")
        print(f"  Container types: {len(container_types)}")

        return True

    except Exception as e:
        print(f"❌ Error setting up master data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
