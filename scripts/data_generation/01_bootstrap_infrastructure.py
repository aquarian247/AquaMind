#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Phase 1: Bootstrap Infrastructure

This script creates the complete physical infrastructure:
- 2 Geographies (Scotland exists, create Faroe Islands)
- 13 Area Groups (hierarchy roots + marine grouping leaves)
- 22 Freshwater Stations (10 Scotland + 12 Faroe Islands)
- 110 Halls (5 per station)
- 1,110 Freshwater Containers (1,100 holding + 10 structural racks)
- 42 Sea Areas (20 Scotland + 22 Faroe Islands)
- 840 Sea Rings (20 per area)
- 236 Feed Containers (110 silos + 126 barges)
- ~14,000 Sensors (7 per operational container)

Key Design Decisions:
- Egg&Alevin hall uses rack -> tray hierarchy (STRUCTURAL racks + HOLDING trays)
  in a subset of stations matching FishTalk stand/rack usage patterns
- Every sea area is assigned to a marine area group
- Each batch occupies ONE hall at a time (never mixed)
- Gradual transitions: 10 containers moved over 10 days
- Post-Smolt → Adult: 10 tanks split into 20 rings (1:2 ratio)
- Each area has 3 feed barges (not 1)
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from decimal import Decimal

import django

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import (
    Geography, AreaGroup, Area, FreshwaterStation, Hall, Container, ContainerType,
    Sensor, FeedContainer
)
from scripts.migration.extractors.base import ExtractionContext
from scripts.migration.extractors.infrastructure import InfrastructureExtractor
from scripts.migration.loaders.infrastructure import InfrastructureLoader

# Progress tracking
progress = {
    'geographies': 0,
    'area_groups': 0,
    'stations': 0,
    'halls': 0,
    'containers': 0,
    'holding_containers': 0,
    'structural_containers': 0,
    'areas': 0,
    'rings': 0,
    'feed_containers': 0,
    'sensors': 0,
}

RACKS_PER_INCUBATION_HALL = 2
TRAYS_PER_RACK = 5
HOLDING_ROLE = "HOLDING"
EXCLUDED_MARINE_GROUP = "NOT IN USE"
# FT pattern emulation: stand/rack hierarchy exists in a subset of stations.
# We mirror this by enabling rack->tray only for selected station numbers.
RACK_HIERARCHY_STATION_NUMBERS = {
    'Faroe Islands': {1, 2},   # mirrors L01 + S16 style hatchery/rack-heavy sites
    'Scotland': {1, 2, 3},     # mirrors BRS/legacy Scottish rack usage
}

# FT marine area-group distribution from Ext_GroupedOrganisation_v2 (MarineSite),
# excluding "Not in use". We allocate synthetic areas with proportional weights.
SEA_AREA_GROUP_WEIGHTS = {
    'Faroe Islands': {
        'North': 8,
        'South': 4,
        'West': 13,
    },
    'Scotland': {
        'LOCH FYNE': 10,
        # FT-inspired deeper branch split for LEWIS hierarchy.
        'LEWIS North': 3,
        'LEWIS South': 2,
        'HARRIS': 5,
        'BENBECULA': 3,
        'SKYE and MAINLAND': 4,
        'STRIVEN,ARRAN,MULL,GIGHA': 8,
    },
}


def _station_uses_rack_hierarchy(geography_name, station_num):
    """Return True if the station should emulate Hall->Rack->Tray hierarchy."""
    return station_num in RACK_HIERARCHY_STATION_NUMBERS.get(geography_name, set())


def _build_weighted_area_group_sequence(geography_name, area_groups, total_areas):
    """
    Build deterministic weighted area-group sequence for area creation.

    Uses largest-remainder allocation + round-robin interleaving so generated
    areas stay distributed while still matching FT-like group proportions.
    """
    if total_areas <= 0 or not area_groups:
        return []

    configured_weights = SEA_AREA_GROUP_WEIGHTS.get(geography_name, {})
    weights = {}
    for group in area_groups:
        weights[group.name] = max(1, int(configured_weights.get(group.name, 1)))

    total_weight = sum(weights.values()) or len(area_groups)
    allocations = {}
    remainders = []
    assigned = 0

    for group in area_groups:
        exact = (total_areas * weights[group.name]) / total_weight
        floor_count = int(exact)
        allocations[group.name] = floor_count
        remainders.append((exact - floor_count, group.name))
        assigned += floor_count

    for _, group_name in sorted(remainders, reverse=True):
        if assigned >= total_areas:
            break
        allocations[group_name] += 1
        assigned += 1

    # Interleave groups to avoid large contiguous blocks.
    sequence = []
    while len(sequence) < total_areas:
        made_progress = False
        for group in area_groups:
            if allocations[group.name] <= 0:
                continue
            sequence.append(group)
            allocations[group.name] -= 1
            made_progress = True
            if len(sequence) >= total_areas:
                break
        if not made_progress:
            break

    if len(sequence) < total_areas:
        # Defensive fallback; should not trigger in normal allocation path.
        for idx in range(total_areas - len(sequence)):
            sequence.append(area_groups[idx % len(area_groups)])

    return sequence[:total_areas]


