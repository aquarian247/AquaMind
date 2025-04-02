#!/usr/bin/env python
"""
Growth Patterns Analysis Script

This script analyzes growth patterns, FCR, and mortality trends for batches 
with the most growth samples in the AquaMind system.
"""
import os
import sys
import datetime
import logging
import django
import matplotlib.pyplot as plt
import numpy as np
from decimal import Decimal

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

logger = logging.getLogger('growth_analysis')

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

def analyze_batch_growth(batch):
    """Analyze growth patterns for a batch"""
    print_section_header(f"GROWTH ANALYSIS: {batch.batch_number}")
    
    # Basic batch info
    print(f"Batch: {batch.batch_number}")
    print(f"Species: {batch.species.name}")
    print(f"Current stage: {batch.lifecycle_stage.name}")
    print(f"Start date: {batch.start_date}")
    print(f"Current population: {batch.population_count:,}")
    print(f"Current average weight: {batch.avg_weight_g:.2f}g")
    print(f"Current biomass: {batch.biomass_kg:.2f}kg")
    
    # Calculate age
    now = timezone.now().date()
    age_days = (now - batch.start_date).days
    print(f"Age: {age_days} days")
    
    # Get growth samples
    growth_samples = GrowthSample.objects.filter(batch=batch).order_by('sample_date')
    sample_count = growth_samples.count()
    
    if sample_count == 0:
        print("No growth samples found for this batch.")
        return
    
    print(f"Growth samples: {sample_count}")
    
    # Get mortality events
    mortality_events = MortalityEvent.objects.filter(batch=batch)
    total_mortality = mortality_events.aggregate(sum=Sum('count'))['sum'] or 0
    total_mortality_biomass = mortality_events.aggregate(sum=Sum('biomass_kg'))['sum'] or 0
    
    if batch.population_count + total_mortality > 0:
        mortality_pct = (total_mortality / (batch.population_count + total_mortality)) * 100
        print(f"Total mortality: {total_mortality:,} fish ({mortality_pct:.2f}%)")
        print(f"Mortality biomass: {total_mortality_biomass:.2f}kg")
    
    # Calculate FCR
    total_feed = FeedingEvent.objects.filter(batch=batch).aggregate(total=Sum('feed_amount_kg'))['total'] or 0
    
    if sample_count >= 2:
        first_sample = growth_samples.first()
        last_sample = growth_samples.last()
        
        print("\nGrowth Analysis:")
        print(f"First sample date: {first_sample.sample_date}, weight: {first_sample.avg_weight_g:.2f}g")
        print(f"Last sample date: {last_sample.sample_date}, weight: {last_sample.avg_weight_g:.2f}g")
        
        days_between = (last_sample.sample_date - first_sample.sample_date).days
        if days_between > 0:
            weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g
            daily_growth_g = weight_gain / days_between
            
            print(f"Days between samples: {days_between}")
            print(f"Weight gain: {weight_gain:.2f}g")
            print(f"Daily growth: {daily_growth_g:.2f}g/day")
            
            if first_sample.avg_weight_g > 0:
                daily_growth_pct = (daily_growth_g / first_sample.avg_weight_g) * 100
                print(f"Daily growth rate: {daily_growth_pct:.3f}%/day")
                
                # Calculate specific growth rate (SGR)
                sgr = (np.log(float(last_sample.avg_weight_g)) - np.log(float(first_sample.avg_weight_g))) / days_between * 100
                print(f"Specific Growth Rate (SGR): {sgr:.3f}%/day")
                
                # Calculate biomass gain and FCR
                initial_count = batch.population_count + total_mortality
                initial_biomass = (first_sample.avg_weight_g * initial_count) / 1000
                final_biomass = batch.biomass_kg + total_mortality_biomass
                biomass_gain = float(final_biomass - initial_biomass)
                
                print(f"\nInitial biomass (est.): {initial_biomass:.2f}kg")
                print(f"Current biomass + mortality: {final_biomass:.2f}kg")
                print(f"Biomass gain: {biomass_gain:.2f}kg")
                print(f"Total feed used: {total_feed:.2f}kg")
                
                if biomass_gain > 0 and total_feed > 0:
                    fcr = float(total_feed) / biomass_gain
                    print(f"Feed Conversion Ratio (FCR): {fcr:.2f}")
                else:
                    print("Cannot calculate FCR (insufficient biomass gain or feed data)")
        
        # Create a growth curve
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
            print(f"\nGrowth curve plot saved to: {plot_file}")
            plt.close()
        except Exception as e:
            print(f"Error generating growth plot: {str(e)}")

def main():
    """Main function"""
    print_section_header("AQUAMIND GROWTH PATTERN ANALYSIS")
    
    # Find batches with the most growth samples
    batch_sample_counts = Batch.objects.annotate(
        sample_count=Count('growth_samples')
    ).order_by('-sample_count')
    
    if not batch_sample_counts:
        print("No batches found in the database.")
        return
    
    print(f"Found {batch_sample_counts.count()} batches in the database.")
    
    # Display summary
    print("\nBatch summary (ordered by number of growth samples):")
    print(f"{'Batch Number':<15} {'Lifecycle Stage':<15} {'Start Date':<12} {'Age (days)':<12} {'Samples':<10}")
    print("-" * 70)
    
    now = timezone.now().date()
    
    for batch in batch_sample_counts[:5]:  # Display top 5
        age_days = (now - batch.start_date).days
        print(f"{batch.batch_number:<15} {batch.lifecycle_stage.name:<15} {batch.start_date.strftime('%Y-%m-%d'):<12} {age_days:<12} {batch.sample_count:<10}")
    
    # Analyze the batch with the most samples
    top_batch = batch_sample_counts.first()
    if top_batch and top_batch.sample_count > 0:
        print(f"\nAnalyzing batch with the most growth samples: {top_batch.batch_number} ({top_batch.sample_count} samples)")
        analyze_batch_growth(top_batch)
    else:
        print("\nNo batches with growth samples found.")
    
    # If available, also analyze a batch that's older (for more complete lifecycle view)
    old_batches = Batch.objects.filter(start_date__lt=now - datetime.timedelta(days=365)).annotate(
        sample_count=Count('growth_samples')
    ).order_by('-sample_count')
    
    if old_batches and old_batches.first().sample_count > 0 and old_batches.first() != top_batch:
        oldest_batch = old_batches.first()
        print(f"\nAnalyzing an older batch for lifecycle comparison: {oldest_batch.batch_number} (Age: {(now - oldest_batch.start_date).days} days)")
        analyze_batch_growth(oldest_batch)
    
    print("\nAnalysis completed!")

if __name__ == "__main__":
    main()
