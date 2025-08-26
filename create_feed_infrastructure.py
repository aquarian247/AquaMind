#!/usr/bin/env python
"""
Create Feed Infrastructure - Silos and Barges
Creates feed containers (silos in freshwater stations, barges in sea areas)
with proper relationships to infrastructure.
"""
import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Area, Hall, FeedContainer, FreshwaterStation

def create_feed_infrastructure():
    """
    Create feed containers for all infrastructure locations.

    This function is rerunnable - it will skip creating containers that already exist
    and only create missing infrastructure components.
    """

    print("=== CREATING FEED INFRASTRUCTURE ===")

    # Check existing infrastructure
    existing_containers = FeedContainer.objects.count()
    print(f"📊 Existing feed containers: {existing_containers}")

    # Create feed containers for freshwater stations (silos)
    freshwater_stations = FreshwaterStation.objects.all()
    silo_count = 0

    for station in freshwater_stations:
        # Get halls for this station
        halls = station.halls.filter(active=True)

        if not halls.exists():
            print(f"⚠️  No active halls found for station {station.name}, skipping...")
            continue

        # Create silos for each hall (distributed across halls)
        num_silos = 8  # Standard configuration
        silos_per_hall = max(1, num_silos // halls.count())

        for hall in halls:
            for i in range(silos_per_hall):
                silo_name = f"{hall.name} Silo {i+1}"

                # Check if silo already exists (rerunnable)
                if not FeedContainer.objects.filter(name=silo_name).exists():
                    silo = FeedContainer.objects.create(
                        name=silo_name,
                        hall=hall,  # Link to the hall
                        container_type='SILO',  # Use the correct choice value
                        capacity_kg=Decimal('50000'),  # 50-ton silos
                        active=True
                    )
                    silo_count += 1
                else:
                    print(f"⏭️  Skipping existing silo: {silo_name}")

    print(f"✅ Created {silo_count} new feed silos in freshwater stations")

    # Create feed containers for sea areas (barges)
    sea_areas = Area.objects.filter(active=True)
    barge_count = 0

    for area in sea_areas:
        # Create 2-4 barges per sea area
        num_barges = 3  # Standard configuration

        for i in range(num_barges):
            barge_name = f"{area.name} Barge {i+1}"

            # Check if barge already exists (rerunnable)
            if not FeedContainer.objects.filter(name=barge_name).exists():
                barge = FeedContainer.objects.create(
                    name=barge_name,
                    area=area,  # Link to the sea area
                    container_type='BARGE',  # Use the correct choice value
                    capacity_kg=Decimal('100000'),  # 100-ton barges
                    active=True
                )
                barge_count += 1
            else:
                print(f"⏭️  Skipping existing barge: {barge_name}")

    print(f"✅ Created {barge_count} new feed barges in sea areas")

    # Final verification
    total_containers = FeedContainer.objects.count()
    new_containers = silo_count + barge_count

    if new_containers == 0:
        print(f"📊 No new containers created - system already has {total_containers} containers")
    else:
        print(f"📊 Total feed containers now: {total_containers} (+{new_containers} new)")

    # Distribution summary (always show current state)
    silo_distribution = {}
    barge_distribution = {}

    for container in FeedContainer.objects.all():
        if container.container_type == 'SILO':
            location_name = container.hall.name if container.hall else container.area.name if container.area else "Unknown"
            silo_distribution[location_name] = silo_distribution.get(location_name, 0) + 1
        elif container.container_type == 'BARGE':
            location_name = container.hall.name if container.hall else container.area.name if container.area else "Unknown"
            barge_distribution[location_name] = barge_distribution.get(location_name, 0) + 1

    print("\n=== CURRENT SILO DISTRIBUTION ===")
    for location, count in sorted(silo_distribution.items()):
        print(f"  {location}: {count} silos")

    print("\n=== CURRENT BARGE DISTRIBUTION ===")
    for location, count in sorted(barge_distribution.items()):
        print(f"  {location}: {count} barges")

    return new_containers

if __name__ == '__main__':
    create_feed_infrastructure()