def print_progress(message, category=None):
    """Print progress message and update counter"""
    print(f"✓ {message}")
    if category:
        progress[category] += 1


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def create_geographies():
    """Create Scotland (if not exists) and Faroe Islands"""
    print_section("Phase 1.1: Creating Geographies")
    
    # Scotland (should exist)
    scotland, created = Geography.objects.get_or_create(
        name="Scotland",
        defaults={'description': 'Scotland aquaculture region'}
    )
    if created:
        print_progress(f"Created geography: Scotland (ID: {scotland.id})", 'geographies')
    else:
        print(f"✓ Geography already exists: Scotland (ID: {scotland.id})")
    
    # Faroe Islands
    faroe, created = Geography.objects.get_or_create(
        name="Faroe Islands",
        defaults={'description': 'Faroe Islands aquaculture region'}
    )
    if created:
        print_progress(f"Created geography: Faroe Islands (ID: {faroe.id})", 'geographies')
    else:
        print(f"✓ Geography already exists: Faroe Islands (ID: {faroe.id})")
    
    return scotland, faroe


def get_or_create_container_types():
    """Get or create container types for all lifecycle stages"""
    print_section("Phase 1.2: Verifying Container Types")
    
    types_config = [
        ('Incubation Rack', 'OTHER', 20.0, 'Structural rack for incubation trays'),
        ('Incubation Trays', 'TRAY', 10.0, 'Egg & Alevin stage trays'),
        ('Small Tanks - Fry', 'TANK', 100.0, 'Fry stage tanks'),
        ('Medium Tanks - Parr', 'TANK', 500.0, 'Parr stage tanks'),
        ('Large Tanks - Smolt', 'TANK', 1000.0, 'Smolt stage tanks'),
        ('Pre-Transfer Tanks - Post-Smolt', 'TANK', 2000.0, 'Post-Smolt stage tanks'),
        ('Sea Rings', 'PEN', 50000.0, 'Adult stage sea cages/rings'),
        ('Feed Silo', 'SILO', 5000.0, 'Hall feed storage silo'),
        ('Feed Barge', 'BARGE', 25000.0, 'Sea area feed storage barge'),
    ]
    
    container_types = {}
    for name, category, volume, description in types_config:
        ct, created = ContainerType.objects.get_or_create(
            name=name,
            defaults={
                'category': category,
                'max_volume_m3': Decimal(str(volume)),
                'description': description
            }
        )
        container_types[name] = ct
        status = "Created" if created else "Exists"
        print(f"✓ {status}: {name} (ID: {ct.id})")
    
    return container_types


def create_area_groups(scotland, faroe):
    """
    Create synthetic marine area-group hierarchy and return leaf groups for assignment.

    All generated sea areas are linked to a child group to emulate FishTalk structure.
    """
    print_section("Phase 1.3: Creating Area Groups")

    group_specs = {
        'Faroe Islands': {
            'North': [],
            'South': [],
            'West': [],
        },
        'Scotland': {
            'LOCH FYNE': [],
            'LEWIS': ['LEWIS North', 'LEWIS South'],
            'HARRIS': [],
            'BENBECULA': [],
            'SKYE and MAINLAND': [],
            'STRIVEN,ARRAN,MULL,GIGHA': [],
        },
    }

    roots = {
        'Faroe Islands': faroe,
        'Scotland': scotland,
    }
    assignment_groups = {}

    for geography_name, group_tree in group_specs.items():
        geography = roots[geography_name]
        root_name = f"{geography_name} Marine"
        root_group, created = AreaGroup.objects.get_or_create(
            name=root_name,
            geography=geography,
            parent=None,
            defaults={
                'code': geography_name.upper().replace(' ', '_')[:32],
                'active': True,
            }
        )
        if created:
            print_progress(f"Created area-group root: {root_name}", 'area_groups')
        else:
            print(f"✓ Area-group root exists: {root_name}")

        assignable = []
        for group_name, subgroup_names in group_tree.items():
            parent_group, created = AreaGroup.objects.get_or_create(
                name=group_name,
                geography=geography,
                parent=root_group,
                defaults={
                    'code': group_name.upper().replace(' ', '_')[:32],
                    'active': True,
                }
            )
            if created:
                print_progress(
                    f"  Created area-group leaf: {root_name} / {group_name}",
                    'area_groups',
                )
            else:
                print(f"✓   Area-group leaf exists: {root_name} / {group_name}")

            if subgroup_names:
                for subgroup_name in subgroup_names:
                    subgroup, created = AreaGroup.objects.get_or_create(
                        name=subgroup_name,
                        geography=geography,
                        parent=parent_group,
                        defaults={
                            'code': subgroup_name.upper().replace(' ', '_')[:32],
                            'active': True,
                        }
                    )
                    if created:
                        print_progress(
                            f"    Created area-group subleaf: {root_name} / {group_name} / {subgroup_name}",
                            'area_groups',
                        )
                    else:
                        print(f"✓     Area-group subleaf exists: {root_name} / {group_name} / {subgroup_name}")
                    assignable.append(subgroup)
            else:
                assignable.append(parent_group)

        assignment_groups[geography_name] = assignable

    return assignment_groups


