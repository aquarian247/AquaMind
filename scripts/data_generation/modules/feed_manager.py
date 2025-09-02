"""
Feed Manager Module

This module handles feed types, feed stock, and feeding events generation
for the AquaMind test data generation system.
"""
import random
import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from datetime import date
import logging

from apps.inventory.models import Feed, FeedStock, FeedingEvent
from apps.infrastructure.models import FeedContainer
from apps.batch.models import BatchContainerAssignment, LifeCycleStage

logger = logging.getLogger(__name__)


class FeedManager:
    """Manages feed-related data generation."""
    
    def __init__(self):
        """Initialize the feed manager."""
        # Define feed types by lifecycle stage
        self.feed_types = self._ensure_feed_types_exist()
        
        # Define FCR (Feed Conversion Ratio) by lifecycle stage
        self.fcr_by_stage = {
            "Egg&Alevin": None,  # Eggs/alevins don't feed
            "Fry": (1.0, 1.2),   # FCR range for Fry
            "Parr": (1.1, 1.3),  # FCR range for Parr
            "Smolt": (1.2, 1.4), # FCR range for Smolt
            "Post-Smolt": (1.2, 1.4), # FCR range for Post-Smolt
            "Adult": (1.2, 1.4)  # FCR range for Adult
        }
        
        # Define feeding rate (% of biomass) by lifecycle stage
        self.feeding_rate_by_stage = {
            "Egg&Alevin": 0.0,    # No feeding for eggs/alevins
            "Fry": (2.0, 5.0),    # 2-5% of biomass per day
            "Parr": (1.5, 3.0),   # 1.5-3% of biomass per day
            "Smolt": (1.0, 2.0),  # 1-2% of biomass per day
            "Post-Smolt": (0.5, 1.5), # 0.5-1.5% of biomass per day
            "Adult": (0.3, 1.0)   # 0.3-1% of biomass per day
        }
    
    def _ensure_feed_types_exist(self):
        """Ensure that all required feed types exist in the database."""
        feed_types = {}
        
        # Define feed specifications by lifecycle stage
        feed_specs = [
            {
                "name": "Fry Feed",
                "stage": "Fry",
                "brand": "AquaNutrition",
                "size_category": "MICRO",
                "pellet_size_mm": 0.5,
                "protein_percentage": 55.0,
                "fat_percentage": 15.0,
                "carbohydrate_percentage": 12.0
            },
            {
                "name": "Parr Feed",
                "stage": "Parr",
                "brand": "AquaNutrition",
                "size_category": "SMALL",
                "pellet_size_mm": 1.5,
                "protein_percentage": 50.0,
                "fat_percentage": 18.0,
                "carbohydrate_percentage": 15.0
            },
            {
                "name": "Smolt Feed",
                "stage": "Smolt",
                "brand": "AquaNutrition",
                "size_category": "MEDIUM",
                "pellet_size_mm": 3.0,
                "protein_percentage": 45.0,
                "fat_percentage": 22.0,
                "carbohydrate_percentage": 18.0
            },
            {
                "name": "Post-Smolt Feed",
                "stage": "Post-Smolt",
                "brand": "AquaNutrition",
                "size_category": "MEDIUM",
                "pellet_size_mm": 4.5,
                "protein_percentage": 42.0,
                "fat_percentage": 25.0,
                "carbohydrate_percentage": 18.0
            },
            {
                "name": "Adult Feed",
                "stage": "Adult",
                "brand": "AquaNutrition",
                "size_category": "LARGE",
                "pellet_size_mm": 6.0,
                "protein_percentage": 40.0,
                "fat_percentage": 28.0,
                "carbohydrate_percentage": 20.0
            }
        ]
        
        # Create feed types
        for spec in feed_specs:
            feed, created = Feed.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "brand": spec["brand"],
                    "size_category": spec["size_category"],
                    "pellet_size_mm": spec["pellet_size_mm"],
                    "protein_percentage": spec["protein_percentage"],
                    "fat_percentage": spec["fat_percentage"],
                    "carbohydrate_percentage": spec["carbohydrate_percentage"],
                    "description": f"Feed for {spec['stage']} stage fish"
                }
            )
            
            feed_types[spec["stage"]] = feed
            
            if created:
                print(f"Created feed type: {feed.name}")
                
                # Create feed stock in containers
                self._ensure_feed_stock_exists(feed)
        
        return feed_types
    
    def _ensure_feed_stock_exists(self, feed):
        """Ensure feed stock exists in appropriate containers."""
        # Get all feed containers
        feed_containers = FeedContainer.objects.all()
        
        if not feed_containers:
            print("WARNING: No feed containers found. Feed stock not created.")
            return
        
        # Create feed stock in each container
        for container in feed_containers:
            stock, created = FeedStock.objects.get_or_create(
                feed=feed,
                feed_container=container,
                defaults={
                    "current_quantity_kg": Decimal('5000.0'),  # 5000kg initial stock
                    "reorder_threshold_kg": Decimal('500.0')   # 500kg reorder threshold
                }
            )
            
            if created:
                print(f"  Created feed stock: {feed.name} in {container.name}")
    
    def get_feed_for_stage(self, stage_name):
        """Get the appropriate feed type for a lifecycle stage."""
        return self.feed_types.get(stage_name)
    
    def get_fcr_for_stage(self, stage_name):
        """Get the Feed Conversion Ratio range for a lifecycle stage."""
        fcr_range = self.fcr_by_stage.get(stage_name)
        if fcr_range:
            return random.uniform(fcr_range[0], fcr_range[1])
        return None
    
    def get_feeding_rate_for_stage(self, stage_name):
        """Get the feeding rate (% of biomass) for a lifecycle stage."""
        rate_range = self.feeding_rate_by_stage.get(stage_name)
        if rate_range:
            return random.uniform(rate_range[0], rate_range[1])
        return 0.0
    
    @transaction.atomic
    def generate_feeding_events(self, start_date, end_date=None, feedings_per_day=4):
        """
        Generate feeding events for all active batch container assignments.
        
        Args:
            start_date: The date to start generating feedings from
            end_date: The end date (defaults to today)
            feedings_per_day: Number of feedings per day (default: 4)
            
        Returns:
            Total number of feeding events generated
        """
        if end_date is None:
            end_date = timezone.now().date()
        
        # Get all active container assignments within the date range
        assignments = BatchContainerAssignment.objects.filter(
            assignment_date__lte=end_date,
            departure_date__isnull=True
        ).select_related('batch', 'container', 'batch__lifecycle_stage')

        # Also get assignments that ended within the date range
        ended_assignments = BatchContainerAssignment.objects.filter(
            assignment_date__lte=end_date,
            departure_date__gte=start_date
        ).select_related('batch', 'container', 'batch__lifecycle_stage')
        
        # Combine all assignments for processing
        all_assignments = list(assignments) + list(ended_assignments)
        
        # Process each day in the range
        current_date = start_date
        total_feedings = 0
        
        while current_date <= end_date:
            # Generate feeding times for the day
            feeding_hours = sorted(random.sample(range(6, 20), feedings_per_day))
            
            for assignment in all_assignments:
                # Check if this assignment was active on this date
                if (assignment.assignment_date <= current_date and 
                    (assignment.departure_date is None or assignment.departure_date >= current_date)):
                    
                    stage_name = assignment.batch.lifecycle_stage.name
                    
                    # Skip feeding for Egg&Alevin stage
                    if stage_name == "Egg&Alevin":
                        continue
                    
                    # Get feed type for this stage
                    feed = self.get_feed_for_stage(stage_name)
                    if not feed:
                        continue
                    
                    # Get feed stock
                    try:
                        # Find a feed container near the batch container
                        if assignment.container.hall:
                            feed_containers = FeedContainer.objects.filter(hall=assignment.container.hall)
                        else:
                            feed_containers = FeedContainer.objects.filter(area=assignment.container.area)
                        
                        if not feed_containers:
                            # Fallback to any feed container
                            feed_containers = FeedContainer.objects.all()
                        
                        if not feed_containers:
                            raise Exception("No feed containers available")
                            
                        feed_container = random.choice(feed_containers)
                        feed_stock = FeedStock.objects.get(feed=feed, feed_container=feed_container)
                    except Exception as e:
                        print(f"Warning: {str(e)}. Skipping feed stock lookup.")
                        feed_stock = None
                    
                    # Calculate current biomass
                    biomass_kg = assignment.batch.biomass_kg
                    
                    # Determine feeding rate for this stage
                    daily_feeding_rate = self.get_feeding_rate_for_stage(stage_name)
                    
                    # Calculate total feed for the day and divide by feedings_per_day
                    total_daily_feed_kg = Decimal(str(float(biomass_kg) * daily_feeding_rate / 100))
                    feed_per_event_kg = total_daily_feed_kg / feedings_per_day
                    
                    # Apply some variation to each feeding (±10%)
                    for hour in feeding_hours:
                        variation = Decimal(str(random.uniform(0.9, 1.1)))
                        amount_kg = round(feed_per_event_kg * variation, 2)
                        
                        # Don't create feeding events with negligible amounts
                        if amount_kg < Decimal('0.01'):
                            continue
                        
                        # Create feeding time
                        feeding_time = datetime.time(
                            hour, 
                            random.randint(0, 59), 
                            random.randint(0, 59)
                        )
                        
                        # Calculate FCR
                        fcr = self.get_fcr_for_stage(stage_name)
                        
                        # Calculate feeding percentage
                        feeding_percentage = (amount_kg / biomass_kg) * 100
                        
                        # Create the feeding event
                        FeedingEvent.objects.create(
                            batch=assignment.batch,
                            batch_assignment=assignment,
                            container=assignment.container,
                            feed=feed,
                            feed_stock=feed_stock,
                            feeding_date=current_date,
                            feeding_time=feeding_time,
                            amount_kg=amount_kg,
                            batch_biomass_kg=biomass_kg,
                            feeding_percentage=feeding_percentage,
                            feed_conversion_ratio=fcr,
                            method='AUTOMATIC',
                            notes="Auto-generated feeding event for testing"
                        )
                        total_feedings += 1
                        
                        # Update feed stock if available
                        if feed_stock:
                            feed_stock.current_quantity_kg -= amount_kg
                            if feed_stock.current_quantity_kg < Decimal('0'):
                                feed_stock.current_quantity_kg = Decimal('0')
                            feed_stock.save()
            
            # Move to next day
            current_date += datetime.timedelta(days=1)
        
        print(f"Generated {total_feedings:,} feeding events from {start_date} to {end_date}")
        return total_feedings

    @transaction.atomic
    def update_current_inventory(self, as_of_date: date):
        """Update inventory levels for current year."""
        stocks = FeedStock.objects.all()
        updates = 0
        for stock in stocks:
            # Simulate inventory adjustment
            adjustment = Decimal(random.uniform(1000, 5000)) * Decimal('1.05')  # Using multiplier
            stock.current_quantity_kg += adjustment
            stock.last_updated = as_of_date
            stock.save()
            updates += 1
        logger.info(f"Updated {updates} inventory records")
        return updates
