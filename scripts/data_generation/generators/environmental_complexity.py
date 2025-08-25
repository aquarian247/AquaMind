"""
Environmental Complexity Generator for AquaMind Data Generation

Implements advanced environmental scenarios including:
- Extreme weather events (storms, heat waves, cold snaps)
- Algae blooms with oxygen depletion
- Temperature anomalies and fluctuations
- Environmental stress events affecting fish health
"""

import logging
import random
import math
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.environmental.models import EnvironmentalReading
from apps.infrastructure.models import Container
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class EnvironmentalComplexityGenerator:
    """
    Generates complex environmental scenarios that affect fish health and growth:
    - Extreme weather events with cascading effects
    - Algae blooms causing oxygen depletion
    - Temperature anomalies and stress events
    - Environmental monitoring alerts
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize the environmental complexity generator.

        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run

        # Get or create system user
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='env_monitor',
                defaults={
                    'email': 'environment@aquamind.com',
                    'first_name': 'Environment',
                    'last_name': 'Monitor',
                    'is_staff': False,
                    'is_active': True
                }
            )

        # Active environmental events
        self.active_events = {}  # container_id -> event_info

    def generate_daily_environmental_events(self, current_date: date) -> Dict[str, int]:
        """
        Generate daily environmental complexity events.

        Args:
            current_date: Current date for event generation

        Returns:
            Dictionary with counts of events generated
        """
        if self.dry_run:
            logger.info("Would generate daily environmental events")
            return {'extreme_weather': 0, 'algae_blooms': 0, 'temp_anomalies': 0}

        events_count = {
            'extreme_weather': 0,
            'algae_blooms': 0,
            'temp_anomalies': 0,
            'oxygen_events': 0,
            'alerts_generated': 0
        }

        with transaction.atomic():
            # Get active containers for environmental event generation
            active_containers = Container.objects.filter(active=True)

            for container in active_containers:
                # Check for extreme weather events
                if self._should_generate_extreme_weather(current_date, container):
                    self._generate_extreme_weather_event(container, current_date)
                    events_count['extreme_weather'] += 1

                # Check for algae blooms
                if self._should_generate_algae_bloom(current_date, container):
                    self._generate_algae_bloom_event(container, current_date)
                    events_count['algae_blooms'] += 1

                # Check for temperature anomalies
                if self._should_generate_temperature_anomaly(current_date, container):
                    self._generate_temperature_anomaly(container, current_date)
                    events_count['temp_anomalies'] += 1

                # Check for oxygen depletion events
                if self._should_generate_oxygen_event(current_date, container):
                    self._generate_oxygen_event(container, current_date)
                    events_count['oxygen_events'] += 1

            # Process ongoing events
            self._process_ongoing_events(current_date)

            logger.info(f"Daily environmental events completed: {events_count}")
            return events_count

    def _should_generate_extreme_weather(self, current_date: date, container: Container) -> bool:
        """Determine if extreme weather should occur for a container."""
        # Higher probability in certain seasons
        month = current_date.month
        base_probability = 0.02  # 2% daily probability

        # Seasonal modifiers
        seasonal_multipliers = {
            1: 1.5,   # January - winter storms
            2: 1.3,   # February
            3: 0.8,   # March
            4: 0.7,   # April
            5: 0.6,   # May
            6: 1.0,   # June - summer storms
            7: 1.2,   # July
            8: 1.4,   # August
            9: 1.3,   # September
            10: 1.1,  # October - autumn gales
            11: 1.4,  # November
            12: 1.6   # December
        }

        adjusted_probability = base_probability * seasonal_multipliers.get(month, 1.0)

        # Container type modifiers (sea cages more affected by weather)
        if 'sea_cage' in container.container_type.name.lower():
            adjusted_probability *= 2.0

        return random.random() < adjusted_probability

    def _generate_extreme_weather_event(self, container: Container, event_date: date):
        """Generate an extreme weather event affecting a container."""
        try:
            # Determine weather type
            weather_types = {
                'storm': {'wind_speed': (20, 40), 'wave_height': (2, 6), 'duration_hours': (6, 24)},
                'heat_wave': {'temp_increase': (3, 8), 'duration_days': (3, 10)},
                'cold_snap': {'temp_decrease': (3, 8), 'duration_days': (2, 7)},
                'fog_event': {'visibility_reduction': (50, 90), 'duration_hours': (12, 72)},
                'rain_storm': {'freshwater_input': (5, 20), 'duration_hours': (3, 12)}
            }

            weather_type = random.choice(list(weather_types.keys()))
            weather_params = weather_types[weather_type]

            # Calculate event duration
            if 'duration_days' in weather_params:
                duration = random.randint(weather_params['duration_days'][0], weather_params['duration_days'][1])
                end_date = event_date + timedelta(days=duration)
            else:
                duration_hours = random.randint(weather_params['duration_hours'][0], weather_params['duration_hours'][1])
                end_date = event_date + timedelta(hours=duration_hours)

            # Store event info
            event_info = {
                'event_type': 'extreme_weather',
                'weather_type': weather_type,
                'container_id': container.id,
                'start_date': event_date,
                'end_date': end_date,
                'parameters': weather_params,
                'impact_level': random.choice(['LOW', 'MEDIUM', 'HIGH'])
            }

            self.active_events[container.id] = event_info

            logger.info(f"Generated {weather_type} event for container {container.name}")

        except Exception as e:
            logger.error(f"Error generating extreme weather event: {e}")

    def _should_generate_algae_bloom(self, current_date: date, container: Container) -> bool:
        """Determine if algae bloom should occur."""
        # Algae blooms more common in summer months and in sea cages
        month = current_date.month
        base_probability = 0.01  # 1% daily probability

        # Summer months have higher probability
        if month in [6, 7, 8, 9]:
            base_probability *= 3.0
        elif month in [5, 10]:
            base_probability *= 1.5

        # Sea cages more susceptible
        if 'sea_cage' in container.container_type.name.lower():
            base_probability *= 2.0

        return random.random() < base_probability

    def _generate_algae_bloom_event(self, container: Container, event_date: date):
        """Generate an algae bloom event."""
        try:
            bloom_types = ['diatom', 'dinoflagellate', 'cyanobacteria', 'mixed']
            bloom_type = random.choice(bloom_types)

            # Calculate bloom duration (typically 7-21 days)
            duration = random.randint(7, 21)
            end_date = event_date + timedelta(days=duration)

            # Algae bloom parameters
            bloom_params = {
                'bloom_type': bloom_type,
                'peak_biomass': random.uniform(10, 100),  # mg/L chlorophyll-a
                'oxygen_depletion_rate': random.uniform(0.5, 2.0),  # mg/L per day
                'toxin_production': random.choice([True, False]),
                'fish_stress_level': random.choice(['LOW', 'MEDIUM', 'HIGH'])
            }

            event_info = {
                'event_type': 'algae_bloom',
                'container_id': container.id,
                'start_date': event_date,
                'end_date': end_date,
                'parameters': bloom_params,
                'impact_level': 'HIGH' if bloom_params['fish_stress_level'] == 'HIGH' else 'MEDIUM'
            }

            self.active_events[container.id] = event_info

            logger.info(f"Generated {bloom_type} algae bloom for container {container.name}")

        except Exception as e:
            logger.error(f"Error generating algae bloom: {e}")

    def _should_generate_temperature_anomaly(self, current_date: date, container: Container) -> bool:
        """Determine if temperature anomaly should occur."""
        base_probability = 0.015  # 1.5% daily probability

        # Higher probability in transitional seasons
        month = current_date.month
        if month in [3, 4, 10, 11]:  # Spring and autumn
            base_probability *= 2.0

        return random.random() < base_probability

    def _generate_temperature_anomaly(self, container: Container, event_date: date):
        """Generate a temperature anomaly event."""
        try:
            # Determine if heating or cooling anomaly
            anomaly_type = random.choice(['heat', 'cold'])
            magnitude = random.uniform(2, 6)  # 2-6°C deviation

            # Duration based on anomaly type
            if anomaly_type == 'heat':
                duration = random.randint(1, 5)  # Heat waves shorter
            else:
                duration = random.randint(2, 10)  # Cold snaps longer

            end_date = event_date + timedelta(days=duration)

            anomaly_params = {
                'anomaly_type': anomaly_type,
                'magnitude_celsius': magnitude,
                'rate_of_change': random.uniform(0.5, 2.0),  # °C per day
                'stress_threshold': random.uniform(1.5, 3.0)  # °C from optimal
            }

            event_info = {
                'event_type': 'temperature_anomaly',
                'container_id': container.id,
                'start_date': event_date,
                'end_date': end_date,
                'parameters': anomaly_params,
                'impact_level': 'HIGH' if magnitude > 4 else 'MEDIUM'
            }

            self.active_events[container.id] = event_info

            logger.info(f"Generated {anomaly_type} anomaly ({magnitude}°C) for container {container.name}")

        except Exception as e:
            logger.error(f"Error generating temperature anomaly: {e}")

    def _should_generate_oxygen_event(self, current_date: date, container: Container) -> bool:
        """Determine if oxygen depletion event should occur."""
        base_probability = 0.008  # 0.8% daily probability

        # Higher probability in summer (higher temperatures, algae blooms)
        month = current_date.month
        if month in [7, 8, 9]:
            base_probability *= 2.0

        return random.random() < base_probability

    def _generate_oxygen_event(self, container: Container, event_date: date):
        """Generate an oxygen depletion event."""
        try:
            depletion_types = ['gradual', 'rapid', 'cascading']
            depletion_type = random.choice(depletion_types)

            # Duration depends on depletion type
            duration_map = {
                'gradual': (3, 7),
                'rapid': (1, 3),
                'cascading': (1, 5)
            }

            duration_range = duration_map[depletion_type]
            duration = random.randint(duration_range[0], duration_range[1])
            end_date = event_date + timedelta(days=duration)

            oxygen_params = {
                'depletion_type': depletion_type,
                'min_oxygen_mgl': random.uniform(2.0, 4.0),
                'recovery_rate': random.uniform(0.5, 2.0),  # mg/L per day
                'trigger_factor': random.choice(['temperature', 'algae', 'respiration', 'equipment'])
            }

            event_info = {
                'event_type': 'oxygen_depletion',
                'container_id': container.id,
                'start_date': event_date,
                'end_date': end_date,
                'parameters': oxygen_params,
                'impact_level': 'HIGH' if oxygen_params['min_oxygen_mgl'] < 3.0 else 'MEDIUM'
            }

            self.active_events[container.id] = event_info

            logger.info(f"Generated {depletion_type} oxygen event for container {container.name}")

        except Exception as e:
            logger.error(f"Error generating oxygen event: {e}")

    def _process_ongoing_events(self, current_date: date):
        """Process ongoing environmental events and their effects."""
        try:
            # Get environmental readings for the day
            daily_readings = EnvironmentalReading.objects.filter(
                reading_time__date=current_date,
                container__active=True
            ).select_related('container', 'parameter')

            for reading in daily_readings:
                container = reading.container
                event = self.active_events.get(container.id)

                if event and event['start_date'] <= current_date <= event['end_date']:
                    # Apply event effects to the reading
                    self._apply_event_effects(reading, event, current_date)

            # Clean up expired events
            expired_events = [
                container_id for container_id, event in self.active_events.items()
                if current_date > event['end_date']
            ]

            for container_id in expired_events:
                del self.active_events[container_id]
                logger.debug(f"Environmental event expired for container {container_id}")

        except Exception as e:
            logger.error(f"Error processing ongoing events: {e}")

    def _apply_event_effects(self, reading: EnvironmentalReading, event: Dict, current_date: date):
        """Apply environmental event effects to readings."""
        try:
            if event['event_type'] == 'extreme_weather':
                self._apply_weather_effects(reading, event)
            elif event['event_type'] == 'algae_bloom':
                self._apply_bloom_effects(reading, event)
            elif event['event_type'] == 'temperature_anomaly':
                self._apply_temperature_effects(reading, event)
            elif event['event_type'] == 'oxygen_depletion':
                self._apply_oxygen_effects(reading, event)

        except Exception as e:
            logger.error(f"Error applying event effects: {e}")

    def _apply_weather_effects(self, reading: EnvironmentalReading, event: Dict):
        """Apply extreme weather effects to environmental readings."""
        weather_type = event.get('weather_type')
        if not weather_type:
            logger.error(f"Missing weather_type in event: {event}")
            return
        param_name = reading.parameter.name

        if weather_type == 'storm':
            # Increase wave action, affect oxygen levels
            if param_name == 'Dissolved Oxygen':
                reading.value = max(4.0, float(reading.value) * 0.8)
            reading.notes = (reading.notes or "") + " | Storm conditions affecting oxygen levels"

        elif weather_type == 'heat_wave':
            # Increase temperature significantly
            temp_increase = random.uniform(2, 5)
            if param_name == 'Temperature':
                reading.value = min(25.0, float(reading.value) + temp_increase)
            elif param_name == 'Dissolved Oxygen':
                reading.value = max(4.0, float(reading.value) - temp_increase * 0.3)
            reading.notes = (reading.notes or "") + f" | Heat wave: +{temp_increase:.1f}°C"

        elif weather_type == 'cold_snap':
            # Decrease temperature significantly
            temp_decrease = random.uniform(2, 5)
            if param_name == 'Temperature':
                reading.value = max(2.0, float(reading.value) - temp_decrease)
            reading.notes = (reading.notes or "") + f" | Cold snap: -{temp_decrease:.1f}°C"

        elif weather_type == 'fog_event':
            # Reduce light, may affect algae
            reading.notes = (reading.notes or "") + " | Fog event reducing light penetration"

        elif weather_type == 'rain_storm':
            # Dilution effects for seawater sites
            if param_name == 'Salinity':
                salinity_decrease = random.uniform(1, 3)
                reading.value = max(20.0, float(reading.value) - salinity_decrease)
                reading.notes = (reading.notes or "") + f" | Rain storm: salinity -{salinity_decrease:.1f}ppt"

        reading.save()

    def _apply_bloom_effects(self, reading: EnvironmentalReading, event: Dict):
        """Apply algae bloom effects to environmental readings."""
        bloom_params = event.get('parameters', {})
        if not bloom_params:
            logger.error(f"Missing parameters in bloom event: {event}")
            return
        param_name = reading.parameter.name

        # Reduce oxygen due to algae respiration
        if param_name == 'Dissolved Oxygen':
            oxygen_reduction = bloom_params['oxygen_depletion_rate'] * random.uniform(0.8, 1.2)
            reading.value = max(2.0, float(reading.value) - oxygen_reduction)

        # May affect pH
        elif param_name == 'pH' and bloom_params['bloom_type'] == 'cyanobacteria':
            ph_change = random.uniform(-0.3, 0.1)
            reading.value = max(6.0, min(9.0, float(reading.value) + ph_change))

        # Add bloom indicators to all readings
        reading.notes = (reading.notes or "") + f" | {bloom_params['bloom_type']} bloom active"
        if bloom_params['toxin_production']:
            reading.notes += " | Potential toxin production"

        reading.save()

    def _apply_temperature_effects(self, reading: EnvironmentalReading, event: Dict):
        """Apply temperature anomaly effects to readings."""
        anomaly_params = event.get('parameters', {})
        if not anomaly_params:
            logger.error(f"Missing parameters in temperature event: {event}")
            return
        anomaly_type = anomaly_params['anomaly_type']
        param_name = reading.parameter.name

        if anomaly_type == 'heat':
            # Apply heating effect to temperature readings
            if param_name == 'Temperature':
                temp_change = min(anomaly_params['magnitude_celsius'],
                                anomaly_params['rate_of_change'] * random.uniform(0.8, 1.2))
                reading.value = min(25.0, float(reading.value) + temp_change)

            # Oxygen decreases with temperature
            elif param_name == 'Dissolved Oxygen':
                temp_change = min(anomaly_params['magnitude_celsius'],
                                anomaly_params['rate_of_change'] * random.uniform(0.8, 1.2))
                oxygen_change = temp_change * 0.25
                reading.value = max(4.0, float(reading.value) - oxygen_change)

        else:  # cold
            if param_name == 'Temperature':
                temp_change = min(anomaly_params['magnitude_celsius'],
                                anomaly_params['rate_of_change'] * random.uniform(0.8, 1.2))
                reading.value = max(2.0, float(reading.value) - temp_change)

        reading.notes = (reading.notes or "") + f" | Temperature anomaly: {anomaly_type} event"
        reading.save()

    def _apply_oxygen_effects(self, reading: EnvironmentalReading, event: Dict):
        """Apply oxygen depletion effects to readings."""
        oxygen_params = event.get('parameters', {})
        if not oxygen_params:
            logger.error(f"Missing parameters in oxygen event: {event}")
            return
        param_name = reading.parameter.name

        # Only apply effects to oxygen readings
        if param_name != 'Dissolved Oxygen':
            return

        # Apply oxygen depletion based on type
        if oxygen_params['depletion_type'] == 'rapid':
            depletion_rate = random.uniform(2.0, 4.0)
        elif oxygen_params['depletion_type'] == 'cascading':
            depletion_rate = random.uniform(1.5, 3.0)
        else:  # gradual
            depletion_rate = random.uniform(0.5, 1.5)

        reading.value = max(oxygen_params['min_oxygen_mgl'],
                           float(reading.value) - depletion_rate)

        reading.notes = (reading.notes or "") + f" | Oxygen depletion: {oxygen_params['depletion_type']}"
        reading.save()

    def get_environmental_stress_level(self, container: Container, current_date: date) -> str:
        """Get the current environmental stress level for a container."""
        event = self.active_events.get(container.id)

        if not event:
            return 'LOW'

        if event['impact_level'] == 'HIGH':
            return 'HIGH'
        elif event['impact_level'] == 'MEDIUM':
            return 'MEDIUM'
        else:
            return 'LOW'

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for environmental complexity."""
        return {
            'active_events_count': len(self.active_events),
            'event_types': list(set(event['event_type'] for event in self.active_events.values())),
            'high_impact_events': len([e for e in self.active_events.values() if e['impact_level'] == 'HIGH'])
        }
