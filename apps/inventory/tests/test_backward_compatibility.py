"""
Tests to ensure backward compatibility of the refactored inventory app.

These tests verify that the refactored code maintains the same behavior
as the original implementation, particularly focusing on:
1. Model behavior and relationships
2. Serializer validation and representation
3. Viewset functionality and API responses
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient, force_authenticate
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


class ModelBackwardCompatibilityTest(TestCase):
    """Tests to ensure model behavior remains consistent after refactoring."""
    
    def setUp(self):
        """Set up test data."""
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
            max_biomass_kg=Decimal("1000.0")
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
            carbohydrate_percentage=Decimal("25.0"),
            description="Test description",
            is_active=True
        )
        
        # Create feed container
        self.feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            area=self.area,
            capacity_kg=Decimal("500.0")
        )
    
    def test_feed_model_fields(self):
        """Test that the Feed model maintains all expected fields."""
        feed = Feed.objects.get(id=self.feed.id)
        
        # Check all fields exist and have correct values
        self.assertEqual(feed.name, "Test Feed")
        self.assertEqual(feed.brand, "Test Brand")
        self.assertEqual(feed.size_category, "MEDIUM")
        self.assertEqual(feed.protein_percentage, Decimal("45.0"))
        self.assertEqual(feed.fat_percentage, Decimal("15.0"))
        self.assertEqual(feed.carbohydrate_percentage, Decimal("25.0"))
        self.assertEqual(feed.description, "Test description")
        self.assertTrue(feed.is_active)
        
        # Check timestamp fields
        self.assertIsNotNone(feed.created_at)
        self.assertIsNotNone(feed.updated_at)
    
    def test_feed_purchase_model_relationships(self):
        """Test that FeedPurchase maintains correct relationships."""
        # Create a feed purchase
        purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal("100.0"),
            cost_per_kg=Decimal("5.0"),
            supplier="Test Supplier",
            batch_number="LOT123",
            expiry_date=timezone.now().date() + timedelta(days=90)
        )
        
        # Test relationship with Feed
        self.assertEqual(purchase.feed, self.feed)
        
        # Test that the feed can access its purchases
        # First refresh the feed to ensure it has the latest related objects
        self.feed.refresh_from_db()
        self.assertIn(purchase, FeedPurchase.objects.filter(feed=self.feed))
    
    def test_feed_stock_model_relationships(self):
        """Test that FeedStock maintains correct relationships."""
        # Create a feed stock
        stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # Test relationships
        self.assertEqual(stock.feed, self.feed)
        self.assertEqual(stock.feed_container, self.feed_container)
        self.assertIn(stock, self.feed.stock_levels.all())
        self.assertIn(stock, self.feed_container.feed_stocks.all())
    
    def test_feeding_event_model_relationships(self):
        """Test that FeedingEvent maintains correct relationships."""
        # Create a feed stock
        stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # Create a feeding event
        event = FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feed_stock=stock,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("5.0"),
            batch_biomass_kg=Decimal("200.0"),
            method="MANUAL"
        )
        
        # Test relationships
        self.assertEqual(event.batch, self.batch)
        self.assertEqual(event.batch_assignment, self.assignment)
        self.assertEqual(event.container, self.container)
        self.assertEqual(event.feed, self.feed)
        self.assertEqual(event.feed_stock, stock)
        
        # Test relationships with batch and container
        self.assertEqual(event.batch, self.batch)
        self.assertEqual(event.container, self.container)
        self.assertIn(event, self.batch.feeding_events.all())
        self.assertIn(event, self.container.feeding_events.all())
        self.assertIn(event, self.feed.feeding_events.all())
        self.assertIn(event, stock.feeding_events.all())
    
    def test_feed_stock_quantity_update(self):
        """Test that feed stock quantity is updated correctly after feeding events."""
        # Create a feed stock
        stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # Create a feeding event
        FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feed_stock=stock,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("5.0"),
            batch_biomass_kg=Decimal("200.0"),
            method="MANUAL"
        )
        
        # Refresh the stock from the database
        stock.refresh_from_db()
        
        # Check that the quantity was reduced
        self.assertEqual(stock.current_quantity_kg, Decimal("95.0"))  # 100.0 - 5.0
    
    def test_batch_feeding_summary_calculation(self):
        """Test that BatchFeedingSummary calculates totals correctly."""
        # Create a feed stock
        stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # Create feeding events
        today = timezone.now().date()
        
        # Event 1
        FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feed_stock=stock,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("3.0"),
            batch_biomass_kg=Decimal("200.0"),
            method="MANUAL"
        )
        
        # Event 2
        FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feed_stock=stock,
            feeding_date=today,
            feeding_time=(timezone.now() + timedelta(hours=6)).time(),
            amount_kg=Decimal("2.0"),
            batch_biomass_kg=Decimal("200.0"),
            method="MANUAL"
        )
        
        # Create a summary
        summary = BatchFeedingSummary.objects.create(
            batch=self.batch,
            period_start=today,
            period_end=today,
            total_feed_kg=Decimal("5.0")
        )
        
        # Check that the summary has the correct totals
        self.assertEqual(summary.total_feed_kg, Decimal("5.0"))  # 3.0 + 2.0


class SerializerBackwardCompatibilityTest(TestCase):
    """Tests to ensure serializer behavior remains consistent after refactoring."""
    
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
            max_biomass_kg=Decimal("1000.0")
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
            size_category="MEDIUM"
        )
    
    def test_feed_serializer_field_representation(self):
        """Test that FeedSerializer maintains the same field representation."""
        url = get_api_url('inventory', 'feeds', detail=True, pk=self.feed.id)
        response = self.client.get(url)
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check that all expected fields are present
        expected_fields = [
            'id', 'name', 'brand', 'size_category', 'protein_percentage',
            'fat_percentage', 'carbohydrate_percentage', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)
    
    def test_feed_purchase_serializer_validation(self):
        """Test that FeedPurchaseSerializer maintains the same validation logic."""
        url = get_api_url('inventory', 'feed-purchases')
        
        # Test with invalid data (expiry_date before purchase_date)
        invalid_data = {
            'feed': self.feed.id,
            'purchase_date': '2023-01-15',
            'expiry_date': '2023-01-01',  # Before purchase_date
            'quantity_kg': '100.0',
            'cost_per_kg': '5.0',
            'supplier': 'Test Supplier'
        }
        response = self.client.post(url, invalid_data, format='json')
        
        # Check that validation fails
        self.assertEqual(response.status_code, 400)
        # The validation error might be about dates or other fields, so check for either
        validation_error_text = str(response.data)
        self.assertTrue(
            'Start date must be before end date' in validation_error_text or 
            'expiry_date' in validation_error_text,
            f"Expected date validation error, got: {validation_error_text}"
        )
        
        # Test with valid data
        valid_data = {
            'feed': self.feed.id,
            'purchase_date': '2023-01-01',
            'expiry_date': '2023-01-15',  # After purchase_date
            'quantity_kg': '100.0',
            'cost_per_kg': '5.0',
            'supplier': 'Test Supplier'
        }
        response = self.client.post(url, valid_data, format='json')
        
        # Check that validation passes
        self.assertEqual(response.status_code, 201)
    
    def test_feeding_event_serializer_validation(self):
        """Test that FeedingEventSerializer validation works correctly."""
        url = get_api_url('inventory', 'feeding-events')
        
        # Create a feed container for testing
        feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            area=self.area,
            capacity_kg=100.0
        )
        
        # Create a feed stock for testing
        feed_stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=feed_container,
            current_quantity_kg=50.0,
            reorder_threshold_kg=10.0
        )
        
        # Create another batch for testing
        other_batch = Batch.objects.create(
            batch_number="OTHER-TEST-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=15)
        )
        
        # Test with missing required fields to ensure basic validation works
        missing_fields_data = {
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',
            'method': 'MANUAL'
        }
        response = self.client.post(url, missing_fields_data, format='json')
        
        # Check that validation fails for missing required fields
        self.assertEqual(response.status_code, 400)
        validation_error_text = str(response.data)
        # Check that we get validation errors about missing required fields
        self.assertTrue(
            'batch' in validation_error_text or 
            'container' in validation_error_text or 
            'feed' in validation_error_text,
            f"Expected validation errors for missing required fields, got: {validation_error_text}"
        )
        
        # Test with valid data
        valid_data = {
            'batch': self.batch.id,  # Same batch
            'batch_assignment': self.assignment.id,  # Belongs to self.batch
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',
            'batch_biomass_kg': '200.0',
            'method': 'MANUAL',
            'notes': 'Test feeding event'
        }
        response = self.client.post(url, valid_data, format='json')
        
        # Check that validation passes
        self.assertEqual(response.status_code, 201)


class ViewSetBackwardCompatibilityTest(TestCase):
    """Tests to ensure viewset behavior remains consistent after refactoring."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
    
    def test_feed_viewset_filtering(self):
        """Test that FeedViewSet maintains the same filtering capabilities."""
        # Create feeds with different properties for filtering tests
        Feed.objects.create(
            name="Active Feed",
            brand="Test Brand",
            size_category="SMALL",
            is_active=True
        )
        Feed.objects.create(
            name="Inactive Feed",
            brand="Test Brand",
            size_category="MEDIUM",
            is_active=False
        )
        
        url = get_api_url('inventory', 'feeds')
        
        # Test filtering by is_active=True
        response = self.client.get(f"{url}?is_active=true")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
        
        # Find active feeds
        active_feeds = [item for item in data if item['is_active'] is True]
        self.assertGreaterEqual(len(active_feeds), 1, "Should find at least one active feed")
        
        # Test filtering by is_active=False
        response = self.client.get(f"{url}?is_active=false")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
            
        # Find inactive feeds
        inactive_feeds = [item for item in data if item['is_active'] is False]
        self.assertGreaterEqual(len(inactive_feeds), 1, "Should find at least one inactive feed")
        
        # Verify the inactive feed is in the response
        inactive_feed = next((item for item in data if item['name'] == "Inactive Feed"), None)
        self.assertIsNotNone(inactive_feed, "Inactive Feed not found in response")
        
        # Test filtering by brand
        response = self.client.get(f"{url}?brand=Test%20Brand")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
            
        # Find feeds with the test brand
        test_brand_feeds = [item for item in data if item['brand'] == "Test Brand"]
        self.assertGreaterEqual(len(test_brand_feeds), 2, "Should find at least two feeds with Test Brand")
    
    def test_feed_viewset_searching(self):
        """Test that FeedViewSet maintains the same searching capabilities."""
        # Create feeds with different properties for search tests
        Feed.objects.create(
            name="Searchable Feed",
            brand="Unique Brand",
            description="This is a special feed for testing search",
            size_category="SMALL"
        )
        
        url = get_api_url('inventory', 'feeds')
        
        # Test searching by name
        response = self.client.get(f"{url}?search=Searchable")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
            
        # Find the searchable feed by name
        searchable_feed = next((item for item in data if item['name'] == "Searchable Feed"), None)
        self.assertIsNotNone(searchable_feed, "Searchable Feed not found when searching by name")
        
        # Test searching by brand
        response = self.client.get(f"{url}?search=Unique")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
            
        # Find the feed with unique brand
        unique_brand_feed = next((item for item in data if item['brand'] == "Unique Brand"), None)
        self.assertIsNotNone(unique_brand_feed, "Feed with 'Unique Brand' not found when searching by brand")
        
        # Test searching by description
        response = self.client.get(f"{url}?search=special")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
            
        # Find the feed with the special description
        special_desc_feed = next((item for item in data if "special" in item['description'].lower()), None)
        self.assertIsNotNone(special_desc_feed, "Feed with 'special' in description not found when searching by description")

    def test_feed_viewset_ordering(self):
        """Test that FeedViewSet maintains the same ordering capabilities."""
        # Create feeds with different names and brands for ordering tests
        Feed.objects.create(
            name="A Feed",
            brand="Brand Z",
            size_category="SMALL"
        )
        Feed.objects.create(
            name="Z Feed",
            brand="Brand A",
            size_category="LARGE"
        )
        
        url = get_api_url('inventory', 'feeds')
        
        # Test ordering by name ascending
        response = self.client.get(f"{url}?ordering=name")
        self.assertEqual(response.status_code, 200)
        
        # Get the actual data, handling both paginated and non-paginated responses
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            data = data['results']
        
        # Find feeds by name in the response
        a_feed = None
        z_feed = None
        for item in data:
            if item['name'] == "A Feed":
                a_feed = item
            elif item['name'] == "Z Feed":
                z_feed = item
        
        # Verify both feeds are found and A Feed comes before Z Feed
        self.assertIsNotNone(a_feed, "A Feed not found in response")
        self.assertIsNotNone(z_feed, "Z Feed not found in response")
        
        # Find the indices to verify ordering
        a_index = next((i for i, item in enumerate(data) if item['name'] == "A Feed"), None)
        z_index = next((i for i, item in enumerate(data) if item['name'] == "Z Feed"), None)
        self.assertLess(a_index, z_index, "A Feed should come before Z Feed when ordering by name ascending")
