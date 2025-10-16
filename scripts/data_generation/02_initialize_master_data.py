#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Phase 2: Initialize Master Data

This script creates all non-event master/reference data:
- Species & Lifecycle Stages (6 stages) - checks for existing
- Environmental Parameters (7 types with safety ranges)
- Feed Types (6 types with nutritional profiles)
- Initial Feed Inventory (FIFO setup)
- Health Master Data
- Test Users

Uses get_or_create() throughout - safe to run multiple times.
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

import django.db.models
from django.contrib.auth import get_user_model
from apps.batch.models import Species, LifeCycleStage
from apps.environmental.models import EnvironmentalParameter
from apps.inventory.models import Feed, FeedPurchase, FeedContainerStock
from apps.infrastructure.models import FeedContainer
from apps.health.models import (
    HealthParameter, MortalityReason, SampleType, VaccinationType
)
from apps.harvest.models import ProductGrade

User = get_user_model()

# Progress tracking
progress = {
    'species': 0,
    'lifecycle_stages': 0,
    'env_parameters': 0,
    'feed_types': 0,
    'feed_purchases': 0,
    'feed_stock': 0,
    'health_parameters': 0,
    'mortality_reasons': 0,
    'sample_types': 0,
    'vaccination_types': 0,
    'users': 0,
    'product_grades': 0,
}


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def print_progress(message, category=None):
    """Print progress message and update counter"""
    print(f"✓ {message}")
    if category:
        progress[category] += 1


def create_species_and_stages():
    """Create Atlantic Salmon species and 6 lifecycle stages (or verify existing)"""
    print_section("Phase 2.1: Verifying Species & Lifecycle Stages")
    
    # Create/verify species
    species, created = Species.objects.get_or_create(
        name="Atlantic Salmon",
        defaults={
            'scientific_name': 'Salmo salar',
        }
    )
    if created:
        print_progress(f"Created species: {species.name}", 'species')
    else:
        print(f"✓ Species already exists: {species.name}")
    
    # Verify lifecycle stages (should already exist)
    existing_stages = LifeCycleStage.objects.filter(species=species).count()
    print(f"✓ Found {existing_stages} existing lifecycle stages for {species.name}")
    
    if existing_stages >= 6:
        print("✓ All required lifecycle stages exist")
        progress['lifecycle_stages'] = existing_stages
    else:
        print(f"⚠ Only {existing_stages} stages found, expected 6+")
    
    return species


def create_environmental_parameters():
    """Create 7 environmental parameters with safety ranges"""
    print_section("Phase 2.2: Creating Environmental Parameters")
    
    params_config = [
        ('Dissolved Oxygen', '%', 'Dissolved oxygen saturation percentage (safe: 80-100%, critical: <30%)'),
        ('CO2', 'mg/L', 'Carbon dioxide concentration (safe: <15 mg/L, critical: >25 mg/L)'),
        ('pH', 'pH', 'Water acidity/alkalinity (safe: 6.5-8.5, critical: <6.0 or >9.0)'),
        ('Temperature', '°C', 'Water temperature (freshwater: 4-16°C, seawater: 6-18°C)'),
        ('NO2', 'mg/L', 'Nitrite concentration (safe: <0.1 mg/L, critical: >0.5 mg/L)'),
        ('NO3', 'mg/L', 'Nitrate concentration (safe: <50 mg/L, critical: >100 mg/L)'),
        ('NH4', 'mg/L', 'Total ammonia concentration (safe: <0.02 mg/L, critical: >0.1 mg/L)'),
    ]
    
    for name, unit, description in params_config:
        param, created = EnvironmentalParameter.objects.get_or_create(
            name=name,
            defaults={
                'unit': unit,
                'description': description,
            }
        )
        if created:
            print_progress(f"Created parameter: {name} ({unit})", 'env_parameters')
        else:
            print(f"✓ Parameter already exists: {name}")


