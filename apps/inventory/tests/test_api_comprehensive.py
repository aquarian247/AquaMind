"""
Comprehensive API tests for the Inventory app.

This module contains tests for all Inventory API endpoints, focusing on:
1. CRUD operations for feed, equipment, supplies
2. Filtering and search functionality
3. Stock level calculations and alerts
4. Batch assignment and consumption tracking
5. Business rules validation
"""

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import (
    ContainerType, Geography, FreshwaterStation, Hall, Container, FeedContainer
)
from apps.inventory.models import (
    Feed, FeedPurchase, FeedStock, FeedingEvent, BatchFeedingSummary, FeedContainerStock
)
from tests.base import BaseAPITestCase

User = get_user_model()


class FeedAPITest(BaseAPITestCase):
    """Test the Feed API endpoints."""
    
    def setUp(self):
        """Set up test data for feed API tests."""
        super().setUp()
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER",
            pellet_size_mm=Decimal('1.5'),
            protein_pct=Decimal('45'),
            fat_pct=Decimal('20'),
            carb_pct=Decimal('15'),
            fiber_pct=Decimal('2'),
            ash_pct=Decimal('8'),
            phosphorus_pct=Decimal('1.2'),
            digestible_energy_mj_kg=Decimal('20')
        )
        
        # Create another feed for list tests
        self.feed2 = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER",
            pellet_size_mm=Decimal('3.0'),
            protein_pct=Decimal('40'),
            fat_pct=Decimal('18'),
            carb_pct=Decimal('20'),
            fiber_pct=Decimal('3'),
            ash_pct=Decimal('7'),
            phosphorus_pct=Decimal('1.0'),
            digestible_energy_mj_kg=Decimal('19')
        )
        
        # URL for feed endpoints
        self.list_url = self.get_api_url('inventory', 'feeds')
        self.detail_url = self.get_api_url('inventory', 'feeds', detail=True, pk=self.feed.id)
    
    def test_feed_list(self):
        """Test retrieving a list of feeds."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Should return both feeds
        
        # Check that the feed data is correct
        feed_data = response.data['results'][0]
        self.assertEqual(feed_data['name'], self.feed2.name)  # Ordered by name
        self.assertEqual(feed_data['manufacturer'], self.feed2.manufacturer)
        self.assertEqual(feed_data['feed_type'], self.feed2.feed_type)
    
    def test_feed_detail(self):
        """Test retrieving a single feed."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.feed.name)
        self.assertEqual(response.data['manufacturer'], self.feed.manufacturer)
        self.assertEqual(response.data['feed_type'], self.feed.feed_type)
        self.assertEqual(Decimal(response.data['pellet_size_mm']), self.feed.pellet_size_mm)
        self.assertEqual(Decimal(response.data['protein_pct']), self.feed.protein_pct)
    
    def test_feed_create(self):
        """Test creating a new feed."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'name': 'New Test Feed',
            'manufacturer': 'New Manufacturer',
            'feed_type': 'FINISHER',
            'pellet_size_mm': '4.5',
            'protein_pct': '35',
            'fat_pct': '22',
            'carb_pct': '25',
            'fiber_pct': '2.5',
            'ash_pct': '6',
            'phosphorus_pct': '0.8',
            'digestible_energy_mj_kg': '18'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Feed.objects.count(), 3)  # Should now have 3 feeds
        
        # Check that the feed was created with the correct data
        created_feed = Feed.objects.get(name='New Test Feed')
        self.assertEqual(created_feed.manufacturer, 'New Manufacturer')
        self.assertEqual(created_feed.feed_type, 'FINISHER')
        self.assertEqual(created_feed.pellet_size_mm, Decimal('4.5'))
    
    def test_feed_update(self):
        """Test updating an existing feed."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'name': 'Updated Feed',
            'manufacturer': self.feed.manufacturer,
            'feed_type': self.feed.feed_type,
            'pellet_size_mm': self.feed.pellet_size_mm,
            'protein_pct': '50',  # Updated value
            'fat_pct': self.feed.fat_pct,
            'carb_pct': self.feed.carb_pct,
            'fiber_pct': self.feed.fiber_pct,
            'ash_pct': self.feed.ash_pct,
            'phosphorus_pct': self.feed.phosphorus_pct,
            'digestible_energy_mj_kg': self.feed.digestible_energy_mj_kg
        }
        
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the feed was updated with the correct data
        self.feed.refresh_from_db()
        self.assertEqual(self.feed.name, 'Updated Feed')
        self.assertEqual(self.feed.protein_pct, Decimal('50'))
    
    def test_feed_partial_update(self):
        """Test partially updating a feed."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'name': 'Partially Updated Feed'
        }
        
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only the name was updated
        self.feed.refresh_from_db()
        self.assertEqual(self.feed.name, 'Partially Updated Feed')
        self.assertEqual(self.feed.manufacturer, 'Test Manufacturer')  # Unchanged
    
    def test_feed_delete(self):
        """Test deleting a feed."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Feed.objects.count(), 1)  # Should now have 1 feed
    
    def test_feed_search(self):
        """Test searching for feeds by name or manufacturer."""
        # Search by name
        response = self.client.get(f"{self.list_url}?search=Another")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Another Feed')
        
        # Search by manufacturer
        response = self.client.get(f"{self.list_url}?search=Test Manufacturer")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Feed')
    
    def test_feed_filter(self):
        """Test filtering feeds by feed_type."""
        response = self.client.get(f"{self.list_url}?feed_type=STARTER")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Feed')
        
        response = self.client.get(f"{self.list_url}?feed_type=GROWER")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Another Feed')


