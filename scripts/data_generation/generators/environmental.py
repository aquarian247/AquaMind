"""
Environmental Generator for AquaMind Data Generation

Handles creation of environmental data with seasonal patterns and correlations.
"""

import logging
import random
import math
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.environmental.models import (
    EnvironmentalParameter, EnvironmentalReading
)
from apps.infrastructure.models import Sensor, Container, FreshwaterStation
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class EnvironmentalGenerator:
    """
    Generates environmental data including:
    - Seasonal temperature patterns
    - Oxygen level variations (inversely correlated with temperature)
    - pH measurements
    - Salinity for sea sites
    - Daily variations with persistence
    - TimescaleDB hypertable storage
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the environmental generator.
        
        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run
        self.created_readings = 0
        self.batch_buffer = []
        self.batch_size = 1000  # Bulk insert size
        
        # Previous day's data for persistence
        self.previous_data = {}
        
        # Get or create system user
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='data_generator',
                defaults={
                    'email': 'generator@aquamind.com',
                    'first_name': 'Data',
                    'last_name': 'Generator',
                    'is_staff': False,
                    'active': True
                }
            )
            
            # Ensure environmental parameters exist
            self._ensure_parameters()
    
    def _ensure_parameters(self):
        """Ensure all environmental parameters are defined in the database."""
        
        parameters = [
            {
                'name': 'Temperature',
                'code': 'TEMP',
                'unit': '°C',
                'min_value': Decimal('-2'),
                'max_value': Decimal('30'),
                'description': 'Water temperature'
            },
            {
                'name': 'Dissolved Oxygen',
                'code': 'DO',
                'unit': 'mg/L',
                'min_value': Decimal('0'),
                'max_value': Decimal('20'),
                'description': 'Dissolved oxygen concentration'
            },
            {
                'name': 'pH',
                'code': 'PH',
                'unit': 'pH',
                'min_value': Decimal('4'),
                'max_value': Decimal('10'),
                'description': 'Water pH level'
            },
            {
                'name': 'Salinity',
                'code': 'SAL',
                'unit': 'ppt',
                'min_value': Decimal('0'),
                'max_value': Decimal('40'),
                'description': 'Water salinity'
            },
            {
                'name': 'Turbidity',
                'code': 'TURB',
                'unit': 'NTU',
                'min_value': Decimal('0'),
                'max_value': Decimal('100'),
                'description': 'Water turbidity'
            },
            {
                'name': 'Ammonia',
                'code': 'NH3',
                'unit': 'mg/L',
                'min_value': Decimal('0'),
                'max_value': Decimal('5'),
                'description': 'Ammonia concentration'
            }
        ]
        
        for param_data in parameters:
            EnvironmentalParameter.objects.get_or_create(
                name=param_data['name'],
                defaults={
                    'unit': param_data['unit'],
                    'min_value': param_data['min_value'],
                    'max_value': param_data['max_value'],
                    'description': param_data['description']
                }
            )
    
    def generate_baseline_data(self, start_date: date, end_date: date, 
                              readings_per_day: int = 8) -> Dict[str, int]:
        """
        Generate baseline environmental data for a date range.
        
        Args:
            start_date: Start date for generation
            end_date: End date for generation
            readings_per_day: Number of readings per day (default 8 = every 3 hours)
            
        Returns:
            Dictionary with generation statistics
        """
        logger.info(f"Generating environmental baseline from {start_date} to {end_date}")
        
        if self.dry_run:
            days = (end_date - start_date).days + 1
            total_readings = days * readings_per_day * 100  # Estimate ~100 sensors
            logger.info(f"Would generate approximately {total_readings:,} readings")
            return {'readings': 0, 'days': days}
        
        # Get all active sensors
        sensors = Sensor.objects.filter(active=True)
        logger.info(f"Found {sensors.count()} active sensors")
        
        # Process each day
        current_date = start_date
        days_processed = 0
        
        while current_date <= end_date:
            self._generate_daily_readings(current_date, sensors, readings_per_day)
            current_date += timedelta(days=1)
            days_processed += 1
            
            # Log progress every 30 days
            if days_processed % 30 == 0:
                logger.info(f"Processed {days_processed} days, {self.created_readings:,} readings created")
        
        # Flush any remaining buffered readings
        self._flush_buffer()
        
        logger.info(f"Generated {self.created_readings:,} environmental readings")
        
        return {
            'readings': self.created_readings,
            'days': days_processed
        }
    
    def _generate_daily_readings(self, reading_date: date, sensors, readings_per_day: int):
        """Generate readings for all sensors for a single day."""
        
        # Time intervals for readings (e.g., every 3 hours for 8 readings)
        hours_between = 24 // readings_per_day
        
        for hour_offset in range(0, 24, hours_between):
            reading_time = datetime.combine(reading_date, datetime.min.time())
            reading_time = reading_time.replace(hour=hour_offset)
            
            for sensor in sensors:
                reading_value = self._calculate_sensor_value(
                    sensor, reading_date, hour_offset
                )
                
                if reading_value is not None:
                    self._add_reading(sensor, reading_time, reading_value)
    
    def _calculate_sensor_value(self, sensor: Sensor, reading_date: date, 
                               hour: int) -> Optional[Decimal]:
        """
        Calculate sensor reading value based on type, location, and time.
        
        Args:
            sensor: The sensor object
            reading_date: Date of the reading
            hour: Hour of the day (0-23)
            
        Returns:
            Calculated sensor value or None
        """
        sensor_key = f"{sensor.id}_{sensor.sensor_type}"
        
        # Determine if freshwater or seawater based on container
        is_seawater = sensor.container.area is not None  # Sea containers have areas
        
        if sensor.sensor_type == 'temperature':
            return self._calculate_temperature(reading_date, hour, is_seawater, sensor_key)
        elif sensor.sensor_type == 'oxygen':
            # Get temperature for correlation
            temp = self._calculate_temperature(reading_date, hour, is_seawater, sensor_key)
            return self._calculate_oxygen(temp, is_seawater)
        elif sensor.sensor_type == 'ph':
            return self._calculate_ph(is_seawater)
        elif sensor.sensor_type == 'salinity':
            return self._calculate_salinity() if is_seawater else None
        elif sensor.sensor_type == 'turbidity':
            return self._calculate_turbidity(reading_date)
        else:
            return None
    
    def _calculate_temperature(self, reading_date: date, hour: int, 
                              is_seawater: bool, sensor_key: str) -> Decimal:
        """Calculate temperature with seasonal and daily variations."""
        
        # Base temperature ranges
        if is_seawater:
            base_min, base_max, optimal = 6, 18, 12
        else:
            base_min, base_max, optimal = 4, 16, 10
        
        # Seasonal variation (sinusoidal pattern)
        day_of_year = reading_date.timetuple().tm_yday
        seasonal_adjustment = 6 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        
        # Daily variation (warmer in afternoon)
        daily_adjustment = 2 * math.sin(2 * math.pi * (hour - 6) / 24)
        
        # Base temperature
        base_temp = optimal + seasonal_adjustment + daily_adjustment
        
        # Add persistence from previous reading
        if sensor_key in self.previous_data:
            prev_temp = self.previous_data[sensor_key].get('temperature', base_temp)
            # 70% persistence, 30% new value
            temperature = 0.7 * float(prev_temp) + 0.3 * base_temp
        else:
            temperature = base_temp
        
        # Add small random variation
        temperature += random.gauss(0, 0.5)
        
        # Clamp to realistic ranges
        temperature = max(base_min, min(base_max, temperature))
        
        # Store for next reading
        if sensor_key not in self.previous_data:
            self.previous_data[sensor_key] = {}
        self.previous_data[sensor_key]['temperature'] = temperature
        
        return Decimal(str(round(temperature, 1)))
    
    def _calculate_oxygen(self, temperature: Decimal, is_seawater: bool) -> Decimal:
        """Calculate dissolved oxygen (inversely correlated with temperature)."""
        
        # Base oxygen levels
        if is_seawater:
            base_oxygen = 9.0
        else:
            base_oxygen = 11.0
        
        # Temperature effect (inverse correlation)
        temp_effect = -0.3 * (float(temperature) - 10)
        
        # Calculate oxygen
        oxygen = base_oxygen + temp_effect + random.gauss(0, 0.5)
        
        # Clamp to realistic ranges
        oxygen = max(4, min(14, oxygen))
        
        return Decimal(str(round(oxygen, 1)))
    
    def _calculate_ph(self, is_seawater: bool) -> Decimal:
        """Calculate pH (relatively stable)."""
        
        if is_seawater:
            base_ph = 8.0
        else:
            base_ph = 7.2
        
        # Small variation
        ph = base_ph + random.gauss(0, 0.1)
        
        # Clamp to realistic ranges
        ph = max(6.5, min(8.5, ph))
        
        return Decimal(str(round(ph, 2)))
    
    def _calculate_salinity(self) -> Decimal:
        """Calculate salinity for seawater sites."""
        
        # Typical seawater salinity with small variation
        salinity = 34.5 + random.gauss(0, 0.5)
        
        # Clamp to realistic ranges
        salinity = max(32, min(36, salinity))
        
        return Decimal(str(round(salinity, 1)))
    
    def _calculate_turbidity(self, reading_date: date) -> Decimal:
        """Calculate turbidity (higher after storms/rain)."""
        
        # Base turbidity
        base_turbidity = 5.0
        
        # Random weather events (simplified)
        if random.random() < 0.1:  # 10% chance of high turbidity event
            turbidity = base_turbidity * random.uniform(3, 10)
        else:
            turbidity = base_turbidity + random.gauss(0, 2)
        
        # Clamp to realistic ranges
        turbidity = max(0, min(50, turbidity))
        
        return Decimal(str(round(turbidity, 1)))
    
    def _add_reading(self, sensor: Sensor, reading_time: datetime, value: Decimal):
        """Add a reading to the buffer for bulk insertion."""
        
        # Get parameter based on sensor type
        param_map = {
            'temperature': 'Temperature',
            'oxygen': 'Dissolved Oxygen',
            'ph': 'pH',
            'salinity': 'Salinity',
            'turbidity': 'Turbidity'
        }
        
        param_name = param_map.get(sensor.sensor_type)
        if not param_name:
            return
        
        try:
            parameter = EnvironmentalParameter.objects.get(name=param_name)
        except EnvironmentalParameter.DoesNotExist:
            logger.warning(f"Parameter {param_name} not found")
            return
        
        # Determine location type and ID
        # Sensors are always attached to containers
        location_type = 'container'
        location_id = sensor.container.id
        
        # Create reading object
        reading = EnvironmentalReading(
            parameter=parameter,
            sensor=sensor,
            location_type=location_type,
            location_id=location_id,
            value=value,
            timestamp=reading_time,
            created_by=self.system_user,
            updated_by=self.system_user
        )
        
        self.batch_buffer.append(reading)
        
        # Flush buffer if it reaches batch size
        if len(self.batch_buffer) >= self.batch_size:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush the buffer and bulk create readings."""
        
        if not self.batch_buffer:
            return
        
        if not self.dry_run:
            try:
                EnvironmentalReading.objects.bulk_create(
                    self.batch_buffer,
                    batch_size=self.batch_size
                )
                self.created_readings += len(self.batch_buffer)
            except Exception as e:
                logger.error(f"Error bulk creating readings: {e}")
        
        self.batch_buffer = []
    
    def generate_daily_updates(self, current_date: date) -> int:
        """
        Generate environmental readings for a single day (for daily operations).
        
        Args:
            current_date: Date to generate readings for
            
        Returns:
            Number of readings created
        """
        if self.dry_run:
            return 0
        
        # Get active sensors
        sensors = Sensor.objects.filter(active=True)
        
        # Generate 8 readings per day (every 3 hours)
        self._generate_daily_readings(current_date, sensors, 8)
        
        # Flush buffer
        self._flush_buffer()
        
        return self.created_readings
    
    def get_summary(self) -> str:
        """
        Get a summary of generated environmental data.
        
        Returns:
            String summary of created readings
        """
        summary = "\n=== Environmental Generation Summary ===\n"
        summary += f"Total Readings Created: {self.created_readings:,}\n"
        
        if not self.dry_run and self.created_readings > 0:
            # Get some statistics
            param_counts = {}
            for param in EnvironmentalParameter.objects.all():
                count = EnvironmentalReading.objects.filter(parameter=param).count()
                if count > 0:
                    param_counts[param.name] = count
            
            if param_counts:
                summary += "\nReadings by Parameter:\n"
                for param_name, count in param_counts.items():
                    summary += f"  {param_name}: {count:,}\n"
        
        return summary
