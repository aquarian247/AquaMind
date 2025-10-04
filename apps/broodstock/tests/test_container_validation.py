"""
Tests for broodstock container validation.

Tests that BroodstockFishSerializer properly validates containers
using category checks instead of fragile name substring matching.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from decimal import Decimal

from apps.broodstock.models import BroodstockFish
from apps.broodstock.serializers import BroodstockFishSerializer
from apps.infrastructure.models import (
    Geography, FreshwaterStation, Hall, 
    ContainerType, Container
)


class BroodstockContainerValidationTest(TestCase):
    """Test container validation for broodstock fish."""
    
    def setUp(self):
        """Set up test infrastructure."""
        # Create infrastructure
        self.geography = Geography.objects.create(name='Test Region')
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            geography=self.geography,
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060')
        )
        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station
        )
        
        # Create various container types with different categories
        self.tank_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=Decimal('100.0')
        )
        
        self.pen_type = ContainerType.objects.create(
            name='Sea Pen',
            category='PEN',
            max_volume_m3=Decimal('1000.0')
        )
        
        self.tray_type = ContainerType.objects.create(
            name='Egg Tray',
            category='TRAY',
            max_volume_m3=Decimal('1.0')
        )
        
        self.other_type = ContainerType.objects.create(
            name='Other Container',
            category='OTHER',
            max_volume_m3=Decimal('50.0')
        )
        
        # Create containers of each type
        self.tank_container = Container.objects.create(
            name='Tank Container',
            container_type=self.tank_type,
            hall=self.hall,
            volume_m3=Decimal('50.0'),
            max_biomass_kg=Decimal('500.0')
        )
        
        self.pen_container = Container.objects.create(
            name='Pen Container',
            container_type=self.pen_type,
            hall=self.hall,
            volume_m3=Decimal('500.0'),
            max_biomass_kg=Decimal('5000.0')
        )
        
        self.tray_container = Container.objects.create(
            name='Tray Container',
            container_type=self.tray_type,
            hall=self.hall,
            volume_m3=Decimal('0.5'),
            max_biomass_kg=Decimal('10.0')
        )
        
        self.other_container = Container.objects.create(
            name='Other Container',
            container_type=self.other_type,
            hall=self.hall,
            volume_m3=Decimal('25.0'),
            max_biomass_kg=Decimal('250.0')
        )
    
    def test_tank_container_accepted(self):
        """Test that TANK category containers are accepted."""
        data = {
            'container': self.tank_container.id,
            'health_status': 'healthy',
            'traits': {'growth_rate': 'high'}
        }
        
        serializer = BroodstockFishSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        fish = serializer.save()
        
        self.assertEqual(fish.container, self.tank_container)
        self.assertEqual(fish.health_status, 'healthy')
    
    def test_pen_container_rejected(self):
        """Test that PEN category containers are rejected."""
        data = {
            'container': self.pen_container.id,
            'health_status': 'healthy'
        }
        
        serializer = BroodstockFishSerializer(data=data)
        
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        
        self.assertIn('container', context.exception.detail)
        error_message = str(context.exception.detail['container'][0])
        self.assertIn('tank', error_message.lower())
        self.assertIn('Pen', error_message)
    
    def test_tray_container_rejected(self):
        """Test that TRAY category containers are rejected."""
        data = {
            'container': self.tray_container.id,
            'health_status': 'healthy'
        }
        
        serializer = BroodstockFishSerializer(data=data)
        
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        
        self.assertIn('container', context.exception.detail)
        error_message = str(context.exception.detail['container'][0])
        self.assertIn('tank', error_message.lower())
        self.assertIn('Tray', error_message)
    
    def test_other_container_rejected(self):
        """Test that OTHER category containers are rejected."""
        data = {
            'container': self.other_container.id,
            'health_status': 'healthy'
        }
        
        serializer = BroodstockFishSerializer(data=data)
        
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        
        self.assertIn('container', context.exception.detail)
        error_message = str(context.exception.detail['container'][0])
        self.assertIn('tank', error_message.lower())
        self.assertIn('Other', error_message)
    
    def test_various_tank_names_accepted(self):
        """Test that tanks with various names are accepted (not relying on name)."""
        # Create tanks with names that DON'T contain 'broodstock'
        tank_names = [
            'Fish Tank A',
            'Container 123',
            'Production Tank',
            'Tank without keyword',
            'TANK_01'
        ]
        
        for tank_name in tank_names:
            container_type = ContainerType.objects.create(
                name=tank_name,
                category='TANK',
                max_volume_m3=Decimal('100.0')
            )
            
            container = Container.objects.create(
                name=tank_name,
                container_type=container_type,
                hall=self.hall,
                volume_m3=Decimal('50.0'),
                max_biomass_kg=Decimal('500.0')
            )
            
            data = {
                'container': container.id,
                'health_status': 'healthy'
            }
            
            serializer = BroodstockFishSerializer(data=data)
            self.assertTrue(
                serializer.is_valid(),
                f"Tank '{tank_name}' should be valid but validation failed: {serializer.errors}"
            )
            
            fish = serializer.save()
            self.assertEqual(fish.container, container)
    
    def test_update_to_invalid_container_rejected(self):
        """Test that updating a fish to an invalid container is rejected."""
        # Create fish in valid tank container
        fish = BroodstockFish.objects.create(
            container=self.tank_container,
            health_status='healthy'
        )
        
        # Try to update to pen container
        data = {
            'container': self.pen_container.id
        }
        
        serializer = BroodstockFishSerializer(fish, data=data, partial=True)
        
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        
        self.assertIn('container', context.exception.detail)
        
        # Verify fish container unchanged
        fish.refresh_from_db()
        self.assertEqual(fish.container, self.tank_container)
    
    def test_error_message_includes_category_display(self):
        """Test that error messages include human-readable category names."""
        test_cases = [
            (self.pen_container, 'Pen'),
            (self.tray_container, 'Tray'),
            (self.other_container, 'Other'),
        ]
        
        for container, expected_category in test_cases:
            data = {
                'container': container.id,
                'health_status': 'healthy'
            }
            
            serializer = BroodstockFishSerializer(data=data)
            
            with self.assertRaises(ValidationError) as context:
                serializer.is_valid(raise_exception=True)
            
            error_message = str(context.exception.detail['container'][0])
            self.assertIn(expected_category, error_message,
                         f"Error message should include category '{expected_category}': {error_message}")

