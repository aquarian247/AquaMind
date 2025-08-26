#!/usr/bin/env python
"""
Create Feed Stock and FIFO Inventory
Creates feed stock entries and container stock tracking for proper FIFO management.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedContainerStock
from apps.infrastructure.models import FeedContainer
from django.db import models

def create_feed_stock():
    """
    Create feed stock entries and container stock for FIFO management.

    This function is rerunnable - it will only create stock for containers that don't
    already have feed stock entries, ensuring no duplicate data.
    """

    print("=== CREATING FEED STOCK AND FIFO INVENTORY ===")

    # Get existing feed containers
    feed_containers = FeedContainer.objects.all()
    if not feed_containers.exists():
        print("❌ No feed containers found. Run create_feed_infrastructure.py first.")
        return 0

    # Get existing feed purchases
    feed_purchases = FeedPurchase.objects.all()
    if not feed_purchases.exists():
        print("❌ No feed purchases found. Need feed purchases for stock tracking.")
        return 0

    # Check existing stock
    existing_stock_count = FeedStock.objects.count()
    existing_container_stock_count = FeedContainerStock.objects.count()
    print(f"📊 Existing feed stock entries: {existing_stock_count}")
    print(f"📊 Existing container stock entries: {existing_container_stock_count}")

    stock_count = 0
    container_stock_count = 0

    # Create feed stock entries only for containers without stock
    containers_needing_stock = []
    for container in feed_containers:
        if not FeedStock.objects.filter(feed_container=container).exists():
            containers_needing_stock.append(container)

    if not containers_needing_stock:
        print("📊 All containers already have feed stock - no new stock created")
        # Still show current inventory status
        total_inventory = FeedStock.objects.aggregate(
            total=models.Sum('current_quantity_kg')
        )['total'] or Decimal('0')

        print(f"📊 Current total inventory: {total_inventory:,.2f} kg")
        return 0

    print(f"📊 Creating stock for {len(containers_needing_stock)} containers...")

    # Create feed stock entries (current inventory levels)
    for container in containers_needing_stock:
        # Get relevant feed purchases (use different subsets for variety)
        purchase_start_idx = (container.id % len(feed_purchases))  # Start at different point for each container
        container_purchases = feed_purchases[purchase_start_idx:purchase_start_idx + 5]  # Use 5 purchases

        if not container_purchases:
            container_purchases = feed_purchases[:5]  # Fallback to first 5

        # Calculate total stock for this container
        total_stock = Decimal('0')
        reorder_threshold = container.capacity_kg * Decimal('0.2')  # 20% of capacity

        for purchase in container_purchases:
            # Check if container stock already exists (extra safety for rerunnability)
            if not FeedContainerStock.objects.filter(
                feed_container=container,
                feed_purchase=purchase
            ).exists():
                # Create container stock entry (FIFO tracking)
                container_stock = FeedContainerStock.objects.create(
                    feed_container=container,
                    feed_purchase=purchase,
                    quantity_kg=min(
                        purchase.quantity_kg * Decimal('0.1'),
                        container.capacity_kg * Decimal('0.05')
                    ),
                    entry_date=purchase.purchase_date
                )
                total_stock += container_stock.quantity_kg
                container_stock_count += 1

        # Create feed stock entry for current inventory level
        feed_stock, created = FeedStock.objects.get_or_create(
            feed=container_purchases[0].feed,  # Use first feed type for this container
            feed_container=container,
            defaults={
                'current_quantity_kg': total_stock,
                'reorder_threshold_kg': reorder_threshold,
                'notes': f"Initial stock for {container.name}"
            }
        )

        if created:
            stock_count += 1
            # Update container current stock
            container.current_stock_kg = total_stock
            container.save()
        else:
            print(f"⏭️  Feed stock already exists for {container.name}")

    print(f"✅ Created {stock_count} new feed stock entries")
    print(f"✅ Created {container_stock_count} new container stock entries (FIFO tracking)")

    # Verify final inventory totals
    total_inventory = FeedStock.objects.aggregate(
        total=models.Sum('current_quantity_kg')
    )['total'] or Decimal('0')

    print(f"📊 Total inventory across all containers: {total_inventory:,.2f} kg")

    # Show inventory by container type
    silo_inventory = FeedStock.objects.filter(
        feed_container__container_type='silo'
    ).aggregate(total=models.Sum('current_quantity_kg'))['total'] or Decimal('0')

    barge_inventory = FeedStock.objects.filter(
        feed_container__container_type='barge'
    ).aggregate(total=models.Sum('current_quantity_kg'))['total'] or Decimal('0')

    print(f"   Silo inventory: {silo_inventory:,.2f} kg")
    print(f"   Barge inventory: {barge_inventory:,.2f} kg")

    return stock_count

if __name__ == '__main__':
    create_feed_stock()