def create_freshwater_station(geography, station_num, container_types):
    """
    Create one freshwater station with 5 halls, 10 containers per hall, and 1 silo per hall.
    
    Hall configuration:
    - Hall A: Egg/Alevin (Incubation Trays)
    - Hall B: Fry (Small Tanks)
    - Hall C: Parr (Medium Tanks)
    - Hall D: Smolt (Large Tanks)
    - Hall E: Post-Smolt (Pre-Transfer Tanks)
    """
    prefix = "S" if geography.name == "Scotland" else "FI"
    station_name = f"{prefix}-FW-{station_num:02d}"
    
    # Create station
    station, created = FreshwaterStation.objects.get_or_create(
        name=station_name,
        defaults={
            'geography': geography,
            'station_type': 'FRESHWATER',
            'latitude': Decimal('62.0') if geography.name == "Faroe Islands" else Decimal('57.5'),
            'longitude': Decimal('-7.0') if geography.name == "Faroe Islands" else Decimal('-4.5'),
            'description': f'Freshwater station {station_num} in {geography.name}',
            'active': True
        }
    )

    if created:
        print_progress(f"Created station: {station_name}", 'stations')
    else:
        print(f"✓ Station exists: {station_name} (ensuring halls/containers)")
    
    # Hall configuration
    hall_configs = [
        ('A', 'Egg & Alevin Hall', container_types['Incubation Trays']),
        ('B', 'Fry Hall', container_types['Small Tanks - Fry']),
        ('C', 'Parr Hall', container_types['Medium Tanks - Parr']),
        ('D', 'Smolt Hall', container_types['Large Tanks - Smolt']),
        ('E', 'Post-Smolt Hall', container_types['Pre-Transfer Tanks - Post-Smolt']),
    ]
    
    for hall_letter, hall_desc, container_type in hall_configs:
        # Create hall
        hall, _ = Hall.objects.get_or_create(
            name=f"{station_name}-Hall-{hall_letter}",
            freshwater_station=station,
            defaults={
                'description': hall_desc,
                'area_sqm': Decimal('1000.0'),
                'active': True
            }
        )
        print_progress(f"  Created hall: {hall.name}", 'halls')
        
        use_rack_hierarchy = (
            hall_letter == 'A'
            and _station_uses_rack_hierarchy(geography.name, station_num)
        )

        # Selected Egg&Alevin halls emulate rack -> tray hierarchy:
        # - structural racks (parent containers)
        # - holding trays (child containers, assignable)
        if use_rack_hierarchy:
            rack_type = container_types['Incubation Rack']
            tray_index = 1

            for rack_idx in range(1, RACKS_PER_INCUBATION_HALL + 1):
                rack_name = f"{station_name}-{hall_letter}-R{rack_idx:02d}"
                rack, rack_created = Container.objects.get_or_create(
                    name=rack_name,
                    defaults={
                        'container_type': rack_type,
                        'hall': hall,
                        'parent_container': None,
                        'hierarchy_role': 'STRUCTURAL',
                        'volume_m3': rack_type.max_volume_m3,
                        'max_biomass_kg': Decimal('0.0'),
                        'active': True,
                    }
                )
                if not rack_created and rack.hierarchy_role != 'STRUCTURAL':
                    rack.hierarchy_role = 'STRUCTURAL'
                    rack.parent_container = None
                    rack.hall = hall
                    rack.save(update_fields=['hierarchy_role', 'parent_container', 'hall'])
                print_progress(f"    Created rack: {rack_name}", 'containers')
                progress['structural_containers'] += 1

                for _ in range(TRAYS_PER_RACK):
                    tray_name = f"{station_name}-{hall_letter}-C{tray_index:02d}"
                    tray, tray_created = Container.objects.get_or_create(
                        name=tray_name,
                        defaults={
                            'container_type': container_type,
                            'hall': hall,
                            'parent_container': rack,
                            'hierarchy_role': 'HOLDING',
                            'volume_m3': container_type.max_volume_m3,
                            'max_biomass_kg': container_type.max_volume_m3 * Decimal('50.0'),
                            'active': True,
                        }
                    )
                    if not tray_created and (
                        tray.parent_container_id != rack.id
                        or tray.hierarchy_role != 'HOLDING'
                        or tray.hall_id != hall.id
                    ):
                        tray.parent_container = rack
                        tray.hierarchy_role = 'HOLDING'
                        tray.hall = hall
                        tray.save(update_fields=['parent_container', 'hierarchy_role', 'hall'])
                    print_progress(f"    Created tray: {tray_name}", 'containers')
                    progress['holding_containers'] += 1
                    create_sensors_for_container(tray)
                    tray_index += 1
        else:
            # Non-rack halls use flat holding containers.
            for i in range(1, 11):
                container_name = f"{station_name}-{hall_letter}-C{i:02d}"
                container, created = Container.objects.get_or_create(
                    name=container_name,
                    defaults={
                        'container_type': container_type,
                        'hall': hall,
                        'parent_container': None,
                        'hierarchy_role': 'HOLDING',
                        'volume_m3': container_type.max_volume_m3,
                        'max_biomass_kg': container_type.max_volume_m3 * Decimal('50.0'),
                        'active': True
                    }
                )
                if not created and (
                    container.hierarchy_role != 'HOLDING'
                    or container.parent_container_id is not None
                ):
                    container.hierarchy_role = 'HOLDING'
                    container.parent_container = None
                    container.save(update_fields=['hierarchy_role', 'parent_container'])
                print_progress(f"    Created container: {container_name}", 'containers')
                progress['holding_containers'] += 1
                
                # Create sensors for container
                create_sensors_for_container(container)

            if hall_letter == 'A':
                stale_rack_qs = Container.objects.filter(
                    hall=hall,
                    hierarchy_role='STRUCTURAL',
                )
                stale_count = stale_rack_qs.count()
                if stale_count:
                    stale_rack_qs.delete()
                    print(f"✓   Removed {stale_count} stale structural racks from {hall.name}")
        
        # Create feed silo for hall with stage-appropriate capacity
        # Hall A (Egg&Alevin): 5t (minimal, they feed from egg sac)
        # Hall B (Fry): 10t (very small fish, low consumption)
        # Hall C (Parr): 15t (growing fish)
        # Hall D (Smolt): 20t (increased consumption)
        # Hall E (Post-Smolt): 30t (high consumption before sea transfer)
        capacities = {
            'A': Decimal('5000.0'),   # 5 tonnes
            'B': Decimal('10000.0'),  # 10 tonnes
            'C': Decimal('15000.0'),  # 15 tonnes
            'D': Decimal('20000.0'),  # 20 tonnes
            'E': Decimal('30000.0'),  # 30 tonnes
        }
        
        silo_name = f"{station_name}-{hall_letter}-Silo"
        FeedContainer.objects.get_or_create(
            name=silo_name,
            defaults={
                'container_type': 'SILO',
                'hall': hall,
                'capacity_kg': capacities.get(hall_letter, Decimal('10000.0')),
                'active': True
            }
        )
        print_progress(f"    Created silo: {silo_name}", 'feed_containers')


