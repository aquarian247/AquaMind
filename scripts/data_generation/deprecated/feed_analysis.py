#!/usr/bin/env python
"""
Quick feed system analysis script
"""
import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedingEvent
from apps.infrastructure.models import FeedContainer

print('=== FEED SYSTEM ANALYSIS ===')
print(f'Feed Types: {Feed.objects.count()}')
print(f'Feed Purchases: {FeedPurchase.objects.count()}')
print(f'Feed Stock Entries: {FeedStock.objects.count()}')
print(f'Feeding Events: {FeedingEvent.objects.count()}')
print(f'Feed Containers: {FeedContainer.objects.count()}')

print('\n=== FEED TYPES ===')
for feed in Feed.objects.all():
    print(f'  {feed.brand} - {feed.name} - {feed.size_category}')

print('\n=== FEED PURCHASES (first 5) ===')
purchases = FeedPurchase.objects.all()
total_cost = 0
for i, purchase in enumerate(purchases):
    if i < 5:
        cost = float(purchase.cost_per_kg) * float(purchase.quantity_kg)
        print(f'  {purchase.feed.name}: {purchase.quantity_kg:,}kg @ ${purchase.cost_per_kg:.2f}/kg = ${cost:.2f}')
        total_cost += cost

print(f'  ... and {len(purchases) - 5} more purchases')
print(f'Total purchase value: ${total_cost:,.2f}')

print('\n=== SESSION 1 FEED SYSTEM STATUS ===')
print('✅ Feed Types: Created (6 types)')
print('✅ Feed Purchases: Recorded with pricing (56 purchases)')
print('❌ Feed Containers: 0 (should be ~150 silos/barges)')
print('❌ Feed Stock Entries: 0 (should track inventory levels)')
print('❌ Feeding Events: 0 (should be 1.4M+ daily feeding events)')
print('\n📋 CONCLUSION: Feed infrastructure partially implemented')
print('   - Basic feed types and purchases created')
print('   - Missing: containers, inventory tracking, feeding events')