class FeedPurchaseAPITest(BaseAPITestCase):
    """Test the FeedPurchase API endpoints."""
    
    def setUp(self):
        """Set up test data for feed purchase API tests."""
        super().setUp()
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER",
            pellet_size_mm=Decimal('1.5'),
            protein_pct=Decimal('45')
        )
        
        # Create a feed purchase
        self.feed_purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            price_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123",
            expiration_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        
        # URL for feed purchase endpoints
        self.list_url = self.get_api_url('inventory', 'feed-purchases')
        self.detail_url = self.get_api_url('inventory', 'feed-purchases', detail=True, pk=self.feed_purchase.id)
    
    def test_feed_purchase_list(self):
        """Test retrieving a list of feed purchases."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Check that the feed purchase data is correct
        purchase_data = response.data['results'][0]
        self.assertEqual(purchase_data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(purchase_data['quantity_kg']), self.feed_purchase.quantity_kg)
        self.assertEqual(Decimal(purchase_data['price_per_kg']), self.feed_purchase.price_per_kg)
        self.assertEqual(purchase_data['supplier'], self.feed_purchase.supplier)
    
    def test_feed_purchase_detail(self):
        """Test retrieving a single feed purchase."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(response.data['quantity_kg']), self.feed_purchase.quantity_kg)
        self.assertEqual(Decimal(response.data['price_per_kg']), self.feed_purchase.price_per_kg)
        self.assertEqual(response.data['supplier'], self.feed_purchase.supplier)
        self.assertEqual(response.data['batch_number'], self.feed_purchase.batch_number)
    
    def test_feed_purchase_create(self):
        """Test creating a new feed purchase."""
        data = {
            'feed': self.feed.id,
            'purchase_date': timezone.now().date().isoformat(),
            'quantity_kg': '500',
            'price_per_kg': '3.00',
            'supplier': 'New Supplier',
            'batch_number': 'BATCH456',
            'expiration_date': (timezone.now().date() + timezone.timedelta(days=180)).isoformat()
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FeedPurchase.objects.count(), 2)  # Should now have 2 purchases
        
        # Check that the purchase was created with the correct data
        created_purchase = FeedPurchase.objects.get(batch_number='BATCH456')
        self.assertEqual(created_purchase.feed, self.feed)
        self.assertEqual(created_purchase.quantity_kg, Decimal('500'))
        self.assertEqual(created_purchase.price_per_kg, Decimal('3.00'))
        self.assertEqual(created_purchase.supplier, 'New Supplier')
    
    def test_feed_purchase_update(self):
        """Test updating an existing feed purchase."""
        data = {
            'feed': self.feed.id,
            'purchase_date': self.feed_purchase.purchase_date.isoformat(),
            'quantity_kg': '1200',  # Updated value
            'price_per_kg': '2.75',  # Updated value
            'supplier': self.feed_purchase.supplier,
            'batch_number': self.feed_purchase.batch_number,
            'expiration_date': self.feed_purchase.expiration_date.isoformat()
        }
        
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the purchase was updated with the correct data
        self.feed_purchase.refresh_from_db()
        self.assertEqual(self.feed_purchase.quantity_kg, Decimal('1200'))
        self.assertEqual(self.feed_purchase.price_per_kg, Decimal('2.75'))
    
    def test_feed_purchase_filter(self):
        """Test filtering feed purchases by feed, supplier, and date range."""
        # Create another feed and purchase for testing filters
        another_feed = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER"
        )
        
        FeedPurchase.objects.create(
            feed=another_feed,
            purchase_date=timezone.now().date() - timezone.timedelta(days=10),
            quantity_kg=Decimal('800'),
            price_per_kg=Decimal('2.25'),
            supplier="Another Supplier",
            batch_number="BATCH789",
            expiration_date=timezone.now().date() + timezone.timedelta(days=120)
        )
        
        # Filter by feed
        response = self.client.get(f"{self.list_url}?feed={self.feed.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed']['name'], self.feed.name)
        
        # Filter by supplier
        response = self.client.get(f"{self.list_url}?supplier=Another Supplier")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['supplier'], "Another Supplier")
        
        # Filter by date range
        today = timezone.now().date().isoformat()
        response = self.client.get(f"{self.list_url}?purchase_date_after={today}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only the purchase from today
        
        # Filter by batch number
        response = self.client.get(f"{self.list_url}?batch_number=BATCH123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_number'], "BATCH123")
    
    def test_feed_purchase_validation(self):
        """Test validation rules for feed purchases."""
        # Test negative quantity
        data = {
            'feed': self.feed.id,
            'purchase_date': timezone.now().date().isoformat(),
            'quantity_kg': '-100',  # Invalid: negative quantity
            'price_per_kg': '2.50',
            'supplier': 'Test Supplier',
            'batch_number': 'INVALID_BATCH'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity_kg', response.data)
        
        # Test negative price
        data['quantity_kg'] = '100'
        data['price_per_kg'] = '-1.00'  # Invalid: negative price
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price_per_kg', response.data)
        
        # Test missing required fields
        data = {
            'feed': self.feed.id,
            # Missing purchase_date
            'quantity_kg': '100',
            'price_per_kg': '2.50'
            # Missing supplier
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_date', response.data)
        self.assertIn('supplier', response.data)


class FeedStockAPITest(BaseAPITestCase):
    """Test the FeedStock API endpoints."""
    
    def setUp(self):
        """Set up test data for feed stock API tests."""
        super().setUp()
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER"
        )
        
        # Create a feed purchase
        self.feed_purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            price_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123"
        )
        
        # Create a feed stock
        self.feed_stock = FeedStock.objects.create(
            feed=self.feed,
            purchase=self.feed_purchase,
            batch_number="BATCH123",
            initial_quantity_kg=Decimal('1000'),
            current_quantity_kg=Decimal('800'),
            location="Main Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        
        # URL for feed stock endpoints
        self.list_url = self.get_api_url('inventory', 'feed-stocks')
        self.detail_url = self.get_api_url('inventory', 'feed-stocks', detail=True, pk=self.feed_stock.id)
    
    def test_feed_stock_list(self):
        """Test retrieving a list of feed stocks."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Check that the feed stock data is correct
        stock_data = response.data['results'][0]
        self.assertEqual(stock_data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(stock_data['initial_quantity_kg']), self.feed_stock.initial_quantity_kg)
        self.assertEqual(Decimal(stock_data['current_quantity_kg']), self.feed_stock.current_quantity_kg)
        self.assertEqual(stock_data['location'], self.feed_stock.location)
    
    def test_feed_stock_detail(self):
        """Test retrieving a single feed stock."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(response.data['initial_quantity_kg']), self.feed_stock.initial_quantity_kg)
        self.assertEqual(Decimal(response.data['current_quantity_kg']), self.feed_stock.current_quantity_kg)
        self.assertEqual(response.data['location'], self.feed_stock.location)
        self.assertEqual(response.data['batch_number'], self.feed_stock.batch_number)
    
    def test_feed_stock_update(self):
        """Test updating an existing feed stock."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'feed': self.feed.id,
            'purchase': self.feed_purchase.id,
            'batch_number': self.feed_stock.batch_number,
            'initial_quantity_kg': self.feed_stock.initial_quantity_kg,
            'current_quantity_kg': '750',  # Updated value
            'location': 'New Location',  # Updated value
            'expiration_date': self.feed_stock.expiration_date.isoformat()
        }
        
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the stock was updated with the correct data
        self.feed_stock.refresh_from_db()
        self.assertEqual(self.feed_stock.current_quantity_kg, Decimal('750'))
        self.assertEqual(self.feed_stock.location, 'New Location')
    
    def test_feed_stock_partial_update(self):
        """Test partially updating a feed stock."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'current_quantity_kg': '700'
        }
        
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only the current quantity was updated
        self.feed_stock.refresh_from_db()
        self.assertEqual(self.feed_stock.current_quantity_kg, Decimal('700'))
        self.assertEqual(self.feed_stock.location, 'Main Warehouse')  # Unchanged
    
    def test_feed_stock_filter(self):
        """Test filtering feed stocks by feed, batch number, and location."""
        # Create another feed and stock for testing filters
        another_feed = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER"
        )
        
        another_purchase = FeedPurchase.objects.create(
            feed=another_feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('500'),
            price_per_kg=Decimal('3.00'),
            supplier="Another Supplier",
            batch_number="BATCH456"
        )
        
        FeedStock.objects.create(
            feed=another_feed,
            purchase=another_purchase,
            batch_number="BATCH456",
            initial_quantity_kg=Decimal('500'),
            current_quantity_kg=Decimal('500'),
            location="Secondary Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=120)
        )
        
        # Filter by feed
        response = self.client.get(f"{self.list_url}?feed={self.feed.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed']['name'], self.feed.name)
        
        # Filter by batch number
        response = self.client.get(f"{self.list_url}?batch_number=BATCH123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_number'], "BATCH123")
        
        # Filter by location
        response = self.client.get(f"{self.list_url}?location=Secondary Warehouse")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['location'], "Secondary Warehouse")
    
    def test_feed_stock_validation(self):
        """Test validation rules for feed stocks."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        # Test current quantity greater than initial quantity
        data = {
            'feed': self.feed.id,
            'purchase': self.feed_purchase.id,
            'batch_number': 'BATCH789',
            'initial_quantity_kg': '500',
            'current_quantity_kg': '600',  # Invalid: greater than initial
            'location': 'Test Location'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_quantity_kg', response.data)
        
        # Test negative initial quantity
        data['initial_quantity_kg'] = '-100'  # Invalid: negative quantity
        data['current_quantity_kg'] = '0'
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('initial_quantity_kg', response.data)
    
    def test_low_stock_alert(self):
        """Test the low stock alert functionality."""
        # Update the stock to a low level
        self.feed_stock.current_quantity_kg = Decimal('50')  # 5% of initial quantity
        self.feed_stock.save()
        
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['low_stock_alert'])
        
        # Update the stock to a normal level
        self.feed_stock.current_quantity_kg = Decimal('500')  # 50% of initial quantity
        self.feed_stock.save()
        
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['low_stock_alert'])


class FeedingEventAPITest(BaseAPITestCase):
    """Test the FeedingEvent API endpoints."""
    
    def setUp(self):
        """Set up test data for feeding event API tests."""
        super().setUp()
        
        # Create species and lifecycle stage
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,  # Ensure required FK is provided
            }
        )
        
        # Create a batch
        self.batch = Batch.objects.create(
            batch_number="TEST-BATCH-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create batch-container assignment
        from apps.batch.models import BatchContainerAssignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            start_date=timezone.now().date(),
            population_count=1000,
            lifecycle_stage=self.lifecycle_stage
        )
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER"
        )
        
        # Create a feed purchase and stock
        self.feed_purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            price_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123"
        )
        
        self.feed_stock = FeedStock.objects.create(
            feed=self.feed,
            purchase=self.feed_purchase,
            batch_number="BATCH123",
            initial_quantity_kg=Decimal('1000'),
            current_quantity_kg=Decimal('1000'),
            location="Main Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        
        # Create a feeding event
        self.feeding_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            stock=self.feed_stock,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal('10'),
            batch_biomass_kg=Decimal('500'),
            method="MANUAL",
            recorded_by=self.user
        )
        
        # URL for feeding event endpoints
        self.list_url = self.get_api_url('inventory', 'feeding-events')
        self.detail_url = self.get_api_url('inventory', 'feeding-events', detail=True, pk=self.feeding_event.id)
    
    def test_feeding_event_list(self):
        """Test retrieving a list of feeding events."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Check that the feeding event data is correct
        event_data = response.data['results'][0]
        self.assertEqual(event_data['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(event_data['container']['name'], self.container.name)
        self.assertEqual(event_data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(event_data['amount_kg']), self.feeding_event.amount_kg)
        self.assertEqual(Decimal(event_data['batch_biomass_kg']), self.feeding_event.batch_biomass_kg)
    
    def test_feeding_event_detail(self):
        """Test retrieving a single feeding event."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(response.data['container']['name'], self.container.name)
        self.assertEqual(response.data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(response.data['amount_kg']), self.feeding_event.amount_kg)
        self.assertEqual(Decimal(response.data['batch_biomass_kg']), self.feeding_event.batch_biomass_kg)
    
    def test_feeding_event_create(self):
        """Test creating a new feeding event."""
        # Verify initial stock quantity
        initial_stock_qty = self.feed_stock.current_quantity_kg
        
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5',
            'batch_biomass_kg': '550',
            'method': 'MANUAL',
            'notes': 'Test feeding event'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FeedingEvent.objects.count(), 2)  # Should now have 2 events
        
        # Check that the event was created with the correct data
        created_event = FeedingEvent.objects.latest('id')
        self.assertEqual(created_event.batch, self.batch)
        self.assertEqual(created_event.container, self.container)
        self.assertEqual(created_event.feed, self.feed)
        self.assertEqual(created_event.amount_kg, Decimal('5'))
        self.assertEqual(created_event.batch_biomass_kg, Decimal('550'))
        
        # Check that the stock quantity was updated
        self.feed_stock.refresh_from_db()
        self.assertEqual(self.feed_stock.current_quantity_kg, initial_stock_qty - Decimal('5'))
    
    def test_feeding_event_filter(self):
        """Test filtering feeding events by batch, container, feed, and date range."""
        # Create another batch, container, and feed for testing filters
        another_batch = Batch.objects.create(
            batch_number="TEST-BATCH-002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        another_container = Container.objects.create(
            name="Another Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        another_feed = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER"
        )
        
        # Create another feed purchase and stock
        another_purchase = FeedPurchase.objects.create(
            feed=another_feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('500'),
            price_per_kg=Decimal('3.00'),
            supplier="Another Supplier",
            batch_number="BATCH456"
        )
        
        another_stock = FeedStock.objects.create(
            feed=another_feed,
            purchase=another_purchase,
            batch_number="BATCH456",
            initial_quantity_kg=Decimal('500'),
            current_quantity_kg=Decimal('500'),
            location="Secondary Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=120)
        )
        
        # Create another feeding event with different batch, container, and feed
        FeedingEvent.objects.create(
            batch=another_batch,
            container=another_container,
            feed=another_feed,
            stock=another_stock,
            feeding_date=timezone.now().date() - timezone.timedelta(days=1),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal('8'),
            batch_biomass_kg=Decimal('400'),
            method="MANUAL",
            recorded_by=self.user
        )
        
        # Filter by batch
        response = self.client.get(f"{self.list_url}?batch={self.batch.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch']['batch_number'], self.batch.batch_number)
        
        # Filter by container
        response = self.client.get(f"{self.list_url}?container={another_container.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['container']['name'], another_container.name)
        
        # Filter by feed
        response = self.client.get(f"{self.list_url}?feed={another_feed.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed']['name'], another_feed.name)
        
        # Filter by date range
        today = timezone.now().date().isoformat()
        response = self.client.get(f"{self.list_url}?feeding_date={today}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only today's event
    
    def test_feeding_event_validation(self):
        """Test validation rules for feeding events."""
        # Test negative amount
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '-5',  # Invalid: negative amount
            'batch_biomass_kg': '500',
            'method': 'MANUAL'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_kg', response.data)
        
        # Test negative biomass
        data['amount_kg'] = '5'
        data['batch_biomass_kg'] = '-100'  # Invalid: negative biomass
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('batch_biomass_kg', response.data)
        
        # Test insufficient stock
        data['batch_biomass_kg'] = '500'
        data['amount_kg'] = '2000'  # Invalid: more than available stock
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_kg', response.data)
    
    def test_feeding_percentage_calculation(self):
        """Test that feeding percentage is automatically calculated."""
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '10',
            'batch_biomass_kg': '500',
            'method': 'MANUAL'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Expected feeding percentage: (10 / 500) * 100 = 2%
        self.assertAlmostEqual(float(response.data['feeding_percentage']), 0.02)


class FeedContainerStockAPITest(BaseAPITestCase):
    """Test the FeedContainerStock API endpoints."""
    
    def setUp(self):
        """Set up test data for feed container stock API tests."""
        super().setUp()
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create a feed container
        self.feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            container_type=self.container_type,
            hall=self.hall,
            capacity_kg=Decimal('100')
        )
        
        # Create a feed purchase and stock
        self.feed_purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            price_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123"
        )
        
        self.feed_stock = FeedStock.objects.create(
            feed=self.feed,
            purchase=self.feed_purchase,
            batch_number="BATCH123",
            initial_quantity_kg=Decimal('1000'),
            current_quantity_kg=Decimal('1000'),
            location="Main Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        
        # Create a feed container stock
        self.container_stock = FeedContainerStock.objects.create(
            feed_container=self.feed_container,
            feed=self.feed,
            stock=self.feed_stock,
            quantity_kg=Decimal('50'),
            entry_date=timezone.now().date()
        )
        
        # URL for feed container stock endpoints
        self.list_url = self.get_api_url('inventory', 'feed-container-stocks')
        self.detail_url = self.get_api_url('inventory', 'feed-container-stocks', detail=True, pk=self.container_stock.id)
    
    def test_container_stock_list(self):
        """Test retrieving a list of feed container stocks."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Check that the container stock data is correct
        stock_data = response.data['results'][0]
        self.assertEqual(stock_data['feed_container']['name'], self.feed_container.name)
        self.assertEqual(stock_data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(stock_data['quantity_kg']), self.container_stock.quantity_kg)
    
    def test_container_stock_detail(self):
        """Test retrieving a single feed container stock."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['feed_container']['name'], self.feed_container.name)
        self.assertEqual(response.data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(response.data['quantity_kg']), self.container_stock.quantity_kg)
    
    def test_container_stock_create(self):
        """Test creating a new feed container stock."""
        # Verify initial stock quantity
        initial_stock_qty = self.feed_stock.current_quantity_kg
        
        data = {
            'feed_container': self.feed_container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'quantity_kg': '20',
            'entry_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FeedContainerStock.objects.count(), 2)  # Should now have 2 container stocks
        
        # Check that the container stock was created with the correct data
        created_stock = FeedContainerStock.objects.latest('id')
        self.assertEqual(created_stock.feed_container, self.feed_container)
        self.assertEqual(created_stock.feed, self.feed)
        self.assertEqual(created_stock.quantity_kg, Decimal('20'))
        
        # Check that the stock quantity was updated
        self.feed_stock.refresh_from_db()
        self.assertEqual(self.feed_stock.current_quantity_kg, initial_stock_qty - Decimal('20'))
    
    def test_container_stock_update(self):
        """Test updating an existing feed container stock."""
        # Verify initial stock quantity
        initial_stock_qty = self.feed_stock.current_quantity_kg
        initial_container_qty = self.container_stock.quantity_kg
        
        data = {
            'feed_container': self.feed_container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'quantity_kg': '60',  # Updated value
            'entry_date': self.container_stock.entry_date.isoformat()
        }
        
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the container stock was updated with the correct data
        self.container_stock.refresh_from_db()
        self.assertEqual(self.container_stock.quantity_kg, Decimal('60'))
        
        # Check that the stock quantity was updated
        self.feed_stock.refresh_from_db()
        # Original 50kg was returned to stock, then 60kg was taken out
        expected_qty = initial_stock_qty + initial_container_qty - Decimal('60')
        self.assertEqual(self.feed_stock.current_quantity_kg, expected_qty)
    
    def test_container_stock_filter(self):
        """Test filtering feed container stocks by feed container, feed, and date range."""
        # Create another feed container, feed, and container stock for testing filters
        another_feed_container = FeedContainer.objects.create(
            name="Another Feed Container",
            container_type=self.container_type,
            hall=self.hall,
            capacity_kg=Decimal('150')
        )
        
        another_feed = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER"
        )
        
        another_purchase = FeedPurchase.objects.create(
            feed=another_feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('500'),
            price_per_kg=Decimal('3.00'),
            supplier="Another Supplier",
            batch_number="BATCH456"
        )
        
        another_stock = FeedStock.objects.create(
            feed=another_feed,
            purchase=another_purchase,
            batch_number="BATCH456",
            initial_quantity_kg=Decimal('500'),
            current_quantity_kg=Decimal('500'),
            location="Secondary Warehouse",
            expiration_date=timezone.now().date() + timezone.timedelta(days=120)
        )
        
        FeedContainerStock.objects.create(
            feed_container=another_feed_container,
            feed=another_feed,
            stock=another_stock,
            quantity_kg=Decimal('30'),
            entry_date=timezone.now().date() - timezone.timedelta(days=1)
        )
        
        # Filter by feed container
        response = self.client.get(f"{self.list_url}?feed_container={self.feed_container.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed_container']['name'], self.feed_container.name)
        
        # Filter by feed
        response = self.client.get(f"{self.list_url}?feed={another_feed.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed']['name'], another_feed.name)
        
        # Filter by date range
        yesterday = (timezone.now().date() - timezone.timedelta(days=1)).isoformat()
        response = self.client.get(f"{self.list_url}?entry_date={yesterday}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only yesterday's entry
    
    def test_container_stock_validation(self):
        """Test validation rules for feed container stocks."""
        # Test negative quantity
        data = {
            'feed_container': self.feed_container.id,
            'feed': self.feed.id,
            'stock': self.feed_stock.id,
            'quantity_kg': '-10',  # Invalid: negative quantity
            'entry_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity_kg', response.data)
        
        # Test quantity exceeding feed container capacity
        data['quantity_kg'] = '150'  # Invalid: exceeds capacity of 100
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity_kg', response.data)
        
        # Test insufficient stock
        data['quantity_kg'] = '2000'  # Invalid: more than available stock
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity_kg', response.data)


class BatchFeedingSummaryAPITest(BaseAPITestCase):
    """Test the BatchFeedingSummary API endpoints."""
    
    def setUp(self):
        """Set up test data for batch feeding summary API tests."""
        super().setUp()
        
        # Create species and lifecycle stage
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,  # Ensure required FK is provided
            }
        )
        
        # Create a batch
        self.batch = Batch.objects.create(
            batch_number="TEST-BATCH-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            manufacturer="Test Manufacturer",
            feed_type="STARTER"
        )
        
        # Create a batch feeding summary
        self.summary = BatchFeedingSummary.objects.create(
            batch=self.batch,
            feed=self.feed,
            summary_date=timezone.now().date(),
            total_feed_kg=Decimal('100'),
            total_biomass_kg=Decimal('5000'),
            fcr=Decimal('0.5'),
            feed_cost=Decimal('250')
        )
        
        # URL for batch feeding summary endpoints
        self.list_url = self.get_api_url('inventory', 'batch-feeding-summaries')
        self.detail_url = self.get_api_url('inventory', 'batch-feeding-summaries', detail=True, pk=self.summary.id)
    
    def test_summary_list(self):
        """Test retrieving a list of batch feeding summaries."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Check that the summary data is correct
        summary_data = response.data['results'][0]
        self.assertEqual(summary_data['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(summary_data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(summary_data['total_feed_kg']), self.summary.total_feed_kg)
        self.assertEqual(Decimal(summary_data['total_biomass_kg']), self.summary.total_biomass_kg)
        self.assertEqual(Decimal(summary_data['fcr']), self.summary.fcr)
        self.assertEqual(Decimal(summary_data['feed_cost']), self.summary.feed_cost)
    
    def test_summary_detail(self):
        """Test retrieving a single batch feeding summary."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(response.data['feed']['name'], self.feed.name)
        self.assertEqual(Decimal(response.data['total_feed_kg']), self.summary.total_feed_kg)
        self.assertEqual(Decimal(response.data['total_biomass_kg']), self.summary.total_biomass_kg)
        self.assertEqual(Decimal(response.data['fcr']), self.summary.fcr)
        self.assertEqual(Decimal(response.data['feed_cost']), self.summary.feed_cost)
    
    def test_summary_filter(self):
        """Test filtering batch feeding summaries by batch, feed, and date range."""
        # Create another batch, feed, and summary for testing filters
        another_batch = Batch.objects.create(
            batch_number="TEST-BATCH-002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        another_feed = Feed.objects.create(
            name="Another Feed",
            manufacturer="Another Manufacturer",
            feed_type="GROWER"
        )
        
        BatchFeedingSummary.objects.create(
            batch=another_batch,
            feed=another_feed,
            summary_date=timezone.now().date() - timezone.timedelta(days=1),
            total_feed_kg=Decimal('80'),
            total_biomass_kg=Decimal('4000'),
            fcr=Decimal('0.6'),
            feed_cost=Decimal('200')
        )
        
        # Filter by batch
        response = self.client.get(f"{self.list_url}?batch={self.batch.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch']['batch_number'], self.batch.batch_number)
        
        # Filter by feed
        response = self.client.get(f"{self.list_url}?feed={another_feed.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['feed']['name'], another_feed.name)
        
        # Filter by date range
        today = timezone.now().date().isoformat()
        response = self.client.get(f"{self.list_url}?summary_date={today}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only today's summary
    
    def test_fcr_calculation(self):
        """Test FCR calculation in the API response."""
        # Create a new summary with FCR calculation
        data = {
            'batch': self.batch.id,
            'feed': self.feed.id,
            'summary_date': timezone.now().date().isoformat(),
            'total_feed_kg': '200',
            'total_biomass_kg': '1000',
            # FCR should be calculated automatically
            'feed_cost': '500'
        }
        
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Expected FCR: 200 / 1000 = 0.2
        self.assertEqual(Decimal(response.data['fcr']), Decimal('0.2'))