def create_sea_area(geography, area_num, container_types, area_group):
    """
    Create one sea area with 20 rings and 3 feed barges.
    """
    prefix = "S" if geography.name == "Scotland" else "FI"
    area_name = f"{prefix}-SEA-{area_num:02d}"
    
    # Create area
    area, created = Area.objects.get_or_create(
        name=area_name,
        geography=geography,
        defaults={
            'area_group': area_group,
            'latitude': Decimal('61.5') if geography.name == "Faroe Islands" else Decimal('57.0'),
            'longitude': Decimal('-6.5') if geography.name == "Faroe Islands" else Decimal('-5.0'),
            'max_biomass': Decimal('5000000.0'),  # 5M kg capacity (500 tonnes)
            'active': True
        }
    )
    if not created and area.area_group_id != area_group.id:
        area.area_group = area_group
        area.save(update_fields=['area_group'])
    
    if not created:
        print(f"  Area {area_name} already exists, skipping...")
        return
    
    print_progress(f"Created area: {area_name}", 'areas')
    
    # Create 20 sea rings
    ring_type = container_types['Sea Rings']
    for i in range(1, 21):
        ring_name = f"{area_name}-Ring-{i:02d}"
        container, _ = Container.objects.get_or_create(
            name=ring_name,
            defaults={
                'container_type': ring_type,
                'area': area,
                'parent_container': None,
                'hierarchy_role': 'HOLDING',
                'volume_m3': ring_type.max_volume_m3,
                'max_biomass_kg': Decimal('500000.0'),  # 500 tonnes per sea ring
                'active': True
            }
        )
        print_progress(f"  Created ring: {ring_name}", 'rings')
        progress['holding_containers'] += 1
        
        # Create sensors for ring (sea sensors: Temperature, DO, pH, Salinity)
        create_sensors_for_sea_container(container)
    
    # Create 3 feed barges (50 tonnes each)
    # Industry standard: GroAqua Barge FF 700 has ~700t / 12 silos = 58t per silo
    # We use 50t as a reasonable per-barge capacity
    for i in range(1, 4):
        barge_name = f"{area_name}-Barge-{i}"
        FeedContainer.objects.get_or_create(
            name=barge_name,
            defaults={
                'container_type': 'BARGE',
                'area': area,
                'capacity_kg': Decimal('50000.0'),  # 50 tonnes per barge
                'active': True
            }
        )
        print_progress(f"  Created barge: {barge_name}", 'feed_containers')