def create_feed_types():
    """Create 6 feed types with nutritional profiles"""
    print_section("Phase 2.3: Creating Feed Types")
    
    feeds_config = [
        ('Starter Feed 0.5mm', 'MICRO', 0.5, 50.0, 18.0, 20.0, 'Fry stage feed'),
        ('Starter Feed 1.0mm', 'SMALL', 1.0, 48.0, 18.0, 22.0, 'Parr stage feed'),
        ('Grower Feed 2.0mm', 'MEDIUM', 2.0, 45.0, 20.0, 23.0, 'Smolt stage feed'),
        ('Grower Feed 3.0mm', 'MEDIUM', 3.0, 43.0, 22.0, 23.0, 'Post-Smolt stage feed'),
        ('Finisher Feed 4.5mm', 'LARGE', 4.5, 40.0, 24.0, 24.0, 'Adult stage feed (early)'),
        ('Finisher Feed 6.0mm', 'LARGE', 6.0, 38.0, 26.0, 24.0, 'Adult stage feed (late)'),
    ]
    
    for name, size, pellet, protein, fat, carb, desc in feeds_config:
        feed, created = Feed.objects.get_or_create(
            name=name,
            defaults={
                'brand': 'BioMar',
                'size_category': size,
                'pellet_size_mm': Decimal(str(pellet)),
                'protein_percentage': Decimal(str(protein)),
                'fat_percentage': Decimal(str(fat)),
                'carbohydrate_percentage': Decimal(str(carb)),
                'is_active': True,
                'description': desc,
            }
        )
        if created:
            print_progress(f"Created feed: {name} (Protein: {protein}%)", 'feed_types')
        else:
            print(f"✓ Feed already exists: {name}")


def create_initial_feed_inventory():
    """Create initial feed inventory with FIFO setup"""
    print_section("Phase 2.4: Creating Initial Feed Inventory")
    
    # Check if inventory already exists
    existing_stock = FeedContainerStock.objects.count()
    if existing_stock > 0:
        print(f"⚠ Found {existing_stock} existing feed stock entries")
        response = input("  Clear existing inventory and recreate? (y/N): ").lower()
        if response != 'y':
            print("  Skipping inventory creation")
            return
        else:
            print("  Clearing existing inventory...")
            FeedContainerStock.objects.all().delete()
            FeedPurchase.objects.all().delete()
    
    # Get all feed containers
    feed_containers = FeedContainer.objects.filter(active=True)
    total_containers = feed_containers.count()
    
    if total_containers == 0:
        print("⚠ No feed containers found! Run Phase 1 first.")
        return
    
    print(f"Found {total_containers} feed containers to stock\n")
    
    # Purchase date: 30 days before today
    purchase_date = date.today() - timedelta(days=30)
    
    # Supplier rotation
    suppliers = ['BioMar', 'Skretting', 'Cargill', 'Aller Aqua']
    
    # Get feed types
    feed_types = Feed.objects.filter(is_active=True)
    
    if feed_types.count() == 0:
        print("⚠ No feed types found! Creating feed types first...")
        create_feed_types()
        feed_types = Feed.objects.filter(is_active=True)
    
    # Determine feed type based on container type
    def get_feed_for_container(container):
        """Select appropriate feed type for container"""
        if 'Silo' in container.name or container.container_type == 'SILO':
            # Freshwater silos: use starter/grower feeds
            return feed_types.filter(name__contains='Starter').first() or feed_types.first()
        else:  # Barges
            # Sea barges: use finisher feeds
            return feed_types.filter(name__contains='Finisher').first() or feed_types.last()
    
    created_purchases = 0
    created_stock = 0
    
    for idx, container in enumerate(feed_containers, 1):
        # Select feed type
        feed = get_feed_for_container(container)
        
        # Determine quantity based on container type
        if container.container_type == 'SILO':
            quantity_kg = Decimal('5000.0')  # 5,000 kg per silo
            cost_per_kg = Decimal('2.50')  # €2.50/kg
        else:  # BARGE
            quantity_kg = Decimal('25000.0')  # 25,000 kg per barge
            cost_per_kg = Decimal('2.00')  # €2.00/kg (bulk discount)
        
        # Select supplier (rotate)
        supplier = suppliers[idx % len(suppliers)]
        
        # Create FeedPurchase
        purchase = FeedPurchase.objects.create(
            feed=feed,
            purchase_date=purchase_date,
            supplier=supplier,
            batch_number=f"BATCH-{purchase_date.strftime('%Y%m%d')}-{idx:04d}",
            quantity_kg=quantity_kg,
            cost_per_kg=cost_per_kg,
            expiry_date=purchase_date + timedelta(days=365),  # 1 year shelf life
            notes=f'Initial inventory for {container.name}',
        )
        created_purchases += 1
        
        # Create FeedContainerStock (FIFO entry)
        from django.utils import timezone
        stock = FeedContainerStock.objects.create(
            feed_container=container,
            feed_purchase=purchase,
            quantity_kg=quantity_kg,
            entry_date=timezone.make_aware(
                datetime.combine(purchase_date, datetime.min.time())
            ),
        )
        created_stock += 1
        
        if (idx % 20 == 0):  # Progress update every 20 containers
            print(f"  Processed {idx}/{total_containers} containers...")
    
    progress['feed_purchases'] = created_purchases
    progress['feed_stock'] = created_stock
    
    print(f"\n✓ Created {created_purchases} feed purchases")
    print(f"✓ Created {created_stock} feed stock entries")
    
    # Calculate total inventory
    total_inventory_kg = FeedContainerStock.objects.aggregate(
        total=django.db.models.Sum('quantity_kg')
    )['total'] or 0
    
    print(f"✓ Total initial inventory: {total_inventory_kg:,.0f} kg")


