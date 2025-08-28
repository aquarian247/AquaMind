"""
Tests for the infrastructure overview API endpoint.

This module tests the functionality of the infrastructure overview endpoint,
which provides aggregated metrics about the infrastructure.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from rest_framework.authtoken.models import Token
import json
from decimal import Decimal
from datetime import timedelta

from apps.infrastructure.models.container import Container
from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.geography import Geography
from apps.infrastructure.models.area import Area
from apps.batch.models.batch import Batch
from apps.batch.models.species import Species, LifeCycleStage
from apps.batch.models.assignment import BatchContainerAssignment
from apps.inventory.models.feeding import FeedingEvent
from apps.inventory.models.feed import Feed


class InfrastructureOverviewAPITestCase(TestCase):
    """Test case for the infrastructure overview API endpoint."""

    def setUp(self):
        """Set up test data and authentication."""
        # Clear cache to ensure tests start fresh
        cache.clear()
        
        # Create a test user and token for authentication
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            email="test@example.com"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = Client()
        
        # Create container type for test data
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.0
        )
        # ------------------------------------------------------------------
        # Geography / Area required for Container.clean() validation
        # ------------------------------------------------------------------
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography for unit tests"
        )
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=Decimal('10.0'),
            longitude=Decimal('20.0'),
            max_biomass=Decimal('10000.0')
        )
        
        # Create species and lifecycle stage for batch
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        
        # Create feed for feeding events
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        
        # URL for the overview endpoint
        # Use the explicit path instead of reverse() because the endpoint
        # is registered via a standalone `path()` rather than a view-set router
        # and may not be present in the URL resolver under the given name in
        # the test configuration used by `settings_ci`.
        self.url = "/api/v1/infrastructure/overview/"
    
    def test_authentication_required(self):
        """Test that authentication is required for the endpoint."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
    
    def test_empty_database_response(self):
        """Test response structure with an empty database."""
        # Authenticate the request
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.token.key}'
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('total_containers', data)
        self.assertIn('capacity_kg', data)
        self.assertIn('active_biomass_kg', data)
        self.assertIn('sensor_alerts', data)
        self.assertIn('feeding_events_today', data)
        
        # With empty database, all values should be zero
        self.assertEqual(data['total_containers'], 0)
        self.assertEqual(data['capacity_kg'], 0)
        self.assertEqual(data['active_biomass_kg'], 0)
        self.assertEqual(data['sensor_alerts'], 0)
        self.assertEqual(data['feeding_events_today'], 0)
    
    def test_with_sample_data(self):
        """Test response with sample data in the database."""
        # Authenticate the request
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.token.key}'
        
        # Create test containers
        container1 = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('80.0'),
            max_biomass_kg=Decimal('1000.0')
        )
        
        container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('90.0'),
            max_biomass_kg=Decimal('1500.0')
        )
        
        # Create test batch
        batch = Batch.objects.create(
            batch_number="B12345",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create batch container assignment
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=container1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal('250.0'),
            biomass_kg=Decimal('250.0'),
            assignment_date=timezone.now().date(),
            is_active=True
        )
        
        # Create feeding event for today
        feeding_event = FeedingEvent.objects.create(
            batch=batch,
            container=container1,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal('10.0'),
            batch_biomass_kg=Decimal('250.0'),
            method="MANUAL"
        )
        
        # Get the overview data
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Check that the data matches our test data
        self.assertEqual(data['total_containers'], 2)
        self.assertEqual(data['capacity_kg'], 2500.0)  # 1000 + 1500
        self.assertEqual(data['active_biomass_kg'], 250.0)
        self.assertEqual(data['feeding_events_today'], 1)
    
    def test_caching_behavior(self):
        """Test that responses are cached and cache is used."""
        # Authenticate the request
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.token.key}'
        
        # Create a container
        container = Container.objects.create(
            name="Cache Test Tank",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('100.0'),
            max_biomass_kg=Decimal('2000.0')
        )
        
        # First request should hit the database
        response1 = self.client.get(self.url)
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertEqual(data1['total_containers'], 1)
        
        # Create another container - this shouldn't be reflected in the cached response
        container2 = Container.objects.create(
            name="Cache Test Tank 2",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('100.0'),
            max_biomass_kg=Decimal('2000.0')
        )
        
        # Second request should use cache and not see the new container
        response2 = self.client.get(self.url)
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertEqual(data2['total_containers'], 1)  # Still 1 from cache
        
        # Clear cache
        cache.clear()
        
        # Third request should hit the database again and see both containers
        response3 = self.client.get(self.url)
        self.assertEqual(response3.status_code, 200)
        data3 = json.loads(response3.content)
        self.assertEqual(data3['total_containers'], 2)  # Now 2 after cache clear
    
    def test_feeding_events_today_filter(self):
        """Test that feeding events are correctly filtered for today only."""
        # Authenticate the request
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.token.key}'
        
        # Create test container and batch
        container = Container.objects.create(
            name="Feeding Test Tank",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('100.0'),
            max_biomass_kg=Decimal('2000.0')
        )
        
        batch = Batch.objects.create(
            batch_number="F12345",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create feeding event for today
        today_event = FeedingEvent.objects.create(
            batch=batch,
            container=container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal('10.0'),
            batch_biomass_kg=Decimal('250.0'),
            method="MANUAL"
        )
        
        # Create feeding event for yesterday
        yesterday = timezone.now().date() - timedelta(days=1)
        yesterday_event = FeedingEvent.objects.create(
            batch=batch,
            container=container,
            feed=self.feed,
            feeding_date=yesterday,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal('10.0'),
            batch_biomass_kg=Decimal('250.0'),
            method="MANUAL"
        )
        
        # Get the overview data
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Check that only today's feeding event is counted
        self.assertEqual(data['feeding_events_today'], 1)
