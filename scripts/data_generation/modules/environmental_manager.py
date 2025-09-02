"""
Environmental Manager Module

This module handles the generation of time-series environmental data for containers,
including temperature, oxygen, pH, and salinity readings.
"""
import random
import datetime
import math
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading, Sensor
from apps.batch.models import BatchContainerAssignment, LifeCycleStage
from apps.infrastructure.models import Container
from scripts.data_generation.config.generation_params import GenerationParameters


class EnvironmentalManager:
    """Manages environmental data generation for containers."""
    
    def __init__(self):
        """Initialize the environmental manager."""
        # Get or create environmental parameters
        self.parameters = self._ensure_parameters_exist()
        
        # Define parameter ranges by lifecycle stage
        self.parameter_ranges = {
            "Egg&Alevin": {
                "Temperature": (4.0, 10.0),         # 4-10°C
                "pH": (6.5, 7.5),                   # 6.5-7.5
                "Oxygen": (80.0, 110.0),            # 80-110% saturation
                "Salinity": (0.0, 0.5),             # 0-0.5 ppt (freshwater)
            },
            "Fry": {
                "Temperature": (6.0, 12.0),         # 6-12°C
                "pH": (6.5, 7.5),                   # 6.5-7.5
                "Oxygen": (80.0, 110.0),            # 80-110% saturation
                "Salinity": (0.0, 0.5),             # 0-0.5 ppt (freshwater)
            },
            "Parr": {
                "Temperature": (8.0, 12.0),         # 8-12°C
                "pH": (6.5, 8.0),                   # 6.5-8.0
                "Oxygen": (80.0, 110.0),            # 80-110% saturation
                "Salinity": (0.0, 0.5),             # 0-0.5 ppt (freshwater)
            },
            "Smolt": {
                "Temperature": (8.0, 14.0),         # 8-14°C
                "pH": (6.5, 8.0),                   # 6.5-8.0
                "Oxygen": (80.0, 110.0),            # 80-110% saturation
                "Salinity": (0.0, 0.5),             # 0-0.5 ppt (freshwater)
            },
            "Post-Smolt": {
                "Temperature": (6.0, 10.0),         # 6-10°C
                "pH": (7.5, 8.4),                   # 7.5-8.4
                "Oxygen": (75.0, 100.0),            # 75-100% saturation
                "Salinity": (15.0, 35.0),           # 15-35 ppt (transition to seawater)
            },
            "Adult": {
                "Temperature": (6.0, 10.0),         # 6-10°C
                "pH": (7.5, 8.4),                   # 7.5-8.4
                "Oxygen": (75.0, 100.0),            # 75-100% saturation
                "Salinity": (30.0, 35.0),           # 30-35 ppt (seawater)
            }
        }
        
        # Cache for container sensors
        self.container_sensors = {}
    
    def _ensure_parameters_exist(self):
        """Ensure that all required environmental parameters exist in the database."""
        parameters = {}
        
        # Define parameter specifications
        param_specs = [
            {
                "name": "Temperature",
                "unit": "°C",
                "description": "Water temperature in degrees Celsius",
                "min_value": 0,
                "max_value": 30,
                "optimal_min": 6,
                "optimal_max": 14
            },
            {
                "name": "Oxygen",
                "unit": "%",
                "description": "Dissolved oxygen as percentage of saturation",
                "min_value": 60,
                "max_value": 120,
                "optimal_min": 80,
                "optimal_max": 110
            },
            {
                "name": "pH",
                "unit": "",
                "description": "pH level of water",
                "min_value": 6.0,
                "max_value": 9.0,
                "optimal_min": 6.5,
                "optimal_max": 8.5
            },
            {
                "name": "Salinity",
                "unit": "ppt",
                "description": "Salinity in parts per thousand",
                "min_value": 0,
                "max_value": 40,
                "optimal_min": 0,
                "optimal_max": 35
            }
        ]
        
        # Create parameters if they don't exist
        for spec in param_specs:
            param, created = EnvironmentalParameter.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "unit": spec["unit"],
                    "description": spec["description"],
                    "min_value": spec["min_value"],
                    "max_value": spec["max_value"],
                    "optimal_min": spec["optimal_min"],
                    "optimal_max": spec["optimal_max"]
                }
            )
            parameters[spec["name"]] = param
            
            if created:
                print(f"Created environmental parameter: {param.name}")
        
        return parameters
    
    def _get_or_create_sensor(self, container_id, parameter_name):
        """
        Get or create a sensor for a container and parameter.
        
        Args:
            container_id: The ID of the container
            parameter_name: The name of the parameter
            
        Returns:
            The Sensor object
        """
        # Check if we already have this sensor in cache
        cache_key = f"{container_id}_{parameter_name}"
        if cache_key in self.container_sensors:
            return self.container_sensors[cache_key]
        
        # Map parameter name to Sensor.SENSOR_TYPES code
        PARAM_TO_SENSOR_TYPE = {
            "Temperature": "TEMPERATURE",
            "Oxygen": "OXYGEN",
            "pH": "PH",
            "Salinity": "SALINITY",
        }
        sensor_type = PARAM_TO_SENSOR_TYPE.get(parameter_name)
        if sensor_type is None:
            # Unsupported parameter – skip creating a sensor
            raise ValueError(f"Unsupported sensor type mapping for parameter '{parameter_name}'")
        
        # Try to get an existing sensor
        sensor = Sensor.objects.filter(
            container_id=container_id,
            sensor_type=sensor_type
        ).first()
        
        # Create a new sensor if none exists
        if not sensor:
            container = Container.objects.get(id=container_id)
            sensor = Sensor.objects.create(
                name=f"{parameter_name} Sensor - {container.name}",
                container_id=container_id,
                sensor_type=sensor_type,
                active=True,
                installation_date=timezone.now().date()
            )
            print(f"Created sensor: {sensor.name}")
        
        # Cache the sensor
        self.container_sensors[cache_key] = sensor
        return sensor
    
    @transaction.atomic
    def generate_readings(self, start_date, end_date=None, reading_count=8):
        """
        Generate environmental readings for all containers with batch assignments.
        
        Args:
            start_date: The date to start generating readings from
            end_date: The end date (defaults to today)
            reading_count: Number of readings per day (default: 8)
            
        Returns:
            Total number of readings generated
        """
        if end_date is None:
            end_date = timezone.now().date()
        
        # Get all active container assignments within the date range
        assignments = BatchContainerAssignment.objects.filter(
            assignment_date__lte=end_date,
            departure_date__isnull=True
        ).select_related('batch', 'container', 'batch__lifecycle_stage')
        
        # Also get assignments that ended within the date range
        ended_assignments = BatchContainerAssignment.objects.filter(
            assignment_date__lte=end_date,
            departure_date__gte=start_date
        ).select_related('batch', 'container', 'batch__lifecycle_stage')
        
        # Combine all relevant assignments
        all_assignments = list(assignments) + list(ended_assignments)
        
        # Group by container to avoid duplicate readings
        container_to_assignments = {}
        for assignment in all_assignments:
            if assignment.container_id not in container_to_assignments:
                container_to_assignments[assignment.container_id] = []
            container_to_assignments[assignment.container_id].append(assignment)
        
        # Process each day in the range
        current_date = start_date
        total_readings = 0
        
        readings_list = []
        batch_size = GenerationParameters.DB_BATCH_SIZE

        while current_date <= end_date:
            # Generate multiple readings per day at different hours
            hours = sorted(random.sample(range(6, 22), reading_count))
            
            for container_id, assignments in container_to_assignments.items():
                for hour in hours:
                    # Determine which assignment was active at this time
                    active_assignment = None
                    for assignment in assignments:
                        # Check if this assignment was active on this date
                        is_active = (
                            assignment.assignment_date <= current_date and
                            (assignment.departure_date is None or assignment.departure_date >= current_date)
                        )
                        if is_active:
                            active_assignment = assignment
                            break
                    
                    if active_assignment is None:
                        continue
                    
                    # Get the lifecycle stage for parameter ranges
                    stage = active_assignment.batch.lifecycle_stage.name
                    
                    # Generate readings for each parameter
                    reading_time = datetime.datetime.combine(
                        current_date, 
                        datetime.time(hour, random.randint(0, 59), random.randint(0, 59))
                    )
                    
                    # Create readings for each parameter
                    for param_name, parameter in self.parameters.items():
                        # Get appropriate range for this stage and parameter
                        param_range = self.parameter_ranges.get(stage, {}).get(param_name)
                        if not param_range:
                            continue
                            
                        # Generate a value within the range with some natural variation
                        min_val, max_val = param_range
                        value = round(random.uniform(min_val, max_val), 2)
                        
                        # Add some time series patterns
                        if param_name == "Temperature":
                            # Daily cycle with peak in afternoon
                            time_factor = 1.0 + 0.05 * float((hour - 6) % 16) / 16
                            value *= time_factor
                            
                            # Seasonal variation
                            day_of_year = current_date.timetuple().tm_yday
                            seasonal_factor = 1.0 + 0.1 * math.sin((day_of_year - 172) * 2 * math.pi / 365)
                            value *= seasonal_factor
                        
                        value = round(value, 2)
                        
                        # Get or create a sensor for this container and parameter
                        sensor = self._get_or_create_sensor(container_id, param_name)
                            
                        # Create the reading with direct assignment linkage for salmon CV tracking
                        reading = EnvironmentalReading(
                            parameter=parameter,
                            container_id=container_id,
                            batch=active_assignment.batch,
                            batch_container_assignment=active_assignment,  # Direct linkage to assignment
                            sensor=sensor,
                            value=value,
                            reading_time=reading_time.replace(tzinfo=timezone.utc),
                            is_manual=False
                        )
                        readings_list.append(reading)
                        total_readings += 1

                    if len(readings_list) >= batch_size:
                        EnvironmentalReading.objects.bulk_create(readings_list)
                        readings_list = []
                        print(f"Flushed {batch_size} readings")
            
            # Move to next day
            current_date += datetime.timedelta(days=1)
        
        if readings_list:
            EnvironmentalReading.objects.bulk_create(readings_list)
            print(f"Flushed final {len(readings_list)} readings")

        print(f"Generated {total_readings:,} environmental readings from {start_date} to {end_date}")
        return total_readings
            
    def get_parameters_for_stage(self, stage_name):
        """Get the parameter ranges for a specific lifecycle stage."""
        return self.parameter_ranges.get(stage_name, {})
