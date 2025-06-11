"""
FIFO Feed Inventory Service

Handles First-In-First-Out feed inventory tracking and cost calculations.
"""
from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from typing import List, Tuple, Optional

from apps.inventory.models import (
    FeedContainerStock, FeedingEvent, FeedPurchase
)
from apps.infrastructure.models import FeedContainer

class InsufficientStockError(ValueError):
    """Exception raised when there's insufficient stock for an operation."""
    pass

class FIFOInventoryService:
    """Service for managing FIFO feed inventory operations."""
    
    @classmethod
    def add_feed_to_container(
        cls, 
        feed_container: FeedContainer,
        feed_purchase: FeedPurchase,
        quantity_kg: Decimal,
        entry_date: Optional[timezone.datetime] = None
    ) -> FeedContainerStock:
        """
        Add feed from a purchase batch to a container.
        
        Args:
            feed_container: Container to add feed to
            feed_purchase: Purchase batch the feed comes from
            quantity_kg: Amount of feed to add
            entry_date: When the feed was added (defaults to now)
            
        Returns:
            FeedContainerStock: The created stock record
            
        Raises:
            ValueError: If quantity exceeds available purchase quantity
        """
        if entry_date is None:
            entry_date = timezone.now()
            
        # Validate quantity doesn't exceed available purchase
        available_qty = cls.get_available_purchase_quantity(feed_purchase)
        if quantity_kg > available_qty:
            raise InsufficientStockError(
                f"Cannot add {quantity_kg}kg - only {available_qty}kg available "
                f"from purchase batch {feed_purchase.batch_number}"
            )
        
        with transaction.atomic():
            stock = FeedContainerStock.objects.create(
                feed_container=feed_container,
                feed_purchase=feed_purchase,
                quantity_kg=quantity_kg,
                entry_date=entry_date
            )
            
        return stock
    
    @classmethod
    def consume_feed_fifo(
        cls,
        feed_container: FeedContainer,
        quantity_kg: Decimal,
        feeding_event: Optional[FeedingEvent] = None
    ) -> Tuple[Decimal, List[dict]]:
        """
        Consume feed from container using FIFO method and calculate cost.
        
        Args:
            feed_container: Container to consume feed from
            quantity_kg: Amount of feed to consume
            feeding_event: Optional feeding event to update with cost
            
        Returns:
            Tuple[Decimal, List[dict]]: Total cost and list of consumed batches
            
        Raises:
            InsufficientStockError: If not enough feed available
        """
        # Get available stock in FIFO order
        available_stocks = FeedContainerStock.objects.filter(
            feed_container=feed_container,
            quantity_kg__gt=0
        ).order_by('entry_date')
        
        # Check if enough feed is available
        total_available = sum(stock.quantity_kg for stock in available_stocks)
        if quantity_kg > total_available:
            raise InsufficientStockError(
                f"Insufficient feed in {feed_container.name}. "
                f"Requested: {quantity_kg}kg, Available: {total_available}kg"
            )
        
        total_cost = Decimal('0.00')
        remaining_to_consume = quantity_kg
        consumed_batches = []
        
        with transaction.atomic():
            for stock in available_stocks:
                if remaining_to_consume <= 0:
                    break
                    
                # Calculate how much to consume from this stock
                consume_from_stock = min(remaining_to_consume, stock.quantity_kg)
                
                # Calculate cost for this portion
                cost_per_kg = stock.feed_purchase.cost_per_kg
                portion_cost = consume_from_stock * cost_per_kg
                total_cost += portion_cost
                
                # Record consumed batch info
                consumed_batches.append({
                    'feed_purchase': stock.feed_purchase,
                    'quantity_consumed': consume_from_stock,
                    'cost_per_kg': cost_per_kg,
                    'total_cost': portion_cost
                })
                
                # Update stock quantity
                stock.quantity_kg -= consume_from_stock
                if stock.quantity_kg == 0:
                    stock.delete()  # Remove depleted stock
                else:
                    stock.save()
                
                remaining_to_consume -= consume_from_stock
        
        # Update feeding event with calculated cost if provided
        if feeding_event:
            feeding_event.feed_cost = total_cost
            feeding_event.save(update_fields=['feed_cost'])
        
        return total_cost, consumed_batches
    
    @classmethod
    def get_available_purchase_quantity(cls, feed_purchase: FeedPurchase) -> Decimal:
        """
        Get the remaining quantity available from a feed purchase.
        
        Args:
            feed_purchase: The purchase to check
            
        Returns:
            Decimal: Available quantity in kg
        """
        allocated_qty = FeedContainerStock.objects.filter(
            feed_purchase=feed_purchase
        ).aggregate(
            total=models.Sum('quantity_kg')
        )['total'] or Decimal('0')
        
        return feed_purchase.quantity_kg - allocated_qty
    
    @classmethod
    def get_container_stock_summary(
        cls, 
        feed_container: FeedContainer
    ) -> List[dict]:
        """
        Get a summary of feed stock in a container by purchase batch.
        
        Args:
            feed_container: Container to summarize
            
        Returns:
            List[dict]: Summary with batch info, quantities, and costs
        """
        stocks = FeedContainerStock.objects.filter(
            feed_container=feed_container,
            quantity_kg__gt=0
        ).select_related('feed_purchase__feed').order_by('entry_date')
        
        summary = []
        for stock in stocks:
            purchase = stock.feed_purchase
            summary.append({
                'purchase_id': purchase.id,
                'batch_number': purchase.batch_number,
                'feed_name': purchase.feed.name,
                'quantity_kg': stock.quantity_kg,
                'cost_per_kg': purchase.cost_per_kg,
                'total_value': stock.quantity_kg * purchase.cost_per_kg,
                'entry_date': stock.entry_date,
                'supplier': purchase.supplier,
                'expiry_date': purchase.expiry_date
            })
        
        return summary
    
    @classmethod
    def get_container_stock_fifo_order(cls, container_id: int) -> List[FeedContainerStock]:
        """
        Get feed container stock in FIFO order.
        
        Args:
            container_id: ID of the container
            
        Returns:
            List[FeedContainerStock]: Stock entries in FIFO order
        """
        return FeedContainerStock.objects.filter(
            feed_container_id=container_id,
            quantity_kg__gt=0
        ).select_related('feed_purchase__feed').order_by('feed_purchase__purchase_date', 'entry_date')
    
    @classmethod
    def get_total_container_stock(cls, feed_container: FeedContainer) -> Decimal:
        """
        Get total stock quantity in a container.
        
        Args:
            feed_container: Container to check
            
        Returns:
            Decimal: Total quantity in kg
        """
        total = FeedContainerStock.objects.filter(
            feed_container=feed_container,
            quantity_kg__gt=0
        ).aggregate(
            total=models.Sum('quantity_kg')
        )['total'] or Decimal('0')
        
        return total
    
    @classmethod
    def get_container_stock_value(cls, feed_container: FeedContainer) -> Decimal:
        """
        Get total value of stock in a container.
        
        Args:
            feed_container: Container to check
            
        Returns:
            Decimal: Total value
        """
        stocks = FeedContainerStock.objects.filter(
            feed_container=feed_container,
            quantity_kg__gt=0
        ).select_related('feed_purchase')
        
        total_value = Decimal('0.00')
        for stock in stocks:
            total_value += stock.quantity_kg * stock.feed_purchase.cost_per_kg
        
        return total_value 