def create_sensors_for_container(container):
    """
    Create 7 sensors for freshwater container:
    Temperature, Dissolved Oxygen, pH, CO2, NO2, NO3, NH4
    """
    sensor_types = [
        'Temperature',
        'Dissolved Oxygen',
        'pH',
        'CO2',
        'NO2',
        'NO3',
        'NH4'
    ]
    
    for sensor_type in sensor_types:
        sensor_name = f"{container.name}-{sensor_type.replace(' ', '')}"
        Sensor.objects.get_or_create(
            name=sensor_name,
            defaults={
                'sensor_type': sensor_type,
                'container': container,
                'serial_number': f"SN-{container.id}-{sensor_type[:3].upper()}",
                'manufacturer': 'AquaSense',
                'active': True
            }
        )
        progress['sensors'] += 1


def create_sensors_for_sea_container(container):
    """
    Create 4 sensors for sea container:
    Temperature, Dissolved Oxygen, pH, Salinity (no nitrogen compounds measured in sea)
    """
    sensor_types = [
        'Temperature',
        'Dissolved Oxygen',
        'pH',
        'Salinity'
    ]
    
    for sensor_type in sensor_types:
        sensor_name = f"{container.name}-{sensor_type.replace(' ', '')}"
        Sensor.objects.get_or_create(
            name=sensor_name,
            defaults={
                'sensor_type': sensor_type,
                'container': container,
                'serial_number': f"SN-{container.id}-{sensor_type[:3].upper()}",
                'manufacturer': 'AquaSense',
                'active': True
            }
        )
        progress['sensors'] += 1


def create_scotland_infrastructure(scotland, container_types, area_groups):
    """Create all Scotland infrastructure"""
    print_section("Phase 1.4: Creating Scotland Infrastructure")
    
    # 10 Freshwater Stations
    print("\n--- Creating Freshwater Stations ---")
    for station_num in range(1, 11):
        create_freshwater_station(scotland, station_num, container_types)
    
    # 20 Sea Areas
    print("\n--- Creating Sea Areas ---")
    group_sequence = _build_weighted_area_group_sequence(
        geography_name='Scotland',
        area_groups=area_groups,
        total_areas=20,
    )
    for area_num, area_group in enumerate(group_sequence, start=1):
        create_sea_area(scotland, area_num, container_types, area_group)


def create_faroe_infrastructure(faroe, container_types, area_groups):
    """Create all Faroe Islands infrastructure"""
    print_section("Phase 1.5: Creating Faroe Islands Infrastructure")
    
    # 12 Freshwater Stations
    print("\n--- Creating Freshwater Stations ---")
    for station_num in range(1, 13):
        create_freshwater_station(faroe, station_num, container_types)
    
    # 22 Sea Areas
    print("\n--- Creating Sea Areas ---")
    group_sequence = _build_weighted_area_group_sequence(
        geography_name='Faroe Islands',
        area_groups=area_groups,
        total_areas=22,
    )
    for area_num, area_group in enumerate(group_sequence, start=1):
        create_sea_area(faroe, area_num, container_types, area_group)


def validate_infrastructure():
    """Validate infrastructure creation with SQL-like queries"""
    print_section("Phase 1.5: Validating Infrastructure")
    expected_area_groups = 13
    expected_structural = (
        (len(RACK_HIERARCHY_STATION_NUMBERS['Scotland']) + len(RACK_HIERARCHY_STATION_NUMBERS['Faroe Islands']))
        * RACKS_PER_INCUBATION_HALL
    )
    
    validations = [
        ("Geographies", Geography.objects.count(), 2),
        ("Area Groups", AreaGroup.objects.count(), expected_area_groups),
        ("Freshwater Stations", FreshwaterStation.objects.count(), 22),
        ("Halls", Hall.objects.count(), 110),
        (
            "Freshwater Holding Containers",
            Container.objects.filter(hall__isnull=False, hierarchy_role='HOLDING').count(),
            1100,
        ),
        (
            "Freshwater Structural Containers",
            Container.objects.filter(hall__isnull=False, hierarchy_role='STRUCTURAL').count(),
            expected_structural,
        ),
        ("Sea Areas", Area.objects.count(), 42),
        (
            "Sea Rings",
            Container.objects.filter(area__isnull=False, hierarchy_role='HOLDING').count(),
            840,
        ),
        (
            "Areas Linked To Group",
            Area.objects.filter(area_group__isnull=False).count(),
            42,
        ),
        ("Feed Containers", FeedContainer.objects.count(), 236),
        ("Sensors", Sensor.objects.count(), 11060),  # 1100*7 + 840*4
    ]
    
    all_valid = True
    for name, actual, expected in validations:
        status = "✓" if actual >= expected * 0.9 else "✗"  # Allow 10% tolerance
        print(f"{status} {name}: {actual} (expected: {expected})")
        if actual < expected * 0.9:
            all_valid = False
    
    return all_valid


