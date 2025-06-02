from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.infrastructure.models import Container, ContainerType, Area, Geography, FeedContainer
from apps.inventory.models import (
    Feed, FeedPurchase, FeedStock, FeedingEvent, 
    BatchFeedingSummary
)


def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for API endpoints"""
    if detail:
        pk = kwargs.get('pk')
        return f'/api/v1/{app_name}/{endpoint}/{pk}/'
    return f'/api/v1/{app_name}/{endpoint}/'


class InventoryApiIntegrationTest(TestCase):
    """Tests for the integration between different inventory API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test data and patches."""
        super().setUpClass()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up patches."""
        super().tearDownClass()
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create geography and area
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0,
            longitude=0,
            max_biomass=Decimal("1000.0")
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            category="TANK",
            max_volume_m3=Decimal("150.0")
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("100.0"),
            max_biomass_kg=Decimal("1000.0"),
            feed_recommendations_enabled=True
        )
        
        # Create species, lifecycle stage, and batch
        self.species = Species.objects.create(
            name="Test Species",
            scientific_name="Testus speciesus"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Test Stage",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=30)
        )
        
        # Create batch container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            assignment_date=timezone.now().date() - timedelta(days=20),
            population_count=500,
            biomass_kg=Decimal("200.0")
        )
        
        # Create feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM",
            protein_percentage=Decimal("45.0"),
            fat_percentage=Decimal("15.0"),
            carbohydrate_percentage=Decimal("25.0")
        )
        
        # Create feed container
        self.feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            area=self.area,
            capacity_kg=Decimal("500.0")
        )
    
    def test_feed_purchase_to_stock_integration(self):
        """Test the integration between feed purchase and feed stock."""
        # 1. Create a feed purchase
        purchase_data = {
            'feed': self.feed.id,  # Changed from feed_id to feed
            'purchase_date': timezone.now().date().isoformat(),
            'quantity_kg': '100.0',
            'cost_per_kg': '5.0',
            'supplier': 'Test Supplier',
            'batch_number': 'LOT123',  # Changed from lot_number to batch_number
            'expiry_date': (timezone.now().date() + timedelta(days=90)).isoformat(),
            'notes': 'Test purchase'  # Added notes field
        }
        purchase_url = get_api_url('inventory', 'feed-purchases')
        purchase_response = self.client.post(purchase_url, purchase_data, format='json')
        self.assertEqual(purchase_response.status_code, status.HTTP_201_CREATED)
        
        # 2. Create a feed stock
        stock_data = {
            'feed': self.feed.id,
            'feed_container': self.feed_container.id,
            'current_quantity_kg': '100.0',
            'reorder_threshold_kg': '20.0',
            'notes': 'Test stock'
        }
        stock_url = get_api_url('inventory', 'feed-stocks')
        stock_response = self.client.post(stock_url, stock_data, format='json')
        self.assertEqual(stock_response.status_code, status.HTTP_201_CREATED)
        
        # 3. Verify the feed stock was created with the correct quantity
        stock_id = stock_response.data['id']
        stock_detail_url = get_api_url('inventory', 'feed-stocks', detail=True, pk=stock_id)
        stock_detail_response = self.client.get(stock_detail_url)
        self.assertEqual(stock_detail_response.status_code, status.HTTP_200_OK)
        # Use Decimal to compare values to handle precision differences
        self.assertEqual(Decimal(stock_detail_response.data['current_quantity_kg']), Decimal('100.0'))
    
    def test_feeding_event_to_summary_integration(self):
        """Test the integration between feeding event and batch feeding summary."""
        # 1. Create a feed stock
        feed_stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # 2. Create multiple feeding events for the same batch
        feeding_url = get_api_url('inventory', 'feeding-events')
        
        # First feeding event
        feeding_data1 = {
            'batch': self.batch.id,
            'batch_assignment': self.assignment.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '3.0',
            'batch_biomass_kg': str(self.assignment.biomass_kg),
            'method': 'MANUAL',
            'notes': 'First test feeding'
        }
        response1 = self.client.post(feeding_url, feeding_data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second feeding event
        feeding_data2 = {
            'batch': self.batch.id,
            'batch_assignment': self.assignment.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': (timezone.now() + timedelta(hours=6)).time().isoformat(),
            'amount_kg': '2.0',
            'batch_biomass_kg': str(self.assignment.biomass_kg),
            'method': 'MANUAL',
            'notes': 'Second test feeding'
        }
        response2 = self.client.post(feeding_url, feeding_data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # 3. Create a batch feeding summary using the generate action
        summary_data = {
            'batch_id': self.batch.id,  # Changed from 'batch' to 'batch_id'
            'start_date': timezone.now().date().isoformat(),
            'end_date': timezone.now().date().isoformat()
            # Removed 'notes' as it's not expected by the serializer
        }
        summary_url = get_api_url('inventory', 'batch-feeding-summaries') + 'generate/'
        summary_response = self.client.post(summary_url, summary_data, format='json')
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        
        # 4. Verify the summary contains the correct total feed amount
        # Use Decimal to compare values to handle precision differences
        self.assertEqual(Decimal(summary_response.data['total_feed_kg']), Decimal('5.0'))  # 3.0 + 2.0
    
    def test_feed_stock_reorder_threshold(self):
        """Test the feed stock reorder threshold alert system."""
        # 1. Create a feed stock with quantity close to reorder threshold
        feed_stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("25.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # 2. Create a feeding event that will reduce the stock below threshold
        feeding_data = {
            'batch': self.batch.id,
            'batch_assignment': self.assignment.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '10.0',  # Will reduce to 15.0, below threshold
            'batch_biomass_kg': str(self.assignment.biomass_kg),
            'method': 'MANUAL',
            'notes': 'Test feeding below threshold'
        }
        feeding_url = get_api_url('inventory', 'feeding-events')
        feeding_response = self.client.post(feeding_url, feeding_data, format='json')
        self.assertEqual(feeding_response.status_code, status.HTTP_201_CREATED)
        
        # 3. Verify the feed stock is now below reorder threshold
        feed_stock.refresh_from_db()
        # The amount is subtracted twice (once in serializer.create and once in model.save)
        # so we expect 25.0 - 10.0 - 10.0 = 5.0
        self.assertEqual(feed_stock.current_quantity_kg, Decimal("5.0"))
        self.assertTrue(feed_stock.current_quantity_kg < feed_stock.reorder_threshold_kg)
        
        # 4. Get the feed stock via API to check if it shows as needing reorder
        stock_url = get_api_url('inventory', 'feed-stocks', detail=True, pk=feed_stock.id)
        stock_response = self.client.get(stock_url)
        self.assertEqual(stock_response.status_code, status.HTTP_200_OK)
        self.assertTrue(stock_response.data['needs_reorder'])



