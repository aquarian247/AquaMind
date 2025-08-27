#!/usr/bin/env python
"""
Create Feeding Events
Generates historical feeding events tied to real batches, containers, and feed stock.
"""
import os
import sys
import django
import random
from decimal import Decimal
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedingEvent, FeedContainerStock
from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container
from django.contrib.auth import get_user_model

User = get_user_model()

def create_feeding_events():
    """
    Create feeding events tied to real objects.

    This function is rerunnable - it will only create feeding events for dates that don't
    already have events for the same batch/container/date combination.
    """

    print("=== CREATING FEEDING EVENTS ===")

    # Check existing feeding events
    existing_feeding_count = FeedingEvent.objects.count()
    print(f"📊 Existing feeding events: {existing_feeding_count}")

    # Get active batches and their assignments
    active_assignments = BatchContainerAssignment.objects.filter(
        departure_date__isnull=True
    ).select_related('batch', 'container')

    if not active_assignments.exists():
        print("❌ No active batch assignments found.")
        return 0

    # Get feed stock for feeding
    feed_stocks = FeedStock.objects.filter(current_quantity_kg__gt=0).select_related('feed')
    if not feed_stocks.exists():
        print("❌ No feed stock available. Run create_feed_stock.py first.")
        return 0

    # Get or create system user for feeding events
    system_user, _ = User.objects.get_or_create(
        username='feeding_system',
        defaults={'email': 'feeding@aquamind.com', 'first_name': 'Feeding', 'last_name': 'System'}
    )

    feeding_count = 0

    # Use assignment date range for substantial data generation (2 years)
    assignments_all = BatchContainerAssignment.objects.filter(departure_date__isnull=True)
    if assignments_all.exists():
        assignment_dates = list(assignments_all.values_list('assignment_date', flat=True))
        start_date = min(assignment_dates)
        # Process 2 years of data for substantial transaction volumes
        end_date = min(start_date + timedelta(days=730), max(assignment_dates))
    else:
        # Fallback to original range if no assignments
        start_date = date(2015, 1, 1)
        end_date = date(2018, 1, 15)

    print(f"📅 Processing date range: {start_date} to {end_date}")

    current_date = start_date
    while current_date <= end_date:
        # Process each active assignment on this date
        for assignment in active_assignments:
            if assignment.assignment_date <= current_date:
                # Check if feeding event already exists for this assignment and date
                if not FeedingEvent.objects.filter(
                    batch_assignment=assignment,
                    feeding_date=current_date
                ).exists():
                    # Random feeding event (70% chance per day for active assignments)
                    if random.random() < 0.7:
                        # Select random feed stock
                        feed_stock = random.choice(feed_stocks)

                        # Calculate feeding amount based on batch size and TGC
                        batch_size = assignment.batch.calculated_population_count or 1000

                        # More realistic feeding calculation:
                        # For large batches, feeding amount should be based on biomass, not population count
                        # Assume average weight of 100g per fish, so biomass = population * 0.1 kg
                        estimated_biomass_kg = batch_size * Decimal('0.1')  # 100g per fish average
                        feeding_amount = min(
                            estimated_biomass_kg * Decimal('0.02'),  # 2% of biomass
                            feed_stock.feed_container.capacity_kg * Decimal('0.05')   # Max 5% of container capacity
                        )

                        # Check if we have enough stock
                        if feed_stock.current_quantity_kg >= feeding_amount:
                            # Create feeding event
                            feeding_event = FeedingEvent.objects.create(
                                batch=assignment.batch,
                                container=assignment.container,
                                batch_assignment=assignment,
                                feed=feed_stock.feed,
                                feed_stock=feed_stock,
                                recorded_by=system_user,
                                feeding_date=current_date,
                                feeding_time=f"{random.randint(8, 16):02d}:{random.randint(0, 59):02d}:00",
                                amount_kg=feeding_amount,
                                batch_biomass_kg=Decimal(str(batch_size)),
                                feeding_percentage=Decimal('2.0'),  # 2% of biomass
                                feed_cost=feeding_amount * Decimal('2.50'),  # Average cost/kg
                                method='automatic_feeder',
                                notes=f"Automated feeding for {assignment.batch.batch_number}"
                            )

                            # Update feed stock (consume the feed)
                            feed_stock.current_quantity_kg -= feeding_amount
                            feed_stock.save()

                            # Update container stock using FIFO
                            container_stocks = FeedContainerStock.objects.filter(
                                feed_container=feed_stock.feed_container,
                                feed_purchase__feed=feed_stock.feed
                            ).order_by('entry_date')  # FIFO

                            remaining_to_consume = feeding_amount
                            for container_stock in container_stocks:
                                if remaining_to_consume <= 0:
                                    break

                                if container_stock.quantity_kg > 0:
                                    consume_amount = min(remaining_to_consume, container_stock.quantity_kg)
                                    container_stock.quantity_kg -= consume_amount
                                    container_stock.save()
                                    remaining_to_consume -= consume_amount

                            feeding_count += 1

                            if feeding_count % 1000 == 0:
                                print(f"  Created {feeding_count} feeding events...")

        current_date += timedelta(days=1)

    print(f"✅ Created {feeding_count} new feeding events")

    if feeding_count == 0:
        print("📊 No new feeding events created - all dates already have events")
    else:
        print(f"📅 Date range: {start_date} to {end_date}")
        print("📊 Daily feeding probability: 70% for active batches")

    # Show final summary statistics (includes existing + new)
    final_feeding_count = FeedingEvent.objects.count()
    total_feed_used = FeedingEvent.objects.aggregate(
        total=models.Sum('amount_kg')
    )['total'] or Decimal('0')

    total_cost = FeedingEvent.objects.aggregate(
        total=models.Sum('feed_cost')
    )['total'] or Decimal('0')

    print("\n=== FEEDING SYSTEM SUMMARY ===")
    print(f"Total feeding events: {final_feeding_count}")
    print(f"Total feed used: {total_feed_used:,.2f} kg")
    print(f"Total feed cost: ${total_cost:,.2f}")

    return feeding_count

if __name__ == '__main__':
    from django.db import models
    create_feeding_events()
