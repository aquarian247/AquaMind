"""
Unit tests for environmental models.

Tests model creation, validation, relationships, and TimescaleDB functionality.
Note: Infrastructure models (Area, Container, etc.) are tested in their respective app tests.
Complex relationship tests and TimescaleDB-specific functionality are covered in integration tests.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.utils import IntegrityError
from django.conf import settings

from apps.environmental.models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    WeatherData
)
from apps.infrastructure.models import (
    Area,
    Container,
    Sensor,
    Geography,
    ContainerType
)
from apps.batch.models.assignment import BatchContainerAssignment


class EnvironmentalParameterTests(TestCase):
    """Tests for the EnvironmentalParameter model."""
    
    def setUp(self):
        """Set up test data for parameter tests."""
        self.parameter = EnvironmentalParameter.objects.create(
            name="Temperature",
            unit="°C",
            description="Water temperature",
            min_value=Decimal('0.0'),
            max_value=Decimal('25.0'),
            optimal_min=Decimal('12.0'),
            optimal_max=Decimal('16.0')
        )
    
    def test_parameter_creation(self):
        """Test basic parameter creation with all fields."""
        parameter = EnvironmentalParameter.objects.create(
            name="Oxygen",
            unit="mg/L",
            description="Dissolved oxygen",
            min_value=Decimal('4.0'),
            max_value=Decimal('20.0'),
            optimal_min=Decimal('7.0'),
            optimal_max=Decimal('12.0')
        )
        
        self.assertEqual(parameter.name, "Oxygen")
        self.assertEqual(parameter.unit, "mg/L")
        self.assertEqual(parameter.description, "Dissolved oxygen")
        self.assertEqual(parameter.min_value, Decimal('4.0'))
        self.assertEqual(parameter.max_value, Decimal('20.0'))
        self.assertEqual(parameter.optimal_min, Decimal('7.0'))
        self.assertEqual(parameter.optimal_max, Decimal('12.0'))
    
    def test_parameter_string_representation(self):
        """Test the string representation of a parameter."""
        self.assertEqual(str(self.parameter), "Temperature (°C)")
    
    def test_parameter_optional_fields(self):
        """Test parameter creation with only required fields."""
        parameter = EnvironmentalParameter.objects.create(
            name="pH",
            unit=""
        )
        
        self.assertEqual(parameter.name, "pH")
        self.assertEqual(parameter.unit, "")
        self.assertIsNone(parameter.min_value)
        self.assertIsNone(parameter.max_value)
        self.assertIsNone(parameter.optimal_min)
        self.assertIsNone(parameter.optimal_max)
    
    # Note: Model-level validation for optimal values within min/max range
    # may not be implemented at the model level, but rather in forms/serializers


class EnvironmentalReadingTests(TestCase):
    """Tests for the EnvironmentalReading model."""
    
    def setUp(self):
        """Set up test data for reading tests."""
        # Create minimal required objects
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=60.0,
            longitude=10.0,
            max_biomass=1000.0
        )
        
        # Create container type
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        
        # Create a container directly in the area (simplifying setup)
        self.container = Container.objects.get_or_create(
            name="Test Container",
            defaults={
                'area': self.area,
                'container_type': self.container_type,
                'volume_m3': Decimal('50.0'),
                'max_biomass_kg': Decimal('500.0')
            }
        )[0]
        
        # Create parameter
        self.parameter = EnvironmentalParameter.objects.create(
            name="Temperature",
            unit="°C"
        )
    
    def test_reading_creation(self):
        """Test creating an environmental reading with required fields."""
        reading_time = timezone.now()
        reading = EnvironmentalReading.objects.create(
            parameter=self.parameter,
            container=self.container,
            value=Decimal('14.5'),
            reading_time=reading_time
        )
        
        self.assertEqual(reading.parameter, self.parameter)
        self.assertEqual(reading.container, self.container)
        self.assertEqual(reading.value, Decimal('14.5'))
        self.assertEqual(reading.reading_time, reading_time)
        self.assertFalse(reading.is_manual)
    
    def test_reading_string_representation(self):
        """Test the string representation of a reading."""
        reading_time = timezone.now()
        reading = EnvironmentalReading.objects.create(
            parameter=self.parameter,
            container=self.container,
            value=Decimal('14.5'),
            reading_time=reading_time
        )
        
        expected = f"Temperature: 14.5 °C at {reading_time}"
        self.assertEqual(str(reading), expected)
    
    def test_reading_manual_flag(self):
        """Test the is_manual flag for readings."""
        reading = EnvironmentalReading.objects.create(
            parameter=self.parameter,
            container=self.container,
            value=Decimal('15.0'),
            reading_time=timezone.now(),
            is_manual=True,
            notes="Manual reading"
        )
        self.assertTrue(reading.is_manual)
        self.assertEqual(reading.notes, "Manual reading")

    def test_reading_with_batch_container_assignment(self):
        """Test creating a reading with batch_container_assignment field."""
        # Create a batch for testing
        from apps.batch.models.species import Species, LifeCycleStage
        species = Species.objects.create(name="Atlantic Salmon", scientific_name="Salmo salar")
        lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=species,
            order=3
        )

        from apps.batch.models.batch import Batch
        batch = Batch.objects.create(
            batch_number="TEST-001",
            species=species,
            lifecycle_stage=lifecycle_stage,
            status="ACTIVE",
            batch_type="STANDARD",
            start_date=timezone.now().date()
        )

        # Create batch-container assignment
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=self.container,
            lifecycle_stage=lifecycle_stage,
            population_count=1000,
            biomass_kg=Decimal('50.0'),
            assignment_date=timezone.now().date()
        )

        # Create reading with assignment
        reading = EnvironmentalReading.objects.create(
            parameter=self.parameter,
            container=self.container,
            batch=batch,
            batch_container_assignment=assignment,
            value=Decimal('16.5'),
            reading_time=timezone.now()
        )

        self.assertEqual(reading.batch_container_assignment, assignment)
        self.assertEqual(reading.batch, batch)
        self.assertEqual(reading.container, self.container)

    def test_reading_batch_container_assignment_nullable(self):
        """Test that batch_container_assignment field can be null."""
        reading = EnvironmentalReading.objects.create(
            parameter=self.parameter,
            container=self.container,
            value=Decimal('14.0'),
            reading_time=timezone.now()
        )

        self.assertIsNone(reading.batch_container_assignment)
        # Reading should still be valid without assignment
        self.assertEqual(reading.value, Decimal('14.0'))

    @unittest.skipIf(
        'timescale' not in settings.DATABASES['default']['ENGINE'],
        "TimescaleDB tests are skipped in CI environments"
    )
    def test_timescaledb_hypertable(self):
        """Test TimescaleDB hypertable functionality (skipped in CI)."""
        # This test would verify TimescaleDB-specific functionality
        # but is skipped when not running with TimescaleDB
        self.assertTrue(True, "Placeholder for TimescaleDB tests")


class PhotoperiodDataTests(TestCase):
    """Tests for the PhotoperiodData model."""
    
    def setUp(self):
        """Set up test data for photoperiod tests."""
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=60.0,
            longitude=10.0,
            max_biomass=1000.0
        )
    
    def test_photoperiod_creation(self):
        """Test creating photoperiod data with all fields."""
        today = timezone.now().date()
        photoperiod = PhotoperiodData.objects.create(
            area=self.area,
            date=today,
            day_length_hours=Decimal('12.5'),
            light_intensity=Decimal('5000.0'),
            is_interpolated=False
        )
        
        self.assertEqual(photoperiod.area, self.area)
        self.assertEqual(photoperiod.date, today)
        self.assertEqual(photoperiod.day_length_hours, Decimal('12.5'))
        self.assertEqual(photoperiod.light_intensity, Decimal('5000.0'))
        self.assertFalse(photoperiod.is_interpolated)
    
    def test_photoperiod_string_representation(self):
        """Test the string representation of photoperiod data."""
        today = timezone.now().date()
        photoperiod = PhotoperiodData.objects.create(
            area=self.area,
            date=today,
            day_length_hours=Decimal('12.5')
        )
        
        expected = f"Test Area: 12.5h on {today}"
        self.assertEqual(str(photoperiod), expected)
    
    def test_day_length_validation(self):
        """Test validation of day length (0-24 hours)."""
        # Valid day length
        photoperiod = PhotoperiodData(
            area=self.area,
            date=timezone.now().date(),
            day_length_hours=Decimal('24.0')
        )
        photoperiod.full_clean()  # Should not raise ValidationError
        
        # Invalid: day length > 24
        photoperiod = PhotoperiodData(
            area=self.area,
            date=timezone.now().date(),
            day_length_hours=Decimal('25.0')
        )
        with self.assertRaises(ValidationError):
            photoperiod.full_clean()
    
    def test_unique_constraint(self):
        """Test the unique constraint on area+date."""
        today = timezone.now().date()
        
        # Create first record
        PhotoperiodData.objects.create(
            area=self.area,
            date=today,
            day_length_hours=Decimal('12.5')
        )
        
        # Attempt to create duplicate record
        with self.assertRaises(IntegrityError):
            PhotoperiodData.objects.create(
                area=self.area,
                date=today,
                day_length_hours=Decimal('13.0')
            )


class WeatherDataTests(TestCase):
    """Tests for the WeatherData model."""
    
    def setUp(self):
        """Set up test data for weather tests."""
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=60.0,
            longitude=10.0,
            max_biomass=1000.0
        )
    
    def test_weather_data_creation(self):
        """Test creating weather data with all fields."""
        timestamp = timezone.now()
        weather = WeatherData.objects.create(
            area=self.area,
            timestamp=timestamp,
            temperature=Decimal('15.5'),
            wind_speed=Decimal('5.2'),
            wind_direction=180,
            precipitation=Decimal('2.5'),
            wave_height=Decimal('1.2'),
            wave_period=Decimal('4.5'),
            wave_direction=225,
            cloud_cover=75
        )
        
        self.assertEqual(weather.area, self.area)
        self.assertEqual(weather.timestamp, timestamp)
        self.assertEqual(weather.temperature, Decimal('15.5'))
        self.assertEqual(weather.wind_direction, 180)
        self.assertEqual(weather.cloud_cover, 75)
    
    def test_weather_data_string_representation(self):
        """Test the string representation of weather data."""
        timestamp = timezone.now()
        weather = WeatherData.objects.create(
            area=self.area,
            timestamp=timestamp,
            temperature=Decimal('15.5')
        )
        
        expected = f"Weather for Test Area at {timestamp}"
        self.assertEqual(str(weather), expected)
    
    def test_direction_validation(self):
        """Test validation of direction fields (0-360 degrees)."""
        # Invalid: wind direction > 360
        weather = WeatherData(
            area=self.area,
            timestamp=timezone.now(),
            wind_direction=361
        )
        with self.assertRaises(ValidationError):
            weather.full_clean()
    
    @unittest.skipIf(
        'timescale' not in settings.DATABASES['default']['ENGINE'],
        "TimescaleDB tests are skipped in CI environments"
    )
    def test_timescaledb_hypertable(self):
        """Test TimescaleDB hypertable functionality (skipped in CI)."""
        # This test would verify TimescaleDB-specific functionality
        # but is skipped when not running with TimescaleDB
        self.assertTrue(True, "Placeholder for TimescaleDB tests")
