"""
Infrastructure Generator for AquaMind Data Generation

Handles creation of geography hierarchy, areas, facilities, and equipment.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, 
    Container, ContainerType, Sensor
)
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class InfrastructureGenerator:
    """
    Generates infrastructure data including:
    - Geography hierarchy (Faroe Islands, Scotland)
    - Areas within geographies
    - Freshwater stations (hatcheries, nurseries, smolt facilities)
    - Sea sites with pen configurations
    - Sensors and equipment
    - Feed storage facilities
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the infrastructure generator.
        
        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run
        self.created_objects = {
            'geographies': [],
            'areas': [],
            'stations': [],
            'halls': [],
            'containers': [],
            'sensors': []
        }
        
        # Get or create system user for audit trails
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='data_generator',
                defaults={
                    'email': 'generator@aquamind.com',
                    'first_name': 'Data',
                    'last_name': 'Generator',
                    'is_staff': False,
                    'is_active': True
                }
            )
    
    def generate_all(self) -> Dict[str, int]:
        """
        Generate all infrastructure data.
        
        Returns:
            Dictionary with counts of created objects
        """
        logger.info("Starting infrastructure generation...")
        
        with transaction.atomic():
            # Create container types first (needed for containers)
            self._create_container_types()
            
            # Create geography hierarchy
            self._create_geographies()
            
            # Create areas within geographies
            self._create_areas()
            
            # Create freshwater stations
            self._create_freshwater_stations()
            
            # Create sea sites
            self._create_sea_sites()
            
            # Create sensors and equipment
            self._create_sensors()
            
        # Return summary
        return {
            'geographies': len(self.created_objects['geographies']),
            'areas': len(self.created_objects['areas']),
            'stations': len(self.created_objects['stations']),
            'halls': len(self.created_objects['halls']),
            'containers': len(self.created_objects['containers']),
            'sensors': len(self.created_objects['sensors'])
        }
    
    def _create_container_types(self):
        """Create all container types used in the facility."""
        logger.info("Creating container types...")
        
        container_types_data = [
            # Freshwater containers
            {
                'name': 'Incubation Tray',
                'category': 'TRAY',
                'max_volume_m3': Decimal('0.2'),
                'description': 'Egg incubation trays'
            },
            {
                'name': 'Start Tank',
                'category': 'TANK',
                'max_volume_m3': Decimal('1.5'),
                'description': 'Initial rearing tanks for alevin'
            },
            {
                'name': 'Circular Tank Small',
                'category': 'TANK',
                'max_volume_m3': Decimal('10'),
                'description': 'Small circular tanks for fry'
            },
            {
                'name': 'Circular Tank Large',
                'category': 'TANK',
                'max_volume_m3': Decimal('35'),
                'description': 'Large circular tanks for parr'
            },
            {
                'name': 'Pre-Transfer Tank',
                'category': 'TANK',
                'max_volume_m3': Decimal('75'),
                'description': 'Pre-seawater transfer tanks for smolt'
            },
            # Seawater containers
            {
                'name': 'Sea Cage Small',
                'category': 'PEN',
                'max_volume_m3': Decimal('2000'),
                'description': 'Small sea cages for post-smolt'
            },
            {
                'name': 'Sea Cage Standard',
                'category': 'PEN',
                'max_volume_m3': Decimal('8000'),
                'description': 'Standard sea cages for grow-out'
            },
            {
                'name': 'Sea Cage Large',
                'category': 'PEN',
                'max_volume_m3': Decimal('20000'),
                'description': 'Large sea cages for grow-out'
            }
        ]
        
        if not self.dry_run:
            for data in container_types_data:
                ContainerType.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
        
        logger.info(f"Created {len(container_types_data)} container types")
    
    def _create_geographies(self):
        """Create geography hierarchy."""
        logger.info("Creating geography hierarchy...")
        
        geographies_data = [
            {
                'name': 'Faroe Islands',
                'description': 'Primary production region in North Atlantic'
            },
            {
                'name': 'Scotland', 
                'description': 'Secondary production region'
            }
        ]
        
        if not self.dry_run:
            for data in geographies_data:
                geo, created = Geography.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
                if created:
                    self.created_objects['geographies'].append(geo)
                    logger.info(f"Created geography: {geo.name}")
        else:
            logger.info(f"Would create {len(geographies_data)} geographies")
    
    def _create_areas(self):
        """Create areas within geographies."""
        logger.info("Creating areas...")
        
        if self.dry_run:
            logger.info("Would create areas for each geography")
            return
        
        # Faroe Islands areas
        faroe_geo = Geography.objects.get(name='Faroe Islands')
        faroe_areas = [
            {'name': 'Streymoy', 'latitude': 62.1100, 'longitude': -6.9700, 'max_biomass': 1000000},
            {'name': 'Eysturoy', 'latitude': 62.2000, 'longitude': -6.9000, 'max_biomass': 800000},
            {'name': 'Vágar', 'latitude': 62.0667, 'longitude': -7.2833, 'max_biomass': 600000},
            {'name': 'Sandoy', 'latitude': 61.8500, 'longitude': -6.8000, 'max_biomass': 700000},
            {'name': 'Suðuroy', 'latitude': 61.5333, 'longitude': -6.8667, 'max_biomass': 900000}
        ]
        
        for area_data in faroe_areas:
            area, created = Area.objects.get_or_create(
                name=area_data['name'],
                geography=faroe_geo,
                defaults={
                    'latitude': Decimal(str(area_data['latitude'])),
                    'longitude': Decimal(str(area_data['longitude'])),
                    'max_biomass': Decimal(str(area_data['max_biomass'])),
                    'active': True
                }
            )
            if created:
                self.created_objects['areas'].append(area)
        
        # Scotland areas
        scotland_geo = Geography.objects.get(name='Scotland')
        scotland_areas = [
            {'name': 'Shetland', 'latitude': 60.3000, 'longitude': -1.3000, 'max_biomass': 700000},
            {'name': 'Orkney', 'latitude': 59.0000, 'longitude': -3.0000, 'max_biomass': 500000},
            {'name': 'Western Isles', 'latitude': 57.7500, 'longitude': -7.0000, 'max_biomass': 900000},
            {'name': 'Highland West', 'latitude': 57.5000, 'longitude': -5.5000, 'max_biomass': 800000}
        ]
        
        for area_data in scotland_areas:
            area, created = Area.objects.get_or_create(
                name=area_data['name'],
                geography=scotland_geo,
                defaults={
                    'latitude': Decimal(str(area_data['latitude'])),
                    'longitude': Decimal(str(area_data['longitude'])),
                    'max_biomass': Decimal(str(area_data['max_biomass'])),
                    'active': True
                }
            )
            if created:
                self.created_objects['areas'].append(area)
        
        logger.info(f"Created {len(self.created_objects['areas'])} areas")
    
    def _create_freshwater_stations(self):
        """Create freshwater stations (hatcheries, nurseries, smolt facilities)."""
        logger.info("Creating freshwater stations...")
        
        if self.dry_run:
            logger.info("Would create freshwater stations")
            return
        
        # Get areas for station placement
        faroe_areas = Area.objects.filter(geography__name='Faroe Islands')
        scotland_areas = Area.objects.filter(geography__name='Scotland')
        
        station_configs = [
            # Faroe Islands stations
            {'area': faroe_areas.get(name='Streymoy'), 'name': 'Streymoy Hatchery', 'type': 'hatchery', 'halls': 4},
            {'area': faroe_areas.get(name='Streymoy'), 'name': 'Streymoy Nursery', 'type': 'nursery', 'halls': 6},
            {'area': faroe_areas.get(name='Eysturoy'), 'name': 'Eysturoy Smolt', 'type': 'smolt', 'halls': 8},
            {'area': faroe_areas.get(name='Vágar'), 'name': 'Vágar Hatchery', 'type': 'hatchery', 'halls': 3},
            {'area': faroe_areas.get(name='Sandoy'), 'name': 'Sandoy Nursery', 'type': 'nursery', 'halls': 4},
            # Scotland stations
            {'area': scotland_areas.get(name='Shetland'), 'name': 'Shetland Hatchery', 'type': 'hatchery', 'halls': 3},
            {'area': scotland_areas.get(name='Orkney'), 'name': 'Orkney Smolt', 'type': 'smolt', 'halls': 6},
            {'area': scotland_areas.get(name='Western Isles'), 'name': 'Western Isles Nursery', 'type': 'nursery', 'halls': 5}
        ]
        
        for config in station_configs:
            # Create station
            station, created = FreshwaterStation.objects.get_or_create(
                name=config['name'],
                defaults={
                    'geography': config['area'].geography,
                    'station_type': 'FRESHWATER',
                    'latitude': config['area'].latitude + Decimal(str(random.uniform(-0.1, 0.1))),
                    'longitude': config['area'].longitude + Decimal(str(random.uniform(-0.1, 0.1))),
                    'description': f'{config["type"].title()} facility in {config["area"].name}',
                    'active': True
                }
            )
            
            if created:
                self.created_objects['stations'].append(station)
                
                # Create halls for the station
                self._create_halls_for_station(station, config['halls'], config['type'])
        
        logger.info(f"Created {len(self.created_objects['stations'])} freshwater stations")
    
    def _create_halls_for_station(self, station: FreshwaterStation, num_halls: int, station_type: str):
        """Create halls and containers for a freshwater station."""
        
        # Determine container types based on station type
        # Increased capacity to handle realistic batch throughput
        if station_type == 'hatchery':
            container_types = ['Incubation Tray', 'Start Tank']
            containers_per_hall = 30  # Increased from 20
        elif station_type == 'nursery':
            container_types = ['Circular Tank Small', 'Circular Tank Large']
            containers_per_hall = 20  # Increased from 10
        else:  # smolt
            container_types = ['Circular Tank Large', 'Pre-Transfer Tank']
            containers_per_hall = 15  # Increased from 8
        
        for hall_num in range(1, num_halls + 1):
            hall_name = f"{station.name} Hall {hall_num}"
            hall, created = Hall.objects.get_or_create(
                name=hall_name,
                defaults={
                    'freshwater_station': station,
                    'description': f'Hall {hall_num} at {station.name}',
                    'area_sqm': Decimal(str(random.randint(200, 500))),
                    'active': True
                }
            )
            
            if created:
                self.created_objects['halls'].append(hall)
                
                # Create containers in the hall
                self._create_containers_for_hall(hall, container_types, containers_per_hall)
    
    def _create_containers_for_hall(self, hall: Hall, container_type_names: List[str], num_containers: int):
        """Create containers for a hall."""
        
        container_types = ContainerType.objects.filter(name__in=container_type_names)
        
        for cont_num in range(1, num_containers + 1):
            # Select a container type (weighted towards larger containers)
            container_type = random.choice(list(container_types))
            
            container_name = f"{hall.name} Container {cont_num}"
            # Set volume based on container type max
            max_vol = float(container_type.max_volume_m3)
            volume = Decimal(str(random.uniform(max_vol * 0.5, max_vol * 0.9)))
            container, created = Container.objects.get_or_create(
                name=container_name,
                defaults={
                    'container_type': container_type,
                    'hall': hall,
                    'volume_m3': volume,
                    'max_biomass_kg': Decimal(str(volume * 10)),  # ~10kg per m³
                    'feed_recommendations_enabled': True,
                    'active': True
                }
            )
            
            if created:
                self.created_objects['containers'].append(container)
    
    def _create_sea_sites(self):
        """Create sea sites with pen configurations."""
        logger.info("Creating sea sites...")
        
        if self.dry_run:
            logger.info("Would create sea sites")
            return
        
        # Get container types for sea cages
        sea_cage_types = ContainerType.objects.filter(name__in=['Sea Cage Small', 'Sea Cage Standard', 'Sea Cage Large'])
        
        # Get areas for sea sites
        all_areas = Area.objects.all()
        
        sea_site_configs = [
            # Major sites with many pens
            {'area': 'Streymoy', 'name': 'Streymoy North', 'pens': 12, 'type': 'Sea Cage Standard'},
            {'area': 'Streymoy', 'name': 'Streymoy South', 'pens': 10, 'type': 'Sea Cage Standard'},
            {'area': 'Eysturoy', 'name': 'Eysturoy East', 'pens': 8, 'type': 'Sea Cage Large'},
            {'area': 'Vágar', 'name': 'Vágar West', 'pens': 6, 'type': 'Sea Cage Standard'},
            {'area': 'Sandoy', 'name': 'Sandoy Bay', 'pens': 8, 'type': 'Sea Cage Standard'},
            {'area': 'Suðuroy', 'name': 'Suðuroy Fjord', 'pens': 10, 'type': 'Sea Cage Large'},
            # Scotland sites
            {'area': 'Shetland', 'name': 'Shetland North', 'pens': 8, 'type': 'Sea Cage Standard'},
            {'area': 'Orkney', 'name': 'Orkney Bay', 'pens': 6, 'type': 'Sea Cage Standard'},
            {'area': 'Western Isles', 'name': 'Lewis Site', 'pens': 10, 'type': 'Sea Cage Large'},
            {'area': 'Highland West', 'name': 'Skye Sound', 'pens': 8, 'type': 'Sea Cage Standard'}
        ]
        
        for config in sea_site_configs:
            area = all_areas.get(name=config['area'])
            container_type = sea_cage_types.get(name=config['type'])
            
            # Create containers (sea cages) directly for sea sites
            # Sea sites don't have stations or halls in our current model
            for pen_num in range(1, config['pens'] + 1):
                pen_name = f"{config['name']} Pen {pen_num}"
                # Set volume based on container type max
                max_vol = float(container_type.max_volume_m3)
                volume = Decimal(str(random.uniform(max_vol * 0.6, max_vol * 0.9)))
                
                container, created = Container.objects.get_or_create(
                    name=pen_name,
                    defaults={
                        'container_type': container_type,
                        'area': area,
                        'hall': None,  # Sea cages don't have halls
                        'volume_m3': volume,
                        'max_biomass_kg': Decimal(str(volume * 5)),  # ~5kg per m³ for sea cages
                        'feed_recommendations_enabled': True,
                        'active': True
                    }
                )
                
                if created:
                    self.created_objects['containers'].append(container)
        
        sea_cages = [c for c in self.created_objects['containers'] if c.area is not None]
        logger.info(f"Created sea sites with {len(sea_cages)} sea cages")
    
    def _create_sensors(self):
        """Create sensors and equipment for monitoring."""
        logger.info("Creating sensors and equipment...")
        
        if self.dry_run:
            logger.info("Would create sensors")
            return
        
        # Get all containers to add sensors to
        freshwater_containers = Container.objects.filter(hall__isnull=False)[:20]  # First 20 freshwater containers
        sea_containers = Container.objects.filter(area__isnull=False)[:20]  # First 20 sea containers
        
        # Create sensors for freshwater containers
        for container in freshwater_containers:
            # Freshwater containers get temperature, oxygen, pH sensors
            sensor_types = ['TEMPERATURE', 'OXYGEN', 'PH']
            
            for sensor_type in sensor_types:
                sensor_name = f"{container.name} {sensor_type.title().replace('_', ' ')} Sensor"
                
                sensor, created = Sensor.objects.get_or_create(
                    name=sensor_name,
                    container=container,
                    defaults={
                        'sensor_type': sensor_type,
                        'serial_number': f"SN{random.randint(100000, 999999)}",
                        'manufacturer': random.choice(['AquaSense', 'OceanTech', 'MarineMonitor']),
                        'installation_date': date.today() - timedelta(days=random.randint(30, 365)),
                        'last_calibration_date': date.today() - timedelta(days=random.randint(1, 30)),
                        'active': True
                    }
                )
                
                if created:
                    self.created_objects['sensors'].append(sensor)
        
        # Create sensors for sea containers
        for container in sea_containers:
            # Sea containers get temperature, oxygen, pH, salinity sensors
            sensor_types = ['TEMPERATURE', 'OXYGEN', 'PH', 'SALINITY']
            
            for sensor_type in sensor_types:
                sensor_name = f"{container.name} {sensor_type.title().replace('_', ' ')} Sensor"
                
                sensor, created = Sensor.objects.get_or_create(
                    name=sensor_name,
                    container=container,
                    defaults={
                        'sensor_type': sensor_type,
                        'serial_number': f"SN{random.randint(100000, 999999)}",
                        'manufacturer': random.choice(['AquaSense', 'OceanTech', 'MarineMonitor']),
                        'installation_date': date.today() - timedelta(days=random.randint(30, 365)),
                        'last_calibration_date': date.today() - timedelta(days=random.randint(1, 30)),
                        'active': True
                    }
                )
                
                if created:
                    self.created_objects['sensors'].append(sensor)
        
        logger.info(f"Created {len(self.created_objects['sensors'])} sensors")
    
    def get_summary(self) -> str:
        """
        Get a summary of all created infrastructure.
        
        Returns:
            String summary of created objects
        """
        summary = "\n=== Infrastructure Generation Summary ===\n"
        summary += f"Geographies: {len(self.created_objects['geographies'])}\n"
        summary += f"Areas: {len(self.created_objects['areas'])}\n"
        summary += f"Freshwater Stations: {len(self.created_objects['stations'])}\n"
        summary += f"Halls: {len(self.created_objects['halls'])}\n"
        summary += f"Containers: {len(self.created_objects['containers'])}\n"
        summary += f"  - Freshwater: {len([c for c in self.created_objects['containers'] if c.hall is not None])}\n"
        summary += f"  - Sea Cages: {len([c for c in self.created_objects['containers'] if c.hall is None])}\n"
        summary += f"Sensors: {len(self.created_objects['sensors'])}\n"
        
        return summary