def print_summary():
    """Print final summary"""
    print_section("Infrastructure Bootstrap Complete!")
    
    print(f"""
Summary of Created Infrastructure:
{'='*80}
Geographies:          {progress['geographies']}
Area Groups:          {progress['area_groups']}
Freshwater Stations:  {progress['stations']}
Halls:                {progress['halls']}
FW Containers:        {progress['containers']}
  Holding:            {progress['holding_containers']}
  Structural:         {progress['structural_containers']}
Sea Areas:            {progress['areas']}
Sea Rings:            {progress['rings']}
Feed Containers:      {progress['feed_containers']}
Sensors:              {progress['sensors']}
{'='*80}

Total Operational Containers: {progress['holding_containers']}
Total Feed Containers:        {progress['feed_containers']}
Total Infrastructure Assets:  {progress['containers'] + progress['rings'] + progress['feed_containers'] + progress['sensors'] + progress['area_groups']}
""")


def _read_reference_pack_csv(reference_pack_dir, filename):
    """Read one CSV from a reference pack directory."""
    path = Path(reference_pack_dir) / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _collect_reference_pack_filters(reference_pack_dir):
    """
    Collect source IDs from reference pack files.

    The pack is the primary allow-list; FT extraction is used to enrich each
    referenced container with hierarchy/group metadata needed for bootstrap.
    """
    containers_rows = _read_reference_pack_csv(reference_pack_dir, "infrastructure_containers.csv")
    if not containers_rows:
        raise ValueError(
            f"Reference pack missing infrastructure_containers.csv: {reference_pack_dir}"
        )
    stations_rows = _read_reference_pack_csv(reference_pack_dir, "infrastructure_stations.csv")
    areas_rows = _read_reference_pack_csv(reference_pack_dir, "infrastructure_areas.csv")

    source_container_ids = set()
    source_org_ids = set()
    for row in containers_rows:
        source_container_id = (row.get("source_container_id") or "").strip()
        if source_container_id:
            source_container_ids.add(source_container_id)
        source_org_id = (
            row.get("source_org_unit_id")
            or row.get("source_orgunit_id")
            or ""
        ).strip()
        if source_org_id:
            source_org_ids.add(source_org_id)

    for row in stations_rows:
        source_org_id = (
            row.get("source_orgunit_id")
            or row.get("source_org_unit_id")
            or ""
        ).strip()
        if source_org_id:
            source_org_ids.add(source_org_id)

    for row in areas_rows:
        source_org_id = (
            row.get("source_orgunit_id")
            or row.get("source_org_unit_id")
            or ""
        ).strip()
        if source_org_id:
            source_org_ids.add(source_org_id)

    if not source_container_ids:
        raise ValueError(
            "Reference pack does not contain source_container_id values; "
            "cannot map to FT hierarchy metadata."
        )

    return {
        "source_container_ids": source_container_ids,
        "source_org_ids": source_org_ids,
        "pack_container_rows": len(containers_rows),
        "pack_station_rows": len(stations_rows),
        "pack_area_rows": len(areas_rows),
    }


def _filter_extracted_infra_rows(
    *,
    container_rows,
    site_rows,
    source_container_ids,
    source_org_ids,
    include_not_in_use=False,
):
    """Filter FT extraction to the reference-pack allow-list."""
    filtered_containers = []
    for row in container_rows:
        container_id = (row.get("ContainerID") or "").strip()
        if not container_id or container_id not in source_container_ids:
            continue
        site_group = (row.get("SiteGroup") or "").strip().upper()
        if not include_not_in_use and site_group == EXCLUDED_MARINE_GROUP:
            continue
        filtered_containers.append(row)

    if not filtered_containers:
        raise ValueError(
            "No FT containers matched reference-pack source_container_id allow-list."
        )

    org_ids = {
        (row.get("OrgUnitID") or "").strip()
        for row in filtered_containers
        if (row.get("OrgUnitID") or "").strip()
    }
    if source_org_ids:
        org_ids |= source_org_ids

    filtered_sites = [
        row for row in site_rows
        if (row.get("OrgUnitID") or "").strip() in org_ids
    ]
    return filtered_containers, filtered_sites


def _ensure_reference_mode_feed_containers():
    """
    Ensure event-engine feed dependencies exist for realistic infrastructure.

    We keep this minimal and deterministic: one silo per hall, one barge per area.
    """
    created_silos = 0
    created_barges = 0

    for hall in Hall.objects.all():
        existing = FeedContainer.objects.filter(hall=hall, container_type="SILO").first()
        if existing:
            continue
        FeedContainer.objects.create(
            name=f"{hall.name}-Silo",
            container_type="SILO",
            hall=hall,
            capacity_kg=Decimal("10000.0"),
            active=True,
        )
        created_silos += 1

    for area in Area.objects.all():
        existing = FeedContainer.objects.filter(area=area, container_type="BARGE").first()
        if existing:
            continue
        FeedContainer.objects.create(
            name=f"{area.name}-Barge-1",
            container_type="BARGE",
            area=area,
            capacity_kg=Decimal("25000.0"),
            active=True,
        )
        created_barges += 1

    return created_silos, created_barges


