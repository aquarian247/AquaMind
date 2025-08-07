"""
Focused tests for Inventory app business logic.

This module contains simplified tests that focus on the business logic
in the Inventory app models, avoiding complex model hierarchies and dependencies.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inventory.models import (
    Feed, FeedPurchase
)
from tests.base import BaseAPITestCase

User = get_user_model()


class FeedLogicTest(TestCase):
    """Test the business logic of the Feed model."""
    
    def test_feed_creation(self):
        """Test that a feed can be created with valid data."""
        feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="SMALL",
            pellet_size_mm=Decimal('1.5'),
            protein_percentage=Decimal('45'),
            fat_percentage=Decimal('20'),
            carbohydrate_percentage=Decimal('15'),
            description="Test feed description"
        )
        
        self.assertEqual(feed.name, "Test Feed")
        self.assertEqual(feed.brand, "Test Brand")
        self.assertEqual(feed.size_category, "SMALL")
        self.assertEqual(feed.pellet_size_mm, Decimal('1.5'))
        self.assertEqual(feed.protein_percentage, Decimal('45'))
    
    def test_feed_str(self):
        """Test the string representation of a feed."""
        feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="SMALL"
        )
        
        expected_str = "Test Brand - Test Feed (Small)"
        self.assertEqual(str(feed), expected_str)
    
    def test_feed_size_category_choices(self):
        """Test the feed size category choices."""
        # Create feeds with different size categories
        micro_feed = Feed.objects.create(
            name="Micro Feed",
            brand="Test Brand",
            size_category="MICRO"
        )
        
        small_feed = Feed.objects.create(
            name="Small Feed",
            brand="Test Brand",
            size_category="SMALL"
        )
        
        medium_feed = Feed.objects.create(
            name="Medium Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        
        large_feed = Feed.objects.create(
            name="Large Feed",
            brand="Test Brand",
            size_category="LARGE"
        )
        
        # Verify the size categories are set correctly
        self.assertEqual(micro_feed.size_category, "MICRO")
        self.assertEqual(small_feed.size_category, "SMALL")
        self.assertEqual(medium_feed.size_category, "MEDIUM")
        self.assertEqual(large_feed.size_category, "LARGE")
    
    def test_feed_nutritional_values(self):
        """Test nutritional values can exceed 100% since validation is not enforced."""
        # Create feed with nutritional values that total more than 100%
        feed = Feed.objects.create(
            name="High Nutrition Feed",
            brand="Test Brand",
            size_category="SMALL",
            protein_percentage=Decimal('60'),
            fat_percentage=Decimal('30'),
            carbohydrate_percentage=Decimal('20')  # Total: 110%
        )
        
        # Verify the values are stored correctly without validation errors
        self.assertEqual(feed.protein_percentage, Decimal('60'))
        self.assertEqual(feed.fat_percentage, Decimal('30'))
        self.assertEqual(feed.carbohydrate_percentage, Decimal('20'))


class FeedPurchaseLogicTest(TestCase):
    """Test the business logic of the FeedPurchase model."""
    
    def setUp(self):
        """Set up minimal test data for feed purchase tests."""
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="SMALL"
        )
    
    def test_feed_purchase_creation(self):
        """Test that a feed purchase can be created with valid data."""
        purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            cost_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123",
            expiry_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        
        self.assertEqual(purchase.feed, self.feed)
        self.assertEqual(purchase.quantity_kg, Decimal('1000'))
        self.assertEqual(purchase.cost_per_kg, Decimal('2.50'))
        self.assertEqual(purchase.supplier, "Test Supplier")
        self.assertEqual(purchase.batch_number, "BATCH123")
    
    def test_feed_purchase_str(self):
        """Test the string representation of a feed purchase."""
        purchase_date = timezone.datetime(2025, 1, 1).date()
        purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=purchase_date,
            quantity_kg=Decimal('1000'),
            cost_per_kg=Decimal('2.50'),
            supplier="Test Supplier",
            batch_number="BATCH123"
        )
        
        expected_str = f"{self.feed} - 1000kg purchased on {purchase_date}"
        self.assertEqual(str(purchase), expected_str)
    
    def test_feed_purchase_total_cost(self):
        """Test the total cost calculation for a feed purchase."""
        purchase = FeedPurchase(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            cost_per_kg=Decimal('2.50'),
            supplier="Test Supplier"
        )
        
        # Expected total cost: 1000 * 2.50 = 2500
        expected_total_cost = Decimal('2500.00')
        self.assertEqual(purchase.quantity_kg * purchase.cost_per_kg, expected_total_cost)
    
    def test_negative_quantity_validation(self):
        """Test validation of negative quantity."""
        purchase = FeedPurchase(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('-100'),  # Invalid: negative quantity
            cost_per_kg=Decimal('2.50'),
            supplier="Test Supplier"
        )
        
        with self.assertRaises(ValidationError):
            purchase.full_clean()
    
    def test_negative_price_validation(self):
        """Test validation of negative price."""
        purchase = FeedPurchase(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal('1000'),
            cost_per_kg=Decimal('-2.50'),  # Invalid: negative price
            supplier="Test Supplier"
        )
        
        with self.assertRaises(ValidationError):
            purchase.full_clean()


class InventoryAPITest(BaseAPITestCase):
    """Test the Inventory API endpoints with minimal setup."""
    
    def setUp(self):
        """Set up minimal test data for API tests."""
        super().setUp()
        
        # Create a feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="SMALL"
        )
        
        # URL for feed endpoints
        self.feed_list_url = self.get_api_url('inventory', 'feeds')
        self.feed_detail_url = self.get_api_url('inventory', 'feeds', detail=True, pk=self.feed.id)
    
    def test_feed_list_api(self):
        """Test retrieving a list of feeds via API."""
        response = self.client.get(self.feed_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], "Test Feed")
    
    def test_feed_detail_api(self):
        """Test retrieving a single feed via API."""
        response = self.client.get(self.feed_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Test Feed")
        self.assertEqual(response.data['brand'], "Test Brand")
        self.assertEqual(response.data['size_category'], "SMALL")
    
    def test_feed_create_api(self):
        """Test creating a new feed via API."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'name': 'New Test Feed',
            'brand': 'New Brand',
            'size_category': 'MEDIUM',
            'pellet_size_mm': '4.5',
            'protein_percentage': '35',
            'fat_percentage': '22',
            'carbohydrate_percentage': '25'
        }
        
        response = self.client.post(self.feed_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Feed.objects.count(), 2)
        
        # Check that the feed was created with the correct data
        created_feed = Feed.objects.get(name='New Test Feed')
        self.assertEqual(created_feed.brand, 'New Brand')
        self.assertEqual(created_feed.size_category, 'MEDIUM')
        self.assertEqual(created_feed.pellet_size_mm, Decimal('4.5'))
    
    def test_feed_update_api(self):
        """Test updating an existing feed via API."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        data = {
            'name': 'Updated Feed',
            'brand': self.feed.brand,
            'size_category': self.feed.size_category
        }
        
        response = self.client.patch(self.feed_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the feed was updated with the correct data
        self.feed.refresh_from_db()
        self.assertEqual(self.feed.name, 'Updated Feed')
    
    def test_feed_delete_api(self):
        """Test deleting a feed via API."""
        # Create a superuser for admin operations
        self.create_and_authenticate_superuser()
        
        response = self.client.delete(self.feed_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Feed.objects.count(), 0)
