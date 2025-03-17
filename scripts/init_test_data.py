#!/usr/bin/env python
"""
Test Data Initialization Script

This script creates infrastructure and batch test data for the AquaMind system.
It includes existing data and creates new halls and containers across various locations.

Usage:
    python manage.py shell < scripts/init_test_data.py
"""
import os
import django
import sys
from django.db import transaction

# Initialize Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Import models
from apps.infrastructure.models import Geography, Area, FreshwaterStation, ContainerType, Hall, Container
from apps.batch.models import Species, LifeCycleStage

# Helper function to print creation status
def print_status(model_name, obj, created=True):
    action = "Created" if created else "Found existing"
    print(f"{action} {model_name}: {obj}")

@transaction.atomic
def create_test_data():
    """Create or verify test data exists"""
    print("\n=== Starting Test Data Initialization ===\n")
    
    # ====== Initialize Geographies ======
    faroe_islands, created = Geography.objects.get_or_create(
        id=1, 
        defaults={"name": "Faroe Islands"}
    )
    print_status("Geography", faroe_islands, created)
    
    scotland, created = Geography.objects.get_or_create(
        id=2, 
        defaults={"name": "Scotland"}
    )
    print_status("Geography", scotland, created)
    
    # ====== Initialize Areas ======
    area_a57, created = Area.objects.get_or_create(
        id=1,
        defaults={
            "name": "A57 - Fuglafjørður",
            "geography": faroe_islands,
            "latitude": 62.2341,  # Example coordinates
            "longitude": -6.8143
        }
    )
    print_status("Area", area_a57, created)
    
    # ====== Initialize Freshwater Stations ======
    station_s24, created = FreshwaterStation.objects.get_or_create(
        id=1,
        defaults={
            "name": "S24 - Á Strond",
            "station_type": "FRESHWATER",
            "geography": faroe_islands,
            "latitude": 62.1023,  # Example coordinates 
            "longitude": -6.7456,
            "active": True
        }
    )
    print_status("Freshwater Station", station_s24, created)
    
    # ====== Initialize Container Types ======
    container_types = [
        {"id": 8, "name": "Egg&Alevin Trays", "category": "TRAY"},
        {"id": 9, "name": "Fry Rearing Tanks", "category": "TANK"},
        {"id": 10, "name": "Parr Rearing Tanks", "category": "TANK"},
        {"id": 11, "name": "Smolt Tanks", "category": "TANK"},
        {"id": 12, "name": "Post-Smolt Tanks", "category": "TANK"},
        {"id": 13, "name": "Sea Pens", "category": "PEN"}
    ]
    
    ct_objects = {}
    for ct_data in container_types:
        ct_obj, created = ContainerType.objects.get_or_create(
            id=ct_data["id"],
            defaults={
                "name": ct_data["name"],
                "category": ct_data["category"]
            }
        )
        ct_objects[ct_data["name"]] = ct_obj
        print_status("Container Type", ct_obj, created)
    
    # ====== Initialize Species ======
    salmon, created = Species.objects.get_or_create(
        id=1,
        defaults={
            "name": "Atlantic Salmon",
            "scientific_name": "Salmo salar",
            "description": "North Atlantic salmon species common in aquaculture"
        }
    )
    print_status("Species", salmon, created)
    
    # ====== Initialize Life Cycle Stages ======
    lifecycle_stages = [
        {"id": 1, "name": "Egg&Alevin", "species": salmon, "order": 1},
        {"id": 2, "name": "Fry", "species": salmon, "order": 2},
        {"id": 3, "name": "Parr", "species": salmon, "order": 3},
        {"id": 4, "name": "Smolt", "species": salmon, "order": 4},
        {"id": 5, "name": "Post-Smolt", "species": salmon, "order": 5},
        {"id": 6, "name": "Adult", "species": salmon, "order": 6}
    ]
    
    for ls_data in lifecycle_stages:
        ls_obj, created = LifeCycleStage.objects.get_or_create(
            id=ls_data["id"],
            defaults={
                "name": ls_data["name"],
                "species": ls_data["species"],
                "order": ls_data["order"]
            }
        )
        print_status("Life Cycle Stage", ls_obj, created)
    
    # ====== Create Halls ======
    print("\n--- Creating Halls ---")
    hall_names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
    halls = {}
    
    for hall_name in hall_names:
        hall, created = Hall.objects.get_or_create(
            name=f"Hall {hall_name}",
            defaults={
                "freshwater_station": station_s24,
                "description": f"Hall {hall_name} in {station_s24.name}",
                "active": True
            }
        )
        halls[hall_name] = hall
        print_status("Hall", hall, created)
    
    # ====== Create Containers ======
    print("\n--- Creating Containers ---")
    
    # Egg&Alevin Trays in Hall A
    for i in range(1, 51):
        container, created = Container.objects.get_or_create(
            name=f"A-Tray{i:02d}",
            defaults={
                "container_type": ct_objects["Egg&Alevin Trays"],
                "hall": halls["A"],
                "volume_m3": 3,
                "max_biomass_kg": 15,  # Example value
                "active": True,
                "area": None  # Not in an area
            }
        )
        print_status("Container", container, created)
    
    # Fry Rearing Tanks in Hall B and C
    for hall_name in ["B", "C"]:
        for i in range(1, 13):
            container, created = Container.objects.get_or_create(
                name=f"{hall_name}-Fry{i:02d}",
                defaults={
                    "container_type": ct_objects["Fry Rearing Tanks"],
                    "hall": halls[hall_name],
                    "volume_m3": 15,
                    "max_biomass_kg": 150,  # Example value
                    "active": True,
                    "area": None  # Not in an area
                }
            )
            print_status("Container", container, created)
    
    # Parr Rearing Tanks in Hall D and E
    for hall_name in ["D", "E"]:
        for i in range(1, 9):
            container, created = Container.objects.get_or_create(
                name=f"{hall_name}-Parr{i:02d}",
                defaults={
                    "container_type": ct_objects["Parr Rearing Tanks"],
                    "hall": halls[hall_name],
                    "volume_m3": 50,
                    "max_biomass_kg": 750,  # Example value
                    "active": True,
                    "area": None  # Not in an area
                }
            )
            print_status("Container", container, created)
    
    # Smolt Tanks in Hall F, G, and H
    for hall_name in ["F", "G", "H"]:
        for i in range(1, 7):
            container, created = Container.objects.get_or_create(
                name=f"{hall_name}-Smolt{i:02d}",
                defaults={
                    "container_type": ct_objects["Smolt Tanks"],
                    "hall": halls[hall_name],
                    "volume_m3": 400,
                    "max_biomass_kg": 8000,  # Example value
                    "active": True,
                    "area": None  # Not in an area
                }
            )
            print_status("Container", container, created)
    
    # Post-Smolt Tanks in Hall I, J, and K
    for hall_name in ["I", "J", "K"]:
        for i in range(1, 7):
            container, created = Container.objects.get_or_create(
                name=f"{hall_name}-PostSmolt{i:02d}",
                defaults={
                    "container_type": ct_objects["Post-Smolt Tanks"],
                    "hall": halls[hall_name],
                    "volume_m3": 1200,
                    "max_biomass_kg": 30000,  # Example value
                    "active": True,
                    "area": None  # Not in an area
                }
            )
            print_status("Container", container, created)
    
    # Sea Pens in Area A57
    for i in range(1, 25):
        container, created = Container.objects.get_or_create(
            name=f"A57-SeaPen{i:02d}",
            defaults={
                "container_type": ct_objects["Sea Pens"],
                "hall": None,  # Not in a hall
                "volume_m3": 42000,
                "max_biomass_kg": 800000,  # Example value
                "active": True,
                "area": area_a57
            }
        )
        print_status("Container", container, created)
    
    print("\n=== Test Data Initialization Complete ===")


# Always run the creation function when imported or run directly
create_test_data()