def _ensure_reference_mode_sensors():
    """Ensure holding containers have expected sensors for event generation."""
    freshwater_sensor_types = [
        "Temperature",
        "Dissolved Oxygen",
        "pH",
        "CO2",
        "NO2",
        "NO3",
        "NH4",
    ]
    sea_sensor_types = [
        "Temperature",
        "Dissolved Oxygen",
        "pH",
        "Salinity",
    ]

    created = 0
    holding_containers = Container.objects.filter(
        active=True,
        hierarchy_role=HOLDING_ROLE,
    ).select_related("hall", "area")

    for container in holding_containers:
        if container.area_id:
            sensor_types = sea_sensor_types
        elif container.hall_id:
            sensor_types = freshwater_sensor_types
        else:
            continue

        for sensor_type in sensor_types:
            sensor_name = f"{container.name}-{sensor_type.replace(' ', '')}"
            _, was_created = Sensor.objects.get_or_create(
                name=sensor_name,
                defaults={
                    "sensor_type": sensor_type,
                    "container": container,
                    "serial_number": f"SN-{container.id}-{sensor_type[:3].upper()}",
                    "manufacturer": "AquaSense",
                    "active": True,
                }
            )
            if was_created:
                created += 1

    return created


def _print_reference_mode_summary(loader_stats):
    """Print concise summary for realistic bootstrap mode."""
    structural_count = Container.objects.filter(hierarchy_role="STRUCTURAL").count()
    holding_count = Container.objects.filter(hierarchy_role="HOLDING").count()
    areas_total = Area.objects.count()
    areas_linked = Area.objects.filter(area_group__isnull=False).count()
    area_groups_total = AreaGroup.objects.count()

    print_section("Realistic Infrastructure Summary")
    print("Loader stats:")
    print(
        f"  Stations created/updated: "
        f"{loader_stats['stations'].get('created', 0)}/"
        f"{loader_stats['stations'].get('updated', 0)}"
    )
    print(
        f"  Areas created/updated: "
        f"{loader_stats['areas'].get('created', 0)}/"
        f"{loader_stats['areas'].get('updated', 0)}"
    )
    print(
        f"  Halls created/updated: "
        f"{loader_stats['halls'].get('created', 0)}/"
        f"{loader_stats['halls'].get('updated', 0)}"
    )
    print(
        f"  Structural racks created/updated: "
        f"{loader_stats['racks'].get('created', 0)}/"
        f"{loader_stats['racks'].get('updated', 0)}"
    )
    print(
        f"  Holding containers created/updated: "
        f"{loader_stats['containers'].get('created', 0)}/"
        f"{loader_stats['containers'].get('updated', 0)}"
    )
    print()
    print("Current DB totals:")
    print(f"  Geographies: {Geography.objects.count()}")
    print(f"  Area Groups: {area_groups_total}")
    print(f"  Stations: {FreshwaterStation.objects.count()}")
    print(f"  Halls: {Hall.objects.count()}")
    print(f"  Containers (holding): {holding_count}")
    print(f"  Containers (structural): {structural_count}")
    print(f"  Areas: {areas_total}")
    print(f"  Areas linked to area group: {areas_linked}/{areas_total}")


def _dedupe_imported_container_types():
    """
    Normalize duplicate FishTalk-imported container types in default DB.

    The migration loader expects name lookups to resolve to a single row.
    """
    managed_names = [
        "FishTalk Imported Tank",
        "FishTalk Imported Pen",
        "FishTalk Imported Rack",
    ]
    deduped = 0
    for type_name in managed_names:
        duplicates = list(ContainerType.objects.filter(name=type_name).order_by("id"))
        if len(duplicates) <= 1:
            continue
        keeper = duplicates[0]
        for duplicate in duplicates[1:]:
            Container.objects.filter(container_type=duplicate).update(container_type=keeper)
            duplicate.delete()
            deduped += 1
    return deduped


