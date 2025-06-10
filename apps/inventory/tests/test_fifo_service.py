"""
Tests for FIFO Inventory Service.

This module tests the First-In-First-Out feed inventory tracking functionality.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta

from apps.inventory.models import (
    Feed, FeedPurchase, FeedContainerStock, FeedingEvent
)
from apps.infrastructure.models import FeedContainer, ContainerType, Hall, Geography, FreshwaterStation
from apps.batch.models import Batch, Species, LifeCycleStage
from apps.inventory.services import FIFOInventoryService
from apps.core.exceptions import InsufficientStockError


class FIFOInventoryServiceTest(TestCase):
    """Test cases for FIFO Inventory Service."""
    
    def setUp(self):
        """Set up test data."""
        # Create geography
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography for FIFO testing"
        )
        
        # Create freshwater station
        self.freshwater_station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=Decimal("10.123456"),
            longitude=Decimal("20.123456"),
            description="Test station for FIFO testing"
        )
        
        # Create hall
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.freshwater_station
        )
        
        # Create container type
        self.container_type = ContainerType.objects.create(
            name="Feed Container",
            category="OTHER",
            max_volume_m3=Decimal("100.00")
        )
        
        # Create feed container
        self.feed_container = FeedContainer.objects.create(
            name="Feed Container 1",
            container_type="SILO",
            hall=self.hall,
            capacity_kg=Decimal("1000.00")
        )
        
        # Create feed
        self.feed = Feed.objects.create(
            name="Premium Salmon Feed",
            brand="AquaFeed",
            size_category="MEDIUM",
            protein_percentage=Decimal("45.0"),
            fat_percentage=Decimal("20.0")
        )
        
        # Create feed purchases (different dates for FIFO testing)
        self.purchase1 = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=date.today() - timedelta(days=10),
            quantity_kg=Decimal("500.00"),
            cost_per_kg=Decimal("2.50"),
            batch_number="BATCH001"
        )
        
        self.purchase2 = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=date.today() - timedelta(days=5),
            quantity_kg=Decimal("300.00"),
            cost_per_kg=Decimal("2.75"),
            batch_number="BATCH002"
        )
        
        self.purchase3 = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=date.today() - timedelta(days=2),
            quantity_kg=Decimal("400.00"),
            cost_per_kg=Decimal("2.60"),
            batch_number="BATCH003"
        )
        
        # Create batch for feeding events
        self.species = Species.objects.create(name="Atlantic Salmon")
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100)
        )
    
    def test_add_feed_to_container(self):
        """Test adding feed to container."""
        # Add feed from first purchase
        stock_entry = FIFOInventoryService.add_feed_to_container(
            feed_container=self.feed_container,
            feed_purchase=self.purchase1,
            quantity_kg=Decimal("200.00")
        )
        
        self.assertEqual(stock_entry.feed_container, self.feed_container)
        self.assertEqual(stock_entry.feed_purchase, self.purchase1)
        self.assertEqual(stock_entry.quantity_kg, Decimal("200.00"))
        self.assertIsNotNone(stock_entry.entry_date)
    
    def test_add_feed_insufficient_stock(self):
        """Test adding more feed than available in purchase."""
        with self.assertRaises(InsufficientStockError):
            FIFOInventoryService.add_feed_to_container(
                feed_container=self.feed_container,
                feed_purchase=self.purchase1,
                quantity_kg=Decimal("600.00")  # More than the 500kg available
            )
    
    def test_get_container_stock_fifo_order(self):
        """Test getting container stock in FIFO order."""
        # Add feeds in different order
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase2, Decimal("100.00")
        )
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("150.00")
        )
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase3, Decimal("200.00")
        )
        
        # Get FIFO order
        fifo_stock = FIFOInventoryService.get_container_stock_fifo_order(
            self.feed_container.id
        )
        
        # Should be ordered by purchase date (oldest first)
        self.assertEqual(len(fifo_stock), 3)
        self.assertEqual(fifo_stock[0].feed_purchase, self.purchase1)  # Oldest
        self.assertEqual(fifo_stock[1].feed_purchase, self.purchase2)
        self.assertEqual(fifo_stock[2].feed_purchase, self.purchase3)  # Newest
    
    def test_consume_feed_fifo_single_batch(self):
        """Test consuming feed from a single batch."""
        # Add feed to container
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("200.00")
        )
        
        # Consume some feed
        cost, consumed_batches = FIFOInventoryService.consume_feed_fifo(
            feed_container=self.feed_container,
            quantity_kg=Decimal("50.00")
        )
        
        # Check cost calculation
        expected_cost = Decimal("50.00") * self.purchase1.cost_per_kg
        self.assertEqual(cost, expected_cost)
        
        # Check consumed batches
        self.assertEqual(len(consumed_batches), 1)
        self.assertEqual(consumed_batches[0]['feed_purchase'], self.purchase1)
        self.assertEqual(consumed_batches[0]['quantity_consumed'], Decimal("50.00"))
        
        # Check remaining stock
        remaining_stock = FeedContainerStock.objects.get(
            feed_container=self.feed_container,
            feed_purchase=self.purchase1
        )
        self.assertEqual(remaining_stock.quantity_kg, Decimal("150.00"))
    
    def test_consume_feed_fifo_multiple_batches(self):
        """Test consuming feed across multiple batches."""
        # Add feeds to container
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("100.00")
        )
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase2, Decimal("150.00")
        )
        
        # Consume more than first batch
        cost, consumed_batches = FIFOInventoryService.consume_feed_fifo(
            feed_container=self.feed_container,
            quantity_kg=Decimal("180.00")
        )
        
        # Check cost calculation (100kg from batch1 + 80kg from batch2)
        expected_cost = (
            Decimal("100.00") * self.purchase1.cost_per_kg +
            Decimal("80.00") * self.purchase2.cost_per_kg
        )
        self.assertEqual(cost, expected_cost)
        
        # Check consumed batches
        self.assertEqual(len(consumed_batches), 2)
        
        # First batch should be completely consumed
        batch1_consumed = next(
            b for b in consumed_batches 
            if b['feed_purchase'] == self.purchase1
        )
        self.assertEqual(batch1_consumed['quantity_consumed'], Decimal("100.00"))
        
        # Second batch should be partially consumed
        batch2_consumed = next(
            b for b in consumed_batches 
            if b['feed_purchase'] == self.purchase2
        )
        self.assertEqual(batch2_consumed['quantity_consumed'], Decimal("80.00"))
        
        # Check remaining stock
        # First batch should be deleted (fully consumed)
        self.assertFalse(
            FeedContainerStock.objects.filter(
                feed_container=self.feed_container,
                feed_purchase=self.purchase1
            ).exists()
        )
        
        # Second batch should have remaining stock
        remaining_stock = FeedContainerStock.objects.get(
            feed_container=self.feed_container,
            feed_purchase=self.purchase2
        )
        self.assertEqual(remaining_stock.quantity_kg, Decimal("70.00"))
    
    def test_consume_feed_insufficient_stock(self):
        """Test consuming more feed than available."""
        # Add limited feed to container
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("100.00")
        )
        
        # Try to consume more than available
        with self.assertRaises(InsufficientStockError):
            FIFOInventoryService.consume_feed_fifo(
                feed_container=self.feed_container,
                quantity_kg=Decimal("150.00")
            )
    
    def test_get_total_container_stock(self):
        """Test getting total stock in container."""
        # Add feeds to container
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("100.00")
        )
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase2, Decimal("150.00")
        )
        
        total_stock = FIFOInventoryService.get_total_container_stock(
            self.feed_container
        )
        
        self.assertEqual(total_stock, Decimal("250.00"))
    
    def test_get_container_stock_value(self):
        """Test getting total value of stock in container."""
        # Add feeds to container
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase1, Decimal("100.00")
        )
        FIFOInventoryService.add_feed_to_container(
            self.feed_container, self.purchase2, Decimal("150.00")
        )
        
        total_value = FIFOInventoryService.get_container_stock_value(
            self.feed_container
        )
        
        expected_value = (
            Decimal("100.00") * self.purchase1.cost_per_kg +
            Decimal("150.00") * self.purchase2.cost_per_kg
        )
        self.assertEqual(total_value, expected_value) 