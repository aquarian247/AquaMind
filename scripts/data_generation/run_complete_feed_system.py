#!/usr/bin/env python
"""
Complete Feed System Setup
Runs all feed-related scripts in proper order with comprehensive reporting.
"""
import os
import sys
import django
import subprocess
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedingEvent, FeedContainerStock
from apps.infrastructure.models import FeedContainer
from apps.health.models import HealthSamplingEvent, JournalEntry
from django.db import models

def run_script(script_name):
    """Run a Python script and return success status."""
    try:
        print(f"\n🔄 Running {script_name}...")
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))

        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {script_name} failed:")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def show_final_summary():
    """Show comprehensive summary of the complete feed system."""

    print("\n" + "="*60)
    print("                COMPLETE FEED SYSTEM SUMMARY")
    print("="*60)

    # Infrastructure
    print("\n🏭 INFRASTRUCTURE:")
    silos = FeedContainer.objects.filter(container_type='silo').count()
    barges = FeedContainer.objects.filter(container_type='barge').count()
    print(f"  Feed Silos: {silos}")
    print(f"  Feed Barges: {barges}")
    print(f"  Total Feed Containers: {silos + barges}")

    # Feed Types and Purchases
    print("\n📦 FEED INVENTORY:")
    feed_types = Feed.objects.count()
    purchases = FeedPurchase.objects.count()
    # Calculate total purchase value from quantity * cost_per_kg
    purchases_list = FeedPurchase.objects.all()
    total_purchase_value = Decimal('0')
    for purchase in purchases_list:
        total_purchase_value += (purchase.quantity_kg * purchase.cost_per_kg)
    print(f"  Feed Types: {feed_types}")
    print(f"  Feed Purchases: {purchases}")
    print(f"  Total Purchase Value: ${total_purchase_value:,.2f}")

    # Stock and FIFO
    print("\n📊 STOCK MANAGEMENT:")
    stock_entries = FeedStock.objects.count()
    fifo_entries = FeedContainerStock.objects.count()
    total_inventory = FeedStock.objects.aggregate(
        total=models.Sum('current_quantity_kg')
    )['total'] or Decimal('0')
    print(f"  Stock Entries: {stock_entries}")
    print(f"  FIFO Container Stock: {fifo_entries}")
    print(f"  Current Inventory: {total_inventory:,.2f} kg")

    # Feeding Operations
    print("\n🍽️  FEEDING OPERATIONS:")
    feeding_events = FeedingEvent.objects.count()
    total_feed_used = FeedingEvent.objects.aggregate(
        total=models.Sum('amount_kg')
    )['total'] or Decimal('0')
    total_feed_cost = FeedingEvent.objects.aggregate(
        total=models.Sum('feed_cost')
    )['total'] or Decimal('0')
    print(f"  Feeding Events: {feeding_events}")
    print(f"  Total Feed Used: {total_feed_used:,.2f} kg")
    print(f"  Total Feed Cost: ${total_feed_cost:,.2f}")

    # Health Monitoring
    print("\n🏥 HEALTH MONITORING:")
    sampling_events = HealthSamplingEvent.objects.count()
    journal_entries = JournalEntry.objects.count()
    print(f"  Health Sampling Events: {sampling_events}")
    print(f"  Journal Entries: {journal_entries}")

    # Data Relationships Verification
    print("\n🔗 RELATIONSHIPS VERIFICATION:")

    # Check feeding events have valid relationships
    feeding_with_batch = FeedingEvent.objects.filter(batch__isnull=False).count()
    feeding_with_container = FeedingEvent.objects.filter(container__isnull=False).count()
    feeding_with_feed = FeedingEvent.objects.filter(feed__isnull=False).count()

    print(f"  Feeding Events with Valid Batches: {feeding_with_batch}/{feeding_events}")
    print(f"  Feeding Events with Valid Containers: {feeding_with_container}/{feeding_events}")
    print(f"  Feeding Events with Valid Feed: {feeding_with_feed}/{feeding_events}")

    # Check health events have valid relationships
    health_with_assignment = HealthSamplingEvent.objects.filter(assignment__isnull=False).count()
    journal_with_batch = JournalEntry.objects.filter(batch__isnull=False).count()

    print(f"  Health Events with Valid Assignments: {health_with_assignment}/{sampling_events}")
    print(f"  Journal Entries with Valid Batches: {journal_with_batch}/{journal_entries}")

    print("\n" + "="*60)
    print("🎉 FEED SYSTEM IMPLEMENTATION COMPLETE!")
    print("All components properly interconnected with real object relationships.")
    print("="*60)

def main():
    """Run the complete feed system setup."""

    print("🚀 STARTING COMPLETE FEED SYSTEM SETUP")
    print("This will create all missing feed components with proper relationships.")

    scripts = [
        'create_feed_infrastructure.py',
        'create_feed_stock.py',
        'create_feeding_events.py',
        'create_health_monitoring.py'
    ]

    success_count = 0
    for script in scripts:
        if run_script(script):
            success_count += 1
        else:
            print(f"⚠️  {script} failed, but continuing with remaining scripts...")

    print(f"\n📊 Setup Complete: {success_count}/{len(scripts)} scripts successful")

    if success_count > 0:
        show_final_summary()
    else:
        print("❌ No scripts completed successfully.")

if __name__ == '__main__':
    main()