def run_reference_pack_bootstrap(args):
    """
    Realistic bootstrap path:
    - Uses reference pack as source allow-list
    - Reuses migration extractor+loader compatibility layer
    - Preserves hierarchy and area-group semantics from FT metadata
    """
    reference_pack_dir = Path(args.reference_pack).resolve()
    if not reference_pack_dir.exists():
        raise FileNotFoundError(f"Reference pack directory not found: {reference_pack_dir}")

    print_section("Phase 1R: Reference-Pack Infrastructure Bootstrap")
    print(f"Reference pack: {reference_pack_dir}")
    print(f"SQL profile: {args.sql_profile}")
    if args.include_not_in_use:
        print("Marine group handling: include 'Not in use'")
    else:
        print("Marine group handling: exclude 'Not in use'")

    filters = _collect_reference_pack_filters(reference_pack_dir)
    print(
        "Reference pack rows: "
        f"containers={filters['pack_container_rows']}, "
        f"stations={filters['pack_station_rows']}, "
        f"areas={filters['pack_area_rows']}"
    )
    print(
        f"Allow-list IDs: containers={len(filters['source_container_ids'])}, "
        f"org_units={len(filters['source_org_ids'])}"
    )

    extractor = InfrastructureExtractor(
        context=ExtractionContext(
            profile=args.sql_profile,
            database=args.sql_database,
            container=args.sql_container,
        )
    )
    print("\nExtracting infrastructure rows from FT...")
    site_rows = extractor.fetch_sites()
    container_rows = extractor.fetch_containers()
    print(f"  Extracted sites: {len(site_rows)}")
    print(f"  Extracted containers: {len(container_rows)}")

    filtered_containers, filtered_sites = _filter_extracted_infra_rows(
        container_rows=container_rows,
        site_rows=site_rows,
        source_container_ids=filters["source_container_ids"],
        source_org_ids=filters["source_org_ids"],
        include_not_in_use=args.include_not_in_use,
    )
    print(f"  Filtered sites: {len(filtered_sites)}")
    print(f"  Filtered containers: {len(filtered_containers)}")

    deduped_types = _dedupe_imported_container_types()
    if deduped_types:
        print(f"  Container type preflight: deduped {deduped_types} duplicate imported type rows")

    loader = InfrastructureLoader(dry_run=args.dry_run)
    loader_stats = loader.load_sites_and_containers(filtered_sites, filtered_containers)

    if args.dry_run:
        print_section("Reference-Pack Dry Run Complete")
        print("No DB writes performed.")
        print(
            "Projected creates: "
            f"stations={loader_stats['stations'].get('created', 0)}, "
            f"areas={loader_stats['areas'].get('created', 0)}, "
            f"halls={loader_stats['halls'].get('created', 0)}, "
            f"racks={loader_stats['racks'].get('created', 0)}, "
            f"containers={loader_stats['containers'].get('created', 0)}"
        )
        return 0

    created_silos, created_barges = _ensure_reference_mode_feed_containers()
    created_sensors = _ensure_reference_mode_sensors()
    print(
        "\nSupport assets: "
        f"silos_created={created_silos}, "
        f"barges_created={created_barges}, "
        f"sensors_created={created_sensors}"
    )

    _print_reference_mode_summary(loader_stats)

    total_areas = Area.objects.count()
    linked_areas = Area.objects.filter(area_group__isnull=False).count()
    if total_areas and linked_areas != total_areas:
        print(
            "\n✗ Reference-pack bootstrap warning: not all areas are linked to area groups "
            f"({linked_areas}/{total_areas})."
        )
        return 1

    print("\n✓ Phase 1R COMPLETE: Realistic infrastructure bootstrap successful!\n")
    return 0


def run_synthetic_bootstrap():
    """Run legacy synthetic bootstrap (default behavior)."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  AquaMind Test Data Generation - Phase 1: Bootstrap Infrastructure".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    try:
        # Phase 1.1: Geographies
        scotland, faroe = create_geographies()
        
        # Phase 1.2: Container Types
        container_types = get_or_create_container_types()
        
        # Phase 1.3: Area Groups
        area_groups = create_area_groups(scotland, faroe)

        # Phase 1.4: Scotland Infrastructure
        create_scotland_infrastructure(
            scotland,
            container_types,
            area_groups['Scotland'],
        )

        # Phase 1.5: Faroe Islands Infrastructure
        create_faroe_infrastructure(
            faroe,
            container_types,
            area_groups['Faroe Islands'],
        )

        # Phase 1.6: Validation
        valid = validate_infrastructure()
        
        # Summary
        print_summary()
        
        if valid:
            print("\n✓ Phase 1 COMPLETE: Infrastructure bootstrap successful!\n")
            return 0
        else:
            print("\n⚠ Phase 1 COMPLETE with warnings: Some counts below expected.\n")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during infrastructure setup: {e}")
        import traceback
        traceback.print_exc()
        return 1


def parse_args():
    """Parse CLI args for legacy synthetic vs realistic reference-pack mode."""
    parser = argparse.ArgumentParser(
        description="Bootstrap infrastructure (synthetic default or realistic reference-pack mode)."
    )
    parser.add_argument(
        "--reference-pack",
        type=str,
        default=None,
        help=(
            "Optional reference pack path. When provided, bootstraps infrastructure "
            "from FT metadata using the pack as allow-list "
            "(for example scripts/data_generation/reference_pack/latest)."
        ),
    )
    parser.add_argument(
        "--sql-profile",
        type=str,
        default="fishtalk_readonly",
        help="SQL Server profile for realistic mode (default: fishtalk_readonly).",
    )
    parser.add_argument(
        "--sql-database",
        type=str,
        default=None,
        help="Optional SQL Server database override for realistic mode.",
    )
    parser.add_argument(
        "--sql-container",
        type=str,
        default=None,
        help="Optional SQL Server docker container override for realistic mode.",
    )
    parser.add_argument(
        "--include-not-in-use",
        action="store_true",
        help="Include SiteGroup='Not in use' marine containers in realistic mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run realistic mode without writing DB rows.",
    )
    return parser.parse_args()


def main():
    """Main execution."""
    args = parse_args()
    if args.reference_pack:
        return run_reference_pack_bootstrap(args)
    if args.dry_run:
        print("⚠ --dry-run is only supported with --reference-pack; running synthetic bootstrap normally.")
    return run_synthetic_bootstrap()


if __name__ == '__main__':
    sys.exit(main())
