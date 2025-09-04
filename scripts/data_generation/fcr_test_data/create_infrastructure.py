#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Infrastructure Setup

This script creates the basic infrastructure for FCR testing:
- Geography: Faroe Islands
- Freshwater Station with 5 halls (each with 10 containers)
- Sea Area with 20 rings
- Associated sensors and feed containers
"""

import os
import sys
import django
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType,
    Sensor, FeedContainer
)
from apps.batch.models import Species
from apps.inventory.models import Feed
from apps.environmental.models import EnvironmentalParameter

def create_geography():
    """Create Faroe Islands geography"""
    print("Creating Faroe Islands geography...")
    geography, created = Geography.objects.get_or_create(
        name="Faroe Islands",
        defaults={
            'description': 'Faroe Islands aquaculture region',
        }
    )
    print(f"Geography created: {geography.name} (ID: {geography.id})")
    return geography

def create_container_types():
    """Create container types for different lifecycle stages"""
    print("Creating container types...")
    types = [
        ('TRAY', 'Egg & Alevin Trays', 10.0),
        ('TANK', 'Fry Tanks', 100.0),
        ('TANK', 'Parr Tanks', 500.0),
        ('TANK', 'Smolt Tanks', 1000.0),
        ('TANK', 'Post-Smolt Tanks', 2000.0),
        ('PEN', 'Sea Rings', 50000.0),  # Large sea cages
    ]

    container_types = {}
    for category, name, volume in types:
        ct, created = ContainerType.objects.get_or_create(
            name=name,
            defaults={
                'category': category,
                'max_volume_m3': volume,
                'description': f'Container type for {name.lower()}'
            }
        )
        container_types[name] = ct
        print(f"Container type created: {ct.name} (ID: {ct.id})")

    return container_types

def create_freshwater_station(geography):
    """Create freshwater station"""
    print("Creating freshwater station...")
    station, created = FreshwaterStation.objects.get_or_create(
        name="Faroe Islands Freshwater Station 1",
        defaults={
            'geography': geography,
            'station_type': 'FRESHWATER',
            'latitude': 62.0,
            'longitude': -7.0,
            'description': 'Main freshwater station for Faroe Islands operations',
            'active': True
        }
    )
    print(f"Freshwater station created: {station.name} (ID: {station.id})")
    return station

def create_halls_and_containers(station, container_types):
    """Create 5 halls with 10 containers each"""
    print("Creating halls and containers...")

    hall_configs = [
        ('Hall A', 'Egg & Alevin Hall', container_types['Egg & Alevin Trays']),
        ('Hall B', 'Fry Hall', container_types['Fry Tanks']),
        ('Hall C', 'Parr Hall', container_types['Parr Tanks']),
        ('Hall D', 'Smolt Hall', container_types['Smolt Tanks']),
        ('Hall E', 'Post-Smolt Hall', container_types['Post-Smolt Tanks']),
    ]

    halls = []
    containers = []

    for hall_name, hall_desc, container_type in hall_configs:
        # Create hall
        hall, created = Hall.objects.get_or_create(
            name=hall_name,
            freshwater_station=station,
            defaults={
                'description': hall_desc,
                'area_sqm': 1000.0,
                'active': True
            }
        )
        halls.append(hall)
        print(f"Hall created: {hall.name} (ID: {hall.id})")

        # Create 10 containers per hall
        for i in range(1, 11):
            container_name = f"{hall_name}-C{i:02d}"
            container, created = Container.objects.get_or_create(
                name=container_name,
                defaults={
                    'container_type': container_type,
                    'hall': hall,
                    'volume_m3': container_type.max_volume_m3,
                    'max_biomass_kg': container_type.max_volume_m3 * 50,  # Rough biomass capacity
                    'active': True
                }
            )
            containers.append(container)
            print(f"Container created: {container.name} (ID: {container.id})")

    return halls, containers

def create_sea_area(geography):
    """Create sea area in Faroe Islands"""
    print("Creating sea area...")
    area, created = Area.objects.get_or_create(
        name="Faroe Islands Sea Area 1",
        geography=geography,
        defaults={
            'latitude': 61.5,
            'longitude': -6.5,
            'max_biomass': 1000000.0,  # 1M kg capacity
            'active': True
        }
    )
    print(f"Sea area created: {area.name} (ID: {area.id})")
    return area

def create_sea_rings(area, container_types):
    """Create 20 sea rings"""
    print("Creating sea rings...")

    containers = []
    ring_type = container_types['Sea Rings']

    for i in range(1, 21):
        ring_name = f"Ring-{i:02d}"
        container, created = Container.objects.get_or_create(
            name=ring_name,
            defaults={
                'container_type': ring_type,
                'area': area,
                'volume_m3': ring_type.max_volume_m3,
                'max_biomass_kg': ring_type.max_volume_m3 * 20,  # Lower density for sea
                'active': True
            }
        )
        containers.append(container)
        print(f"Sea ring created: {container.name} (ID: {container.id})")

    return containers

def create_sensors(containers):
    """Create sensors for containers"""
    print("Creating sensors...")

    # Get environmental parameters (assuming they exist)
    try:
        temp_param = EnvironmentalParameter.objects.get(name='Temperature')
        oxygen_param = EnvironmentalParameter.objects.get(name='Dissolved Oxygen')
        ph_param = EnvironmentalParameter.objects.get(name='pH')
    except EnvironmentalParameter.DoesNotExist:
        print("Warning: Environmental parameters not found. Skipping sensor creation.")
        return []

    sensors = []
    sensor_configs = [
        ('Temperature', temp_param),
        ('Oxygen', oxygen_param),
        ('pH', ph_param),
    ]

    for container in containers:
        for sensor_type, param in sensor_configs:
            sensor, created = Sensor.objects.get_or_create(
                name=f"{container.name}-{sensor_type}",
                defaults={
                    'sensor_type': sensor_type,
                    'container': container,
                    'serial_number': f"SN-{container.id}-{sensor_type[:3].upper()}",
                    'manufacturer': 'TestManufacturer',
                    'active': True
                }
            )
            sensors.append(sensor)
            print(f"Sensor created: {sensor.name} (ID: {sensor.id})")

    return sensors

def create_feed_containers(station, area, halls):
    """Create feed containers"""
    print("Creating feed containers...")

    feed_containers = []

    # Station-level feed container (linked to first hall)
    first_hall = halls[0] if halls else None
    if first_hall:
        station_feed, created = FeedContainer.objects.get_or_create(
            name="Station Feed Silo",
            defaults={
                'container_type': 'SILO',
                'hall': first_hall,
                'capacity_kg': 50000.0,
                'active': True
            }
        )
        feed_containers.append(station_feed)
        print(f"Feed container created: {station_feed.name} (ID: {station_feed.id})")

    # Area-level feed container
    area_feed, created = FeedContainer.objects.get_or_create(
        name="Area Feed Storage",
        defaults={
            'container_type': 'BARGE',
            'area': area,
            'capacity_kg': 100000.0,
            'active': True
        }
    )
    feed_containers.append(area_feed)
    print(f"Feed container created: {area_feed.name} (ID: {area_feed.id})")

    return feed_containers

def main():
    """Main execution"""
    print("Starting AquaMind Infrastructure Setup...")
    print("=" * 50)

    try:
        # Create geography
        geography = create_geography()

        # Create container types
        container_types = create_container_types()

        # Create freshwater station
        station = create_freshwater_station(geography)

        # Create halls and containers
        halls, freshwater_containers = create_halls_and_containers(station, container_types)

        # Create sea area
        area = create_sea_area(geography)

        # Create sea rings
        sea_rings = create_sea_rings(area, container_types)

        # Create sensors
        all_containers = freshwater_containers + sea_rings
        sensors = create_sensors(all_containers)

        # Create feed containers
        feed_containers = create_feed_containers(station, area, halls)

        print("=" * 50)
        print("Infrastructure setup completed successfully!")
        print(f"- Geography: 1")
        print(f"- Freshwater Station: 1")
        print(f"- Halls: {len(halls)}")
        print(f"- Freshwater Containers: {len(freshwater_containers)}")
        print(f"- Sea Area: 1")
        print(f"- Sea Rings: {len(sea_rings)}")
        print(f"- Sensors: {len(sensors)}")
        print(f"- Feed Containers: {len(feed_containers)}")

    except Exception as e:
        print(f"Error during infrastructure setup: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