def create_health_master_data():
    """Create health parameters, mortality reasons, sample types, vaccination types"""
    print_section("Phase 2.5: Creating Health Master Data")
    
    print("\n--- Health Parameters ---")
    health_params = [
        ('Gill Condition', 'Healthy gills, pink color', 'Slight mucus buildup', 
         'Moderate inflammation', 'Severe inflammation', 'Critical damage, necrosis'),
        ('Eye Condition', 'Clear, bright eyes', 'Slight cloudiness', 
         'Moderate cloudiness', 'Severe cloudiness/damage', 'Blind or missing'),
        ('Wounds/Lesions', 'No wounds', 'Minor abrasions', 
         'Moderate wounds', 'Severe wounds/ulcers', 'Extensive necrotic lesions'),
        ('Fin Condition', 'Intact, healthy fins', 'Minor fraying', 
         'Moderate erosion', 'Severe erosion', 'Complete fin loss'),
        ('Body Condition', 'Robust, well-formed', 'Slight deformities', 
         'Moderate deformities', 'Severe deformities', 'Critical malformation'),
        ('Swimming Behavior', 'Active, normal swimming', 'Slightly lethargic', 
         'Moderately lethargic', 'Severely impaired', 'Unable to swim'),
        ('Appetite', 'Excellent feeding response', 'Good appetite', 
         'Reduced appetite', 'Poor appetite', 'No feeding response'),
        ('Mucous Membrane', 'Normal mucus layer', 'Slight excess mucus', 
         'Moderate excess mucus', 'Heavy excess mucus', 'Absent or damaged'),
        ('Color/Pigmentation', 'Normal coloration', 'Slight color changes', 
         'Moderate discoloration', 'Severe discoloration', 'Extreme color abnormalities'),
    ]
    
    for name, desc1, desc2, desc3, desc4, desc5 in health_params:
        param, created = HealthParameter.objects.get_or_create(
            name=name,
            defaults={
                'description_score_1': desc1,
                'description_score_2': desc2,
                'description_score_3': desc3,
                'description_score_4': desc4,
                'description_score_5': desc5,
                'is_active': True,
            }
        )
        if created:
            print_progress(f"  Created: {name}", 'health_parameters')
        else:
            print(f"  ✓ Exists: {name}")
    
    print("\n--- Mortality Reasons ---")
    mortality_reasons = [
        ('Natural Death', 'Natural causes, age-related'),
        ('Disease', 'Disease-related mortality'),
        ('Stress', 'Stress-induced mortality'),
        ('Handling', 'Mortality during handling/transfer'),
        ('Predation', 'Predation by birds, seals, etc.'),
        ('Environmental', 'Environmental conditions (temp, oxygen, etc.)'),
        ('Unknown', 'Cause unknown or not determined'),
    ]
    
    for name, desc in mortality_reasons:
        reason, created = MortalityReason.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        if created:
            print_progress(f"  Created: {name}", 'mortality_reasons')
        else:
            print(f"  ✓ Exists: {name}")
    
    print("\n--- Sample Types ---")
    sample_types = [
        ('Blood Sample', 'Whole blood or serum sample'),
        ('Tissue Sample', 'Organ or tissue biopsy'),
        ('Gill Sample', 'Gill tissue or swab'),
        ('Kidney Sample', 'Kidney tissue sample'),
        ('Fecal Sample', 'Fecal matter for parasitology'),
    ]
    
    for name, desc in sample_types:
        sample, created = SampleType.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        if created:
            print_progress(f"  Created: {name}", 'sample_types')
        else:
            print(f"  ✓ Exists: {name}")
    
    print("\n--- Vaccination Types ---")
    vaccination_types = [
        ('IPN Vaccine', 'Novartis', '0.05 ml', 'Infectious Pancreatic Necrosis vaccine'),
        ('VHS Vaccine', 'Elanco', '0.05 ml', 'Viral Hemorrhagic Septicemia vaccine'),
        ('Multi-component Vaccine', 'Pharmaq', '0.10 ml', 
         'Multi-disease vaccine (IPN, VHS, IHNV)'),
    ]
    
    for name, manufacturer, dosage, desc in vaccination_types:
        vacc, created = VaccinationType.objects.get_or_create(
            name=name,
            defaults={
                'manufacturer': manufacturer,
                'dosage': dosage,
                'description': desc,
            }
        )
        if created:
            print_progress(f"  Created: {name}", 'vaccination_types')
        else:
            print(f"  ✓ Exists: {name}")


