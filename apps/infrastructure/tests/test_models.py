from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from decimal import Decimal

from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType, 
    Container,
    Sensor,
    FeedContainer
)


class GeographyModelTest(TestCase):
    """Test the Geography model."""
    
    def setUp(self):
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography description"
        )
    
    def test_geography_creation(self):
        """Test that a Geography instance can be created."""
        self.assertEqual(self.geography.name, "Test Geography")
        self.assertEqual(self.geography.description, "Test geography description")
    
    def test_geography_str(self):
        """Test the string representation of a Geography instance."""
        self.assertEqual(str(self.geography), "Test Geography")
    
    def test_geography_unique_name(self):
        """Test that Geography names must be unique."""
        with self.assertRaises(IntegrityError):
            Geography.objects.create(name="Test Geography")


class AreaModelTest(TestCase):
    """Test the Area model."""
    
    def setUp(self):
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456,
            max_biomass=1000.00
        )
    
    def test_area_creation(self):
        """Test that an Area instance can be created."""
        self.assertEqual(self.area.name, "Test Area")
        self.assertEqual(self.area.geography, self.geography)
        # Use assertAlmostEqual for floating point comparisons
        self.assertAlmostEqual(float(self.area.latitude), 10.123456)
        self.assertAlmostEqual(float(self.area.longitude), 20.123456)
        self.assertAlmostEqual(float(self.area.max_biomass), 1000.00)
        self.assertTrue(self.area.active)
    
    def test_area_str(self):
        """Test the string representation of an Area instance."""
        self.assertEqual(str(self.area), f"Test Area (Test Geography)")
    
    def test_area_latitude_validation(self):
        """Test that latitude is validated."""
        # Create the object first, then validate it to trigger the validator
        invalid_area = Area(
            name="Invalid Area",
            geography=self.geography,
            latitude=100,  # Invalid: > 90
            longitude=20,
            max_biomass=1000
        )
        
        # Django validators are called during full_clean(), not during save()
        with self.assertRaises(ValidationError):
            invalid_area.full_clean()


class FreshwaterStationModelTest(TestCase):
    """Test the FreshwaterStation model."""
    
    def setUp(self):
        self.geography = Geography.objects.create(name="Test Geography")
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456,
            description="Test description"
        )
    
    def test_station_creation(self):
        """Test that a FreshwaterStation instance can be created."""
        self.assertEqual(self.station.name, "Test Station")
        self.assertEqual(self.station.station_type, "FRESHWATER")
        self.assertEqual(self.station.geography, self.geography)
        self.assertEqual(self.station.description, "Test description")
        self.assertTrue(self.station.active)
    
    def test_station_str(self):
        """Test the string representation of a FreshwaterStation instance."""
        self.assertEqual(str(self.station), "Test Station (Freshwater)")


class ContainerModelTest(TestCase):
    """Test the Container model."""
    
    def setUp(self):
        # Create prerequisites
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456,
            max_biomass=1000.00
        )
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456
        )
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station
        )
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.00
        )
        
        # Create containers in different locations
        self.area_container = Container.objects.create(
            name="Area Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=80.00,
            max_biomass_kg=800.00
        )
        
        self.hall_container = Container.objects.create(
            name="Hall Container",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.00,
            max_biomass_kg=500.00
        )
    
    def test_container_creation(self):
        """Test that Container instances can be created in different locations."""
        # Test area container
        self.assertEqual(self.area_container.name, "Area Container")
        self.assertEqual(self.area_container.container_type, self.container_type)
        self.assertEqual(self.area_container.area, self.area)
        self.assertIsNone(self.area_container.hall)
        self.assertEqual(self.area_container.volume_m3, Decimal('80.00'))
        
        # Test hall container
        self.assertEqual(self.hall_container.name, "Hall Container")
        self.assertEqual(self.hall_container.container_type, self.container_type)
        self.assertEqual(self.hall_container.hall, self.hall)
        self.assertIsNone(self.hall_container.area)
    
    def test_container_validation(self):
        """Test that a Container cannot be in both a hall and an area."""
        invalid_container = Container(
            name="Invalid Container",
            container_type=self.container_type,
            hall=self.hall,
            area=self.area,
            volume_m3=60.00,
            max_biomass_kg=600.00
        )
        
        with self.assertRaises(ValidationError):
            invalid_container.full_clean()
    
    def test_volume_validation(self):
        """Test that volume cannot exceed container type maximum."""
        invalid_container = Container(
            name="Volume Exceeded",
            container_type=self.container_type,  # max 100.00
            area=self.area,
            volume_m3=120.00,  # > 100.00
            max_biomass_kg=600.00
        )
        
        with self.assertRaises(ValidationError):
            invalid_container.full_clean()


class SensorModelTest(TestCase):
    """Test the Sensor model."""
    
    def setUp(self):
        # Create prerequisites
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456,
            max_biomass=1000.00
        )
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.00
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=80.00,
            max_biomass_kg=800.00
        )
        
        # Create sensor
        self.sensor = Sensor.objects.create(
            name="Test Sensor",
            sensor_type="TEMPERATURE",
            container=self.container,
            serial_number="SN12345",
            manufacturer="SensorCorp"
        )
    
    def test_sensor_creation(self):
        """Test that a Sensor instance can be created."""
        self.assertEqual(self.sensor.name, "Test Sensor")
        self.assertEqual(self.sensor.sensor_type, "TEMPERATURE")
        self.assertEqual(self.sensor.container, self.container)
        self.assertEqual(self.sensor.serial_number, "SN12345")
        self.assertEqual(self.sensor.manufacturer, "SensorCorp")
        self.assertTrue(self.sensor.active)
    
    def test_sensor_str(self):
        """Test the string representation of a Sensor instance."""
        self.assertEqual(str(self.sensor), "Test Sensor (Temperature in Test Container)")