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

    def test_geography_historical_records_creation(self):
        """Test that Geography creates proper historical records on creation."""
        geography = Geography.objects.create(
            name="Historical Test Geography",
            description="Test for historical records"
        )
        historical_records = Geography.history.model.objects.filter(id=geography.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_geography_historical_records_update(self):
        """Test that Geography creates proper historical records on update."""
        geography = Geography.objects.create(
            name="Historical Test Geography",
            description="Test for historical records"
        )
        # Update the geography
        geography.description = "Updated description"
        geography.save()

        historical_records = Geography.history.model.objects.filter(id=geography.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_geography_historical_records_delete(self):
        """Test that Geography creates proper historical records on deletion."""
        geography = Geography.objects.create(
            name="Historical Test Geography",
            description="Test for historical records"
        )
        geography_id = geography.id
        geography.delete()

        historical_records = Geography.history.model.objects.filter(id=geography_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


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

    def test_area_historical_records_creation(self):
        """Test that Area creates proper historical records on creation."""
        area = Area.objects.create(
            name="Historical Test Area",
            geography=self.geography,
            latitude=15.123456,
            longitude=25.123456,
            max_biomass=2000.00
        )
        historical_records = Area.history.model.objects.filter(id=area.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_area_historical_records_update(self):
        """Test that Area creates proper historical records on update."""
        area = Area.objects.create(
            name="Historical Test Area",
            geography=self.geography,
            latitude=15.123456,
            longitude=25.123456,
            max_biomass=2000.00
        )
        # Update the area
        area.max_biomass = 3000.00
        area.save()

        historical_records = Area.history.model.objects.filter(id=area.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_area_historical_records_delete(self):
        """Test that Area creates proper historical records on deletion."""
        area = Area.objects.create(
            name="Historical Test Area",
            geography=self.geography,
            latitude=15.123456,
            longitude=25.123456,
            max_biomass=2000.00
        )
        area_id = area.id
        area.delete()

        historical_records = Area.history.model.objects.filter(id=area_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


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

    def test_station_historical_records_creation(self):
        """Test that FreshwaterStation creates proper historical records on creation."""
        station = FreshwaterStation.objects.create(
            name="Historical Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=20.123456,
            longitude=30.123456,
            description="Historical test station"
        )
        historical_records = FreshwaterStation.history.model.objects.filter(id=station.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_station_historical_records_update(self):
        """Test that FreshwaterStation creates proper historical records on update."""
        station = FreshwaterStation.objects.create(
            name="Historical Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=20.123456,
            longitude=30.123456,
            description="Historical test station"
        )
        # Update the station
        station.description = "Updated description"
        station.save()

        historical_records = FreshwaterStation.history.model.objects.filter(id=station.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_station_historical_records_delete(self):
        """Test that FreshwaterStation creates proper historical records on deletion."""
        station = FreshwaterStation.objects.create(
            name="Historical Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=20.123456,
            longitude=30.123456,
            description="Historical test station"
        )
        station_id = station.id
        station.delete()

        historical_records = FreshwaterStation.history.model.objects.filter(id=station_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


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

    def test_sensor_historical_records_creation(self):
        """Test that Sensor creates proper historical records on creation."""
        sensor = Sensor.objects.create(
            name="Historical Test Sensor",
            sensor_type="OXYGEN",
            container=self.container,
            serial_number="HIST123",
            manufacturer="Historical Corp"
        )
        historical_records = Sensor.history.model.objects.filter(id=sensor.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_sensor_historical_records_update(self):
        """Test that Sensor creates proper historical records on update."""
        sensor = Sensor.objects.create(
            name="Historical Test Sensor",
            sensor_type="OXYGEN",
            container=self.container,
            serial_number="HIST123",
            manufacturer="Historical Corp"
        )
        # Update the sensor
        sensor.manufacturer = "Updated Corp"
        sensor.save()

        historical_records = Sensor.history.model.objects.filter(id=sensor.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_sensor_historical_records_delete(self):
        """Test that Sensor creates proper historical records on deletion."""
        sensor = Sensor.objects.create(
            name="Historical Test Sensor",
            sensor_type="OXYGEN",
            container=self.container,
            serial_number="HIST123",
            manufacturer="Historical Corp"
        )
        sensor_id = sensor.id
        sensor.delete()

        historical_records = Sensor.history.model.objects.filter(id=sensor_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


class HallModelTest(TestCase):
    """Test the Hall model."""

    def setUp(self):
        self.geography = Geography.objects.create(name="Test Geography")
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456
        )
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station,
            description="Test hall description",
            area_sqm=100.50
        )

    def test_hall_creation(self):
        """Test that a Hall instance can be created."""
        self.assertEqual(self.hall.name, "Test Hall")
        self.assertEqual(self.hall.freshwater_station, self.station)
        self.assertEqual(self.hall.description, "Test hall description")
        self.assertEqual(self.hall.area_sqm, Decimal('100.50'))
        self.assertTrue(self.hall.active)

    def test_hall_str(self):
        """Test the string representation of a Hall instance."""
        self.assertEqual(str(self.hall), "Test Hall (in Test Station)")

    def test_hall_historical_records_creation(self):
        """Test that Hall creates proper historical records on creation."""
        hall = Hall.objects.create(
            name="Historical Test Hall",
            freshwater_station=self.station,
            description="Historical test hall",
            area_sqm=200.50
        )
        historical_records = Hall.history.model.objects.filter(id=hall.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_hall_historical_records_update(self):
        """Test that Hall creates proper historical records on update."""
        hall = Hall.objects.create(
            name="Historical Test Hall",
            freshwater_station=self.station,
            description="Historical test hall",
            area_sqm=200.50
        )
        # Update the hall
        hall.area_sqm = 250.75
        hall.save()

        historical_records = Hall.history.model.objects.filter(id=hall.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_hall_historical_records_delete(self):
        """Test that Hall creates proper historical records on deletion."""
        hall = Hall.objects.create(
            name="Historical Test Hall",
            freshwater_station=self.station,
            description="Historical test hall",
            area_sqm=200.50
        )
        hall_id = hall.id
        hall.delete()

        historical_records = Hall.history.model.objects.filter(id=hall_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


class ContainerTypeModelTest(TestCase):
    """Test the ContainerType model."""

    def setUp(self):
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.00,
            description="Test container type description"
        )

    def test_container_type_creation(self):
        """Test that a ContainerType instance can be created."""
        self.assertEqual(self.container_type.name, "Test Tank")
        self.assertEqual(self.container_type.category, "TANK")
        self.assertEqual(self.container_type.max_volume_m3, Decimal('100.00'))
        self.assertEqual(self.container_type.description, "Test container type description")

    def test_container_type_str(self):
        """Test the string representation of a ContainerType instance."""
        self.assertEqual(str(self.container_type), "Test Tank (Tank)")

    def test_container_type_historical_records_creation(self):
        """Test that ContainerType creates proper historical records on creation."""
        container_type = ContainerType.objects.create(
            name="Historical Test Tank",
            category="TANK",
            max_volume_m3=150.00,
            description="Historical test container type"
        )
        historical_records = ContainerType.history.model.objects.filter(id=container_type.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_container_type_historical_records_update(self):
        """Test that ContainerType creates proper historical records on update."""
        container_type = ContainerType.objects.create(
            name="Historical Test Tank",
            category="TANK",
            max_volume_m3=150.00,
            description="Historical test container type"
        )
        # Update the container type
        container_type.max_volume_m3 = 200.00
        container_type.save()

        historical_records = ContainerType.history.model.objects.filter(id=container_type.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_container_type_historical_records_delete(self):
        """Test that ContainerType creates proper historical records on deletion."""
        container_type = ContainerType.objects.create(
            name="Historical Test Tank",
            category="TANK",
            max_volume_m3=150.00,
            description="Historical test container type"
        )
        container_type_id = container_type.id
        container_type.delete()

        historical_records = ContainerType.history.model.objects.filter(id=container_type_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record


class FeedContainerModelTest(TestCase):
    """Test the FeedContainer model."""

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

        # Create feed containers in different locations
        self.area_feed_container = FeedContainer.objects.create(
            name="Area Feed Container",
            container_type="SILO",
            area=self.area,
            capacity_kg=5000.00,
            active=True
        )

        self.hall_feed_container = FeedContainer.objects.create(
            name="Hall Feed Container",
            container_type="BARGE",
            hall=self.hall,
            capacity_kg=10000.00,
            active=True
        )

    def test_feed_container_creation(self):
        """Test that FeedContainer instances can be created in different locations."""
        # Test area feed container
        self.assertEqual(self.area_feed_container.name, "Area Feed Container")
        self.assertEqual(self.area_feed_container.container_type, "SILO")
        self.assertEqual(self.area_feed_container.area, self.area)
        self.assertIsNone(self.area_feed_container.hall)
        self.assertEqual(self.area_feed_container.capacity_kg, Decimal('5000.00'))

        # Test hall feed container
        self.assertEqual(self.hall_feed_container.name, "Hall Feed Container")
        self.assertEqual(self.hall_feed_container.container_type, "BARGE")
        self.assertEqual(self.hall_feed_container.hall, self.hall)
        self.assertIsNone(self.hall_feed_container.area)

    def test_feed_container_validation(self):
        """Test that a FeedContainer cannot be linked to both a hall and an area."""
        invalid_feed_container = FeedContainer(
            name="Invalid Feed Container",
            container_type="TANK",
            hall=self.hall,
            area=self.area,
            capacity_kg=3000.00
        )

        with self.assertRaises(ValidationError):
            invalid_feed_container.clean()

    def test_feed_container_str(self):
        """Test the string representation of a FeedContainer instance."""
        self.assertEqual(str(self.area_feed_container), "Area Feed Container (Silo at Test Area)")
        self.assertEqual(str(self.hall_feed_container), "Hall Feed Container (Barge at Test Hall)")

    def test_feed_container_historical_records_creation(self):
        """Test that FeedContainer creates proper historical records on creation."""
        feed_container = FeedContainer.objects.create(
            name="Historical Test Feed Container",
            container_type="SILO",
            area=self.area,
            capacity_kg=3000.00
        )
        historical_records = FeedContainer.history.model.objects.filter(id=feed_container.id)
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Create record

    def test_feed_container_historical_records_update(self):
        """Test that FeedContainer creates proper historical records on update."""
        feed_container = FeedContainer.objects.create(
            name="Historical Test Feed Container",
            container_type="SILO",
            area=self.area,
            capacity_kg=3000.00
        )
        # Update the feed container
        feed_container.capacity_kg = 4000.00
        feed_container.save()

        historical_records = FeedContainer.history.model.objects.filter(id=feed_container.id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '~')  # Update record

    def test_feed_container_historical_records_delete(self):
        """Test that FeedContainer creates proper historical records on deletion."""
        feed_container = FeedContainer.objects.create(
            name="Historical Test Feed Container",
            container_type="SILO",
            area=self.area,
            capacity_kg=3000.00
        )
        feed_container_id = feed_container.id
        feed_container.delete()

        historical_records = FeedContainer.history.model.objects.filter(id=feed_container_id).order_by('history_date')
        self.assertEqual(historical_records.count(), 2)
        self.assertEqual(historical_records[0].history_type, '+')  # Create record
        self.assertEqual(historical_records[1].history_type, '-')  # Delete record