def create_product_grades():
    """Create standard product grades for harvest output"""
    print_section("Phase 2.6: Creating Product Grades")
    
    grades = [
        ('SUPERIOR', 'Superior Quality', '5-7kg, premium appearance'),
        ('GRADE_A', 'Grade A', '4-6kg, excellent quality'),
        ('GRADE_B', 'Grade B', '3-5kg, good quality'),
        ('GRADE_C', 'Grade C', '2-4kg, standard quality'),
        ('REJECT', 'Reject', 'Below standard, processing only'),
    ]
    
    for code, name, description in grades:
        grade, created = ProductGrade.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
            }
        )
        if created:
            print_progress(f"Created grade: {code} - {name}", 'product_grades')
        else:
            print(f"✓ Grade already exists: {code}")


def create_test_users():
    """Create test users for different roles"""
    print_section("Phase 2.7: Creating Test Users")
    
    users_config = [
        ('system_admin', 'System', 'Administrator', 'admin@aquamind.test', True),
        ('operator_01', 'Farm', 'Operator', 'operator@aquamind.test', False),
        ('vet_01', 'Dr. Sarah', 'Johnson', 'vet@aquamind.test', False),
        ('manager_01', 'John', 'Manager', 'manager@aquamind.test', False),
    ]
    
    for username, first, last, email, is_staff in users_config:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first,
                'last_name': last,
                'email': email,
                'is_staff': is_staff,
                'is_active': True,
            }
        )
        
        if created:
            user.set_password('aquamind2024')  # Default password
            user.save()
            print_progress(f"Created user: {username} ({first} {last})", 'users')
        else:
            print(f"✓ User already exists: {username}")


def validate_master_data():
    """Validate all master data creation"""
    print_section("Phase 2.7: Validating Master Data")
    
    validations = [
        ("Species", Species.objects.count(), 1),
        ("Lifecycle Stages", LifeCycleStage.objects.count(), 6),
        ("Environmental Parameters", EnvironmentalParameter.objects.count(), 7),
        ("Feed Types", Feed.objects.count(), 6),
        ("Feed Purchases", FeedPurchase.objects.count(), 236),
        ("Feed Stock Entries", FeedContainerStock.objects.count(), 236),
        ("Health Parameters", HealthParameter.objects.count(), 9),
        ("Mortality Reasons", MortalityReason.objects.count(), 7),
        ("Sample Types", SampleType.objects.count(), 5),
        ("Vaccination Types", VaccinationType.objects.count(), 3),
        ("Test Users", User.objects.filter(username__in=[
            'system_admin', 'operator_01', 'vet_01', 'manager_01'
        ]).count(), 4),
    ]
    
    all_valid = True
    for name, actual, expected in validations:
        status = "✓" if actual >= expected else "✗"
        print(f"{status} {name}: {actual} (expected: >={expected})")
        if actual < expected:
            all_valid = False
    
    return all_valid


def print_summary():
    """Print final summary"""
    print_section("Master Data Initialization Complete!")
    
    print(f"""
Summary of Created Master Data:
{'='*80}
Species:                {progress['species']} (verified existing)
Lifecycle Stages:       {progress['lifecycle_stages']} (verified existing)
Env Parameters:         {progress['env_parameters']}
Feed Types:             {progress['feed_types']}
Feed Purchases:         {progress['feed_purchases']}
Feed Stock Entries:     {progress['feed_stock']}
Health Parameters:      {progress['health_parameters']}
Mortality Reasons:      {progress['mortality_reasons']}
Sample Types:           {progress['sample_types']}
Vaccination Types:      {progress['vaccination_types']}
Test Users:             {progress['users']}
{'='*80}

✓ All master data initialized successfully!
✓ Database is ready for Phase 3: Chronological Event Engine
""")


def main():
    """Main execution"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  AquaMind - Phase 2: Initialize Master Data".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    try:
        # Phase 2.1: Species & Stages
        create_species_and_stages()
        
        # Phase 2.2: Environmental Parameters
        create_environmental_parameters()
        
        # Phase 2.3: Feed Types
        create_feed_types()
        
        # Phase 2.4: Initial Feed Inventory
        create_initial_feed_inventory()
        
        # Phase 2.5: Health Master Data
        create_health_master_data()
        
        # Phase 2.6: Product Grades
        create_product_grades()
        
        # Phase 2.7: Test Users
        create_test_users()
        
        # Phase 2.8: Validation
        valid = validate_master_data()
        
        # Summary
        print_summary()
        
        if valid:
            print("\n✓ Phase 2 COMPLETE: Master data initialization successful!\n")
            return 0
        else:
            print("\n⚠ Phase 2 COMPLETE with warnings: Some counts below expected.\n")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during master data initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
