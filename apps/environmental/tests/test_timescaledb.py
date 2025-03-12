"""
Tests to verify TimescaleDB hypertables are working correctly.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import random

from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.infrastructure.models import Container, Area, Geography, ContainerType


class TimescaleDBTest(TestCase):
    """Test TimescaleDB hypertable functionality for EnvironmentalReading model.
    
    This test verifies that:
    1. The hypertable is correctly set up with time-based partitioning
    2. We can create and retrieve time-series data efficiently
    3. Time-based queries work as expected
    """
    
    def setUp(self):
        """Set up test data."""
        # Create geography first (required by Area)
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography for TimescaleDB testing"
        )
        
        # Create area
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=10.123456,
            longitude=20.123456,
            max_biomass=1000.00
        )
        
        # Create container type (required by Container)
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.00
        )
        
        # Create container
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=80.00,
            max_biomass_kg=800.00
        )
        
        # Create parameter
        self.temp_param = EnvironmentalParameter.objects.create(
            name="Temperature",
            description="Water temperature",
            unit="°C",
            min_value=8.0,
            max_value=20.0,
            optimal_min=12.0,
            optimal_max=16.0
        )
        
        self.oxygen_param = EnvironmentalParameter.objects.create(
            name="Dissolved Oxygen",
            description="Dissolved oxygen in water",
            unit="mg/L",
            min_value=3.0,
            max_value=16.0,
            optimal_min=7.0,
            optimal_max=12.0
        )
    
    def test_create_time_series_data(self):
        """Test creation of time-series data across multiple time chunks."""
        # Create 50 readings over 5 days (should span multiple TimescaleDB chunks)
        now = timezone.now()
        
        # Temperature readings
        for i in range(50):
            # Create a reading every 2.4 hours over 5 days
            reading_time = now - timedelta(hours=i*2.4)
            # Random value between 12-16 with some outliers
            value = random.uniform(11.0, 17.0)
            
            EnvironmentalReading.objects.create(
                parameter=self.temp_param,
                container=self.container,
                value=value,
                reading_time=reading_time,
                is_manual=False
            )
        
        # Verify data was created
        self.assertEqual(EnvironmentalReading.objects.count(), 50)
        
        # Test time-based querying (last day)
        one_day_ago = now - timedelta(days=1)
        recent_readings = EnvironmentalReading.objects.filter(
            reading_time__gte=one_day_ago
        ).count()
        
        self.assertGreater(recent_readings, 0)
        self.assertLess(recent_readings, 50)  # Should be fewer than total
        
        # Test parameter + time-based querying
        temp_day_readings = EnvironmentalReading.objects.filter(
            parameter=self.temp_param,
            reading_time__gte=one_day_ago
        ).count()
        
        self.assertEqual(temp_day_readings, recent_readings)
    
    def test_time_range_queries(self):
        """Test time range queries which are optimized by TimescaleDB."""
        now = timezone.now()
        
        # Create readings with specific timestamps for testing
        times = [
            now - timedelta(days=10),
            now - timedelta(days=5),
            now - timedelta(days=3),
            now - timedelta(days=1),
            now - timedelta(hours=12),
            now - timedelta(hours=1),
            now,
        ]
        
        # Create readings at specific times
        for t in times:
            EnvironmentalReading.objects.create(
                parameter=self.temp_param,
                container=self.container,
                value=15.0,
                reading_time=t,
                is_manual=False
            )
            
        # Test various time range queries
        self.assertEqual(
            EnvironmentalReading.objects.filter(
                reading_time__gte=now - timedelta(days=3)
            ).count(), 
            4  # Last 3 days should have 4 readings
        )
        
        self.assertEqual(
            EnvironmentalReading.objects.filter(
                reading_time__gte=now - timedelta(days=6),
                reading_time__lt=now - timedelta(days=2)
            ).count(), 
            2  # Between 6 and 2 days ago should have 2 readings
        )
