#!/usr/bin/env python
"""
Batch Growth Analysis Script

This script analyzes growth patterns, feed conversion ratios (FCR), and mortality
trends for batches in the AquaMind system. It helps verify that the generated test
data is within realistic ranges for Atlantic Salmon aquaculture.
"""
import os
import sys
import datetime
import logging
import django
import matplotlib.pyplot as plt
import numpy as np
from decimal import Decimal
from collections import defaultdict

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger('batch_analysis')

# Import models after Django setup
from django.db.models import Sum, Avg, Max, Min, F, Q, Count
from django.utils import timezone
from apps.batch.models import Batch, GrowthSample, MortalityEvent, BatchContainerAssignment
from apps.inventory.models import FeedingEvent

def print_section_header(title):
    """Print a section header for console output"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def analyze_batches():
    """Analyze and list all batches in the system with key metrics"""
    print_section_header("BATCH ANALYSIS")
    
    # Get all batches
    batches = Batch.objects.all().order_by('start_date')
    
    if not batches:
        print("No batches found in the database.")
        return
    
    print(f"Found {batches.count()} batches in the database.")
    print("\nBatch summary:")
    print(f"{'Batch Number':<15} {'Species':<20} {'Start Date':<12} {'Age (days)':<12} {'Population':<12} {'Avg Weight':<12} {'Biomass (kg)':<12} {'Status':<10} {'Lifecycle Stage':<15}")
    print("-" * 120)
    
    now = timezone.now().date()
    
    for batch in batches:
        age_days = (now - batch.start_date).days
        print(f"{batch.batch_number:<15} {batch.species.name:<20} {batch.start_date.strftime('%Y-%m-%d'):<12} {age_days:<12} {batch.population_count:<12} {batch.avg_weight_g:<12g} {batch.biomass_kg:<12.2f} {batch.status:<10} {batch.lifecycle_stage.name:<15}")
    
    print("\nSelect a batch number to analyze in detail (e.g., 'B2022-096'), or 'all' to analyze all batches: ", end='')
    batch_input = input().strip()
    
    if batch_input.lower() == 'all':
        selected_batches = batches
    else:
        selected_batches = Batch.objects.filter(batch_number=batch_input)
        if not selected_batches:
            print(f"Batch '{batch_input}' not found.")
            return
    
    for batch in selected_batches:
        analyze_batch_detail(batch)

def calculate_fcr(batch):
    """Calculate Feed Conversion Ratio for a batch"""
    # Get total feed used (kg)
    total_feed = FeedingEvent.objects.filter(batch=batch).aggregate(total=Sum('feed_amount_kg'))['total'] or 0
    
    # Get biomass gain
    first_sample = GrowthSample.objects.filter(batch=batch).order_by('sample_date').first()
    last_sample = GrowthSample.objects.filter(batch=batch).order_by('sample_date').last()
    
    if not first_sample or not last_sample:
        return None, 0, 0
    
    # Calculate initial and final biomass
    initial_biomass = (first_sample.avg_weight_g * batch.population_count) / 1000
    final_biomass = batch.biomass_kg
    biomass_gain = float(final_biomass - initial_biomass)
    
    # Calculate FCR
    if biomass_gain <= 0:
        return None, total_feed, biomass_gain
    
    fcr = float(total_feed) / biomass_gain
    return fcr, total_feed, biomass_gain

def analyze_batch_detail(batch):
    """Analyze a single batch in detail"""
    print_section_header(f"DETAILED ANALYSIS: {batch.batch_number}")
    
    # Basic batch info
    print(f"Batch: {batch.batch_number}")
    print(f"Species: {batch.species.name}")
    print(f"Current stage: {batch.lifecycle_stage.name}")
    print(f"Start date: {batch.start_date}")
    print(f"Current population: {batch.population_count:,}")
    print(f"Current average weight: {batch.avg_weight_g:.2f}g")
    print(f"Current biomass: {batch.biomass_kg:.2f}kg")
    print(f"Status: {batch.status}")
    
    # Calculate age
    now = timezone.now().date()
    age_days = (now - batch.start_date).days
    print(f"Age: {age_days} days")
    
    # Get growth samples
    growth_samples = GrowthSample.objects.filter(batch=batch).order_by('sample_date')
    sample_count = growth_samples.count()
    
    if sample_count == 0:
        print("\nNo growth samples found for this batch.")
        return
    
    print(f"\nGrowth samples: {sample_count}")
    
    # Get mortality events
    mortality_events = MortalityEvent.objects.filter(batch=batch)
    total_mortality = mortality_events.aggregate(sum=Sum('count'))['sum'] or 0
    total_mortality_biomass = mortality_events.aggregate(sum=Sum('biomass_kg'))['sum'] or 0
    
    mortality_pct = (total_mortality / (batch.population_count + total_mortality)) * 100 if (batch.population_count + total_mortality) > 0 else 0
    
    print(f"Total mortality: {total_mortality:,} fish ({mortality_pct:.2f}%)")
    print(f"Mortality biomass: {total_mortality_biomass:.2f}kg")
    
    # Calculate FCR
    fcr, total_feed, biomass_gain = calculate_fcr(batch)
    if fcr is not None:
        print(f"\nFeed Conversion Ratio (FCR): {fcr:.2f}")
        print(f"Total feed used: {total_feed:.2f}kg")
        print(f"Biomass gain: {biomass_gain:.2f}kg")
    else:
        print("\nUnable to calculate FCR (insufficient data or negative growth)")
    
    # Analyze growth curve
    if sample_count >= 2:
        print("\nGrowth Analysis:")
        
        # Calculate daily growth rate
        first_sample = growth_samples.first()
        last_sample = growth_samples.last()
        days_between = (last_sample.sample_date - first_sample.sample_date).days
        
        if days_between > 0:
            weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g
            daily_growth_g = weight_gain / days_between
            daily_growth_pct = (daily_growth_g / first_sample.avg_weight_g) * 100 if first_sample.avg_weight_g > 0 else 0
            
            print(f"Growth period: {first_sample.sample_date} to {last_sample.sample_date} ({days_between} days)")
            print(f"Initial weight: {first_sample.avg_weight_g:.2f}g")
            print(f"Final weight: {last_sample.avg_weight_g:.2f}g")
            print(f"Total weight gain: {weight_gain:.2f}g")
            print(f"Average daily growth: {daily_growth_g:.2f}g/day ({daily_growth_pct:.2f}%/day)")
            
            # Calculate specific growth rate (SGR)
            if first_sample.avg_weight_g > 0:
                sgr = (np.log(float(last_sample.avg_weight_g)) - np.log(float(first_sample.avg_weight_g))) / days_between * 100
                print(f"Specific Growth Rate (SGR): {sgr:.2f}%/day")
        
        # Plot growth curve
        try:
            dates = [sample.sample_date for sample in growth_samples]
            weights = [float(sample.avg_weight_g) for sample in growth_samples]
            
            plt.figure(figsize=(10, 6))
            plt.plot(dates, weights, 'b-o', linewidth=2, markersize=8)
            plt.xlabel('Date')
            plt.ylabel('Average Weight (g)')
            plt.title(f'Growth Curve for Batch {batch.batch_number}')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to file
            plot_file = f"growth_curve_{batch.batch_number.replace('-', '_')}.png"
            plt.savefig(plot_file)
            print(f"\nGrowth curve saved to {plot_file}")
            plt.close()
        except Exception as e:
            print(f"Error generating growth plot: {str(e)}")
    
    # Analyze mortality patterns
    if mortality_events.exists():
        print("\nMortality Analysis:")
        
        # Group by cause
        mortality_by_cause = mortality_events.values('cause').annotate(
            count=Sum('count'),
            percentage=Sum('count') * 100.0 / total_mortality
        ).order_by('-count')
        
        print("\nMortality by cause:")
        for item in mortality_by_cause:
            print(f"  {item['cause']}: {item['count']:,} fish ({item['percentage']:.2f}%)")
        
        # Group by month
        mortality_by_month = defaultdict(int)
        for event in mortality_events:
            month_key = event.event_date.strftime('%Y-%m')
            mortality_by_month[month_key] += event.count
        
        print("\nMortality by month:")
        for month, count in sorted(mortality_by_month.items()):
            print(f"  {month}: {count:,} fish")

def main():
    """Main function"""
    print_section_header("AQUAMIND BATCH ANALYSIS")
    
    analyze_batches()
    
    print("\nAnalysis completed!")

if __name__ == "__main__":
    main()
