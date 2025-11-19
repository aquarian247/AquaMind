#!/usr/bin/env python
"""
Full Lifecycle Simulation Script

This script simulates a complete Atlantic Salmon lifecycle from egg to harvest
(850-900 days), generating realistic growth patterns, stage transitions, and
feed conversion ratios (FCR).
"""
import os
import sys
import datetime
import logging
import random
import django
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Import models after Django setup
from django.db.models import Sum, Avg, Max, Min, F, Q, Count
from django.utils import timezone
from apps.batch.models import Batch, GrowthSample, MortalityEvent, BatchContainerAssignment, LifeCycleStage
from apps.infrastructure.models import Container, Geography, Area
from apps.inventory.models import FeedingEvent, Feed, FeedStock, FeedContainer
from django.db import transaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger('lifecycle_simulation')

def print_section_header(title):
    """Print a section header for console output"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def cleanup_previous_simulation():
    """Clean up previous simulation data"""
    print_section_header("CLEANING UP PREVIOUS SIMULATION DATA")
    
    # Define the batch number for our simulation
    batch_number = "B2023-SIM"
    
    # Delete the simulation batch if it exists
    try:
        batch = Batch.objects.filter(batch_number=batch_number).first()
        if batch:
            # Delete related records first
            GrowthSample.objects.filter(batch=batch).delete()
            MortalityEvent.objects.filter(batch=batch).delete()
            FeedingEvent.objects.filter(batch=batch).delete()
            BatchContainerAssignment.objects.filter(batch=batch).delete()
            batch.delete()
            print(f"Deleted previous simulation batch: {batch_number}")
        else:
            print(f"No previous simulation batch found.")
    except Exception as e:
        logger.error(f"Error cleaning up previous simulation: {str(e)}")

def create_simulation_batch():
    """Create a new batch for simulation"""
    print_section_header("CREATING SIMULATION BATCH")
    
    # Define the batch number and start date
    batch_number = "B2023-SIM"
    start_date = timezone.now().date() - datetime.timedelta(days=900)
    
    # Get required objects
    try:
        # Get the first Atlantic Salmon species
        species = None
        for s in list(Batch.objects.all().values_list('species__name', flat=True).distinct()):
            if 'salmon' in s.lower():
                species = Batch.objects.filter(species__name=s).first().species
                break
        
        if not species:
            print("Could not find Atlantic Salmon species. Using first available species.")
            species = Batch.objects.first().species
        
        # Get the first lifecycle stage (Egg&Alevin)
        first_stage = LifeCycleStage.objects.order_by('order').first()
        
        # Create the new batch
        batch = Batch.objects.create(
            batch_number=batch_number,
            species=species,
            start_date=start_date,
            population_count=1000000,  # Start with 1 million eggs
            avg_weight_g=0.2,  # Average egg weight
            status='ACTIVE',
            lifecycle_stage=first_stage,
            notes="Simulation batch for full lifecycle testing"
        )
        
        print(f"Created new simulation batch: {batch_number}")
        print(f"  Species: {species.name}")
        print(f"  Start date: {start_date}")
        print(f"  Initial population: {batch.population_count:,}")
        print(f"  Initial stage: {first_stage.name}")
        
        return batch
    
    except Exception as e:
        logger.error(f"Error creating simulation batch: {str(e)}")
        return None

def get_lifecycle_stages():
    """Get the lifecycle stages in order"""
    return list(LifeCycleStage.objects.all().order_by('order'))

def get_stage_duration(stage_name):
    """Get the typical duration for each lifecycle stage in days"""
    durations = {
        'Egg&Alevin': 90,
        'Fry': 90,
        'Parr': 90,
        'Smolt': 90,
        'Post-Smolt': 90,
        'Adult': 400
    }
    return durations.get(stage_name, 90)  # Default to 90 days if stage not found

def get_expected_weight(stage_name, day_in_stage):
    """
    Get the expected weight based on lifecycle stage and day in stage
    Returns weight in grams
    """
    # Starting weights for each stage
    start_weights = {
        'Egg&Alevin': 0.2,  # Egg weight
        'Fry': 0.5,
        'Parr': 5.0,
        'Smolt': 50.0,
        'Post-Smolt': 100.0,
        'Adult': 500.0
    }
    
    # End weights for each stage (target for the end of the stage)
    end_weights = {
        'Egg&Alevin': 0.5,  # Alevin weight
        'Fry': 5.0,
        'Parr': 50.0,
        'Smolt': 100.0,
        'Post-Smolt': 500.0,
        'Adult': 5000.0  # Harvest weight
    }
    
    # Get stage duration and calculate where we are in the stage
    stage_duration = get_stage_duration(stage_name)
    start_weight = start_weights.get(stage_name, 0.2)
    end_weight = end_weights.get(stage_name, 5000.0)
    
    # Use a logarithmic growth model for more realistic growth patterns
    if day_in_stage <= 0:
        return start_weight
    
    if day_in_stage >= stage_duration:
        return end_weight
    
    # Calculate growth percentage complete
    percentage_complete = day_in_stage / stage_duration
    
    # Use a sigmoid growth function for more realistic pattern
    if stage_name == 'Adult':
        # Adults grow faster in the middle of the cycle
        import math
        x = percentage_complete * 10 - 5  # Scale to -5 to 5 for sigmoid function
        sigmoid = 1 / (1 + math.exp(-x))  # Sigmoid function from 0 to 1
        weight = start_weight + (end_weight - start_weight) * sigmoid
    else:
        # More linear growth for earlier stages
        weight = start_weight + (end_weight - start_weight) * percentage_complete
    
    return round(weight, 2)

def get_expected_mortality_rate(stage_name, day_in_stage):
    """
    Get the expected daily mortality rate based on lifecycle stage and day in stage
    Returns percentage (0-100)
    """
    # Base daily mortality rates for each stage
    base_rates = {
        'Egg&Alevin': 0.20,  # Higher mortality for eggs
        'Fry': 0.10,
        'Parr': 0.05,
        'Smolt': 0.08,  # Slightly higher during transition
        'Post-Smolt': 0.03,
        'Adult': 0.02
    }
    
    # Get base rate for the stage
    base_rate = base_rates.get(stage_name, 0.05)
    
    # Add random variation
    variation = random.uniform(-0.5, 1.0) * base_rate
    daily_rate = max(0, base_rate + variation)
    
    # Add occasional disease events (rare spikes)
    if random.random() < 0.02:  # 2% chance each day
        daily_rate *= random.uniform(3, 10)  # 3-10x higher mortality
    
    return daily_rate

def get_expected_fcr(stage_name, avg_weight):
    """
    Get the expected Feed Conversion Ratio based on lifecycle stage and average weight
    """
    # FCR increases as fish grow larger
    if stage_name in ['Egg&Alevin', 'Fry']:
        return random.uniform(0.8, 1.0)  # Very efficient at small sizes
    elif stage_name == 'Parr':
        return random.uniform(0.9, 1.1)
    elif stage_name == 'Smolt':
        return random.uniform(1.0, 1.2)
    elif stage_name == 'Post-Smolt':
        return random.uniform(1.1, 1.3)
    else:  # Adult
        # FCR increases with size for adults
        if avg_weight < 1000:
            return random.uniform(1.1, 1.3)
        elif avg_weight < 3000:
            return random.uniform(1.2, 1.4)
        else:
            return random.uniform(1.3, 1.5)

def get_mortality_cause():
    """Get a random mortality cause based on probability"""
    causes = [
        ('DISEASE', 0.25),
        ('HANDLING', 0.15),
        ('PREDATION', 0.05),
        ('ENVIRONMENTAL', 0.20),
        ('UNKNOWN', 0.20),
        ('OTHER', 0.15)
    ]
    
    r = random.random()
    cumulative = 0
    for cause, prob in causes:
        cumulative += prob
        if r <= cumulative:
            return cause
    
    return 'UNKNOWN'  # Fallback

def get_suitable_container(stage_name):
    """Get a suitable container for a lifecycle stage"""
    # Use container naming patterns to find appropriate containers for each stage
    if stage_name == 'Egg&Alevin':
        # Look for trays which are suitable for eggs
        containers = Container.objects.filter(name__icontains='Tray')
    elif stage_name in ['Fry', 'Parr']:
        # Look for small tanks for fry and parr
        containers = Container.objects.filter(name__icontains='Tank')
    elif stage_name == 'Smolt':
        # Larger tanks for smolts
        containers = Container.objects.filter(name__icontains='Tank').filter(volume_m3__gte=10)
    elif stage_name in ['Post-Smolt', 'Adult']:
        # Sea pens for post-smolts and adults
        containers = Container.objects.filter(Q(name__icontains='Pen') | Q(area__isnull=False))
    else:
        # Fallback to any container
        containers = Container.objects.all()
    
    # If no specific containers found, fall back to any container
    if not containers.exists():
        containers = Container.objects.all()
    
    # Return a random container from the filtered set
    container_count = containers.count()
    if container_count > 0:
        random_index = random.randint(0, container_count - 1)
        return containers[random_index]
    
    # If still no containers, return None
    logger.warning(f"No suitable containers found for stage {stage_name}")
    return None

def simulate_batch_lifecycle(batch, days=900):
    """
    Simulate the complete lifecycle of a batch over specified days
    """
    print_section_header(f"SIMULATING LIFECYCLE FOR {batch.batch_number}")
    
    # Get lifecycle stages
    stages = get_lifecycle_stages()
    
    if not stages:
        print("No lifecycle stages found in the database.")
        return
    
    # Starting values
    current_date = batch.start_date
    current_stage = stages[0]
    current_stage_day = 0
    current_population = batch.population_count
    current_weight = batch.avg_weight_g
    current_biomass = (current_population * current_weight) / 1000  # kg
    current_container = None
    current_assignment = None
    
    # Track cumulative values
    total_feed_used = 0
    total_mortality = 0
    
    # Make initial container assignment
    initial_container = get_suitable_container(current_stage.name)
    if initial_container:
        try:
            current_assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=initial_container,
                lifecycle_stage=current_stage,
                assignment_date=current_date,
                population_count=current_population,
                biomass_kg=current_biomass,
                is_active=True
            )
            current_container = initial_container
            print(f"Assigned batch to initial container: {initial_container.name}")
        except Exception as e:
            logger.error(f"Error creating initial container assignment: {str(e)}")
    else:
        print("No suitable containers available for initial assignment.")
        return
    
    # Simulate each day
    for day in range(days):
        # Update current date
        current_date = batch.start_date + datetime.timedelta(days=day)
        
        # Check if we need to transition to next stage
        stage_duration = get_stage_duration(current_stage.name)
        if current_stage_day >= stage_duration and stages.index(current_stage) < len(stages) - 1:
            # Move to next stage
            current_stage_idx = stages.index(current_stage)
            previous_stage = current_stage
            current_stage = stages[current_stage_idx + 1]
            current_stage_day = 0
            
            # Update batch lifecycle stage
            batch.lifecycle_stage = current_stage
            batch.save()
            
            # Assign to new container for the new stage
            new_container = get_suitable_container(current_stage.name)
            
            if new_container:
                try:
                    # Deactivate previous assignment
                    if current_assignment:
                        current_assignment.is_active = False
                        current_assignment.save()
                    
                    # Create new assignment
                    current_biomass = (current_population * current_weight) / 1000  # kg
                    current_assignment = BatchContainerAssignment.objects.create(
                        batch=batch,
                        container=new_container,
                        lifecycle_stage=current_stage,
                        assignment_date=current_date,
                        population_count=current_population,
                        biomass_kg=current_biomass,
                        is_active=True
                    )
                    current_container = new_container
                    
                    print(f"Day {day}: Batch transitioned from {previous_stage.name} to {current_stage.name}")
                    print(f"Day {day}: Assigned batch to new container: {new_container.name}")
                except Exception as e:
                    logger.error(f"Error transitioning to new container: {str(e)}")
            else:
                logger.warning(f"No suitable container found for stage {current_stage.name}")
        
        # Calculate expected weight for this day
        expected_weight = get_expected_weight(current_stage.name, current_stage_day)
        
        # Calculate expected mortality
        daily_mortality_rate = get_expected_mortality_rate(current_stage.name, current_stage_day)
        daily_mortality = int(current_population * daily_mortality_rate / 100)
        
        # Create mortality event if there are mortalities
        if daily_mortality > 0:
            try:
                mortality_biomass = (daily_mortality * current_weight) / 1000  # kg
                
                # Create mortality event (requires assignment - skip if none available)
                active_assignment = batch.batch_assignments.filter(is_active=True).first()
                if active_assignment:
                    MortalityEvent.objects.create(
                        batch=batch,
                        assignment=active_assignment,
                        event_date=current_date,
                        count=daily_mortality,
                        biomass_kg=mortality_biomass,
                        cause=get_mortality_cause(),
                        description=f"Simulated mortality event for {batch.batch_number}"
                    )
                
                # Update population and assignment
                current_population -= daily_mortality
                total_mortality += daily_mortality
                
                if current_assignment:
                    current_assignment.population_count = current_population
                    current_assignment.biomass_kg = (current_population * current_weight) / 1000
                    current_assignment.save()
            except Exception as e:
                logger.error(f"Error creating mortality event: {str(e)}")
        
        # Update weight (simulate growth)
        current_weight = expected_weight
        
        # Calculate feeding (only if past alevin stage with yolk sac)
        if current_stage.name != 'Egg&Alevin':
            try:
                current_biomass = (current_population * current_weight) / 1000  # kg
                
                # Calculate feeding rate as percentage of biomass
                if current_weight < 10:
                    feeding_pct = random.uniform(3.0, 5.0)  # Fry (3-5% of biomass)
                elif current_weight < 100:
                    feeding_pct = random.uniform(2.0, 3.0)  # Parr/small smolt (2-3%)
                elif current_weight < 1000:
                    feeding_pct = random.uniform(1.0, 2.0)  # Smolt/post-smolt (1-2%)
                else:
                    feeding_pct = random.uniform(0.5, 1.0)  # Adult (0.5-1%)
                
                # Calculate daily feed amount
                daily_feed_kg = Decimal(str(current_biomass * feeding_pct / 100))
                daily_feed_kg = daily_feed_kg.quantize(Decimal('0.01'))  # Round to 2 decimal places
                
                # Get or create a feed for the stage
                # Use appropriate feed size for each stage/weight
                if current_weight < 1:
                    feed_size = 'MICRO'  # Micro feed for very small fish
                elif current_weight < 10:
                    feed_size = 'SMALL'  # Small feed for fry
                elif current_weight < 100:
                    feed_size = 'MEDIUM'  # Medium for parr/small smolts
                else:
                    feed_size = 'LARGE'  # Large for post-smolts and adults
                
                # Try to find an appropriate feed based on size category
                feed = Feed.objects.filter(size_category=feed_size).first()
                
                # If no feed of that size exists, try to find any feed
                if not feed:
                    feed = Feed.objects.first()
                
                feed_stock = None
                if feed:
                    feed_stock = FeedStock.objects.filter(feed=feed).first()
                
                # Skip creating feeding if there's not enough stock
                if feed and feed_stock:
                    try:
                        if feed_stock.current_quantity_kg >= daily_feed_kg:
                            # Create the feeding event with proper Decimal values
                            FeedingEvent.objects.create(
                                batch=batch,
                                batch_assignment=current_assignment,
                                container=current_container,
                                feed=feed,
                                feed_stock=feed_stock,
                                feeding_date=current_date,
                                feeding_time=datetime.time(hour=8, minute=0),  # Default feeding time
                                batch_biomass_kg=Decimal(str(current_biomass)),
                                amount_kg=daily_feed_kg,
                                feeding_percentage=Decimal(str(feeding_pct)),
                                feed_conversion_ratio=Decimal(str(get_expected_fcr(current_stage.name, current_weight))),
                                method='AUTOMATIC',
                                notes=f"Simulated feeding for {batch.batch_number}"
                            )
                            
                            # Update total feed used for simulation summary
                            total_feed_used += float(daily_feed_kg)
                    except Exception as e:
                        logger.error(f"Error creating feeding event record: {str(e)}")
            except Exception as e:
                logger.error(f"Error in feeding calculation: {str(e)}")
        
        # Create growth sample every 30 days (more frequent for adults)
        sample_frequency = 15 if current_stage.name == 'Adult' else 30
        if day % sample_frequency == 0 or day == days - 1:
            try:
                # Calculate sample size (1-3% of population)
                sample_size = min(max(int(current_population * random.uniform(0.01, 0.03)), 1), 100)
                
                # Calculate length from weight using condition factor
                # Length (cm) = (Weight (g) / CF)^(1/3) * 10
                condition_factor = random.uniform(0.9, 1.2)  # Typical range for salmon
                avg_length_cm = round(((current_weight / condition_factor) ** (1/3)) * 10, 2)
                
                # Create growth sample
                GrowthSample.objects.create(
                    batch=batch,
                    sample_date=current_date,
                    sample_size=sample_size,
                    avg_weight_g=current_weight,
                    avg_length_cm=avg_length_cm,
                    condition_factor=condition_factor,
                    notes=f"Simulated growth sample for {batch.batch_number}"
                )
                
                print(f"Day {day}: Created growth sample - Weight: {current_weight:.2f}g, Length: {avg_length_cm:.2f}cm")
            except Exception as e:
                logger.error(f"Error creating growth sample: {str(e)}")
        
        # Update batch stats every 7 days
        if day % 7 == 0 or day == days - 1:
            try:
                current_biomass = (current_population * current_weight) / 1000  # kg
                
                batch.population_count = current_population
                batch.avg_weight_g = current_weight
                batch.biomass_kg = current_biomass
                batch.save()
                
                # Also update the container assignment
                if current_assignment:
                    current_assignment.population_count = current_population
                    current_assignment.biomass_kg = current_biomass
                    current_assignment.save()
            except Exception as e:
                logger.error(f"Error updating batch stats: {str(e)}")
        
        # Increment stage day
        current_stage_day += 1
    
    # Final update of batch
    try:
        current_biomass = (current_population * current_weight) / 1000  # kg
        batch.population_count = current_population
        batch.avg_weight_g = current_weight
        batch.biomass_kg = current_biomass
        batch.save()
    except Exception as e:
        logger.error(f"Error in final batch update: {str(e)}")
    
    # Print summary statistics
    print_section_header("SIMULATION SUMMARY")
    print(f"Batch: {batch.batch_number}")
    print(f"Simulation period: {batch.start_date} to {current_date} ({days} days)")
    print(f"Final lifecycle stage: {current_stage.name}")
    print(f"Starting population: {batch.population_count + total_mortality:,}")
    print(f"Final population: {batch.population_count:,}")
    print(f"Total mortality: {total_mortality:,} ({total_mortality/(batch.population_count + total_mortality)*100:.2f}%)")
    print(f"Final average weight: {batch.avg_weight_g:.2f}g")
    print(f"Final biomass: {batch.biomass_kg:.2f}kg")
    print(f"Total feed used: {total_feed_used:.2f}kg")
    
    # Calculate overall FCR
    if total_feed_used > 0:
        initial_biomass = 0.2 * (batch.population_count + total_mortality) / 1000  # Initial biomass at 0.2g egg weight
        final_biomass = batch.biomass_kg
        biomass_gain = final_biomass - initial_biomass
        
        if biomass_gain > 0:
            overall_fcr = total_feed_used / biomass_gain
            print(f"Overall Feed Conversion Ratio (FCR): {overall_fcr:.2f}")
    
    return batch

def ensure_feed_stock_exists():
    """Create feed and feed stock records if they don't already exist"""
    print_section_header("ENSURING FEED STOCK AVAILABLE")
    
    # Define feed types we need for all lifecycle stages
    feed_types = [
        {
            'name': 'Starter Feed',
            'brand': 'AquaGrow',
            'size_category': 'MICRO',
            'pellet_size_mm': Decimal('0.5'),
            'protein_percentage': Decimal('55.0'),
            'fat_percentage': Decimal('15.0'),
            'description': 'Very fine micro feed for fry'
        },
        {
            'name': 'Fry Feed',
            'brand': 'AquaGrow',
            'size_category': 'SMALL',
            'pellet_size_mm': Decimal('1.0'),
            'protein_percentage': Decimal('50.0'),
            'fat_percentage': Decimal('18.0'),
            'description': 'Small pellets for growing fry'
        },
        {
            'name': 'Parr/Smolt Feed',
            'brand': 'AquaGrow',
            'size_category': 'MEDIUM',
            'pellet_size_mm': Decimal('3.0'),
            'protein_percentage': Decimal('45.0'),
            'fat_percentage': Decimal('20.0'),
            'description': 'Medium pellets for parr and smolts'
        },
        {
            'name': 'Grower Feed',
            'brand': 'AquaGrow',
            'size_category': 'LARGE',
            'pellet_size_mm': Decimal('6.0'),
            'protein_percentage': Decimal('42.0'),
            'fat_percentage': Decimal('25.0'),
            'description': 'Large pellets for post-smolts and adults'
        }
    ]
    
    # Check if we have any feed records
    feed_count = Feed.objects.count()
    if feed_count == 0:
        print("No feed records found. Creating standard feed types...")
        for feed_data in feed_types:
            Feed.objects.create(**feed_data)
        print(f"Created {len(feed_types)} feed types")
    else:
        print(f"Found {feed_count} existing feed types.")
    
    # Check if we have any feed containers
    feed_containers = FeedContainer.objects.all()
    if not feed_containers.exists():
        print("No feed containers found. Creating default container...")
        # Create a default feed container if none exist
        default_container = FeedContainer.objects.create(
            name="Main Feed Silo",
            capacity_kg=10000,
            description="Main feed storage silo"
        )
        feed_containers = [default_container]
        print("Created default feed container")
    else:
        print(f"Found {feed_containers.count()} feed containers")
    
    # Check if we have feed stock for all feed types
    feeds = Feed.objects.all()
    stock_created = 0
    
    for feed in feeds:
        # Check if feed stock exists for this feed
        stock = FeedStock.objects.filter(feed=feed).first()
        if not stock:
            # Create stock with a large quantity
            container = feed_containers[0]  # Use first container
            FeedStock.objects.create(
                feed=feed,
                feed_container=container,
                current_quantity_kg=Decimal('5000.0'),  # Plenty of feed for simulation
                reorder_threshold_kg=Decimal('500.0'),
                notes=f"Simulation stock for {feed.name}"
            )
            stock_created += 1
    
    if stock_created > 0:
        print(f"Created {stock_created} feed stock records")
    else:
        print("Feed stock already exists for all feed types")
    
    return True

def main():
    """Main function to run the simulation"""
    print_section_header("FULL LIFECYCLE SIMULATION")
    
    # Clean up any previous simulation data
    cleanup_previous_simulation()
    
    # Ensure feed stock exists
    ensure_feed_stock_exists()
    
    # Create new simulation batch
    batch = create_simulation_batch()
    if not batch:
        print("Failed to create simulation batch. Exiting.")
        return
    
    # Simulate the batch lifecycle
    simulate_batch_lifecycle(batch, days=900)
    
    print("\nSimulation completed!")
    print("\nTo analyze the results, you can run:")
    print("1. scripts\\analyze_batch_growth.py - For growth patterns and FCR analysis")
    print("2. scripts\\inspect_assignment_model.py - To verify lifecycle stage transitions")
    print("3. SELECT * FROM batch_growthsample WHERE batch_id = <batch_id> ORDER BY sample_date;")
    print("4. SELECT * FROM batch_mortalityevent WHERE batch_id = <batch_id> ORDER BY event_date;")

if __name__ == "__main__":
    main()
