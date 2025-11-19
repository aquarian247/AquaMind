#!/usr/bin/env python3
"""
Initialize Scenario Master Data

Ensures all foundational configuration data exists for scenario projections:
- Temperature profiles with readings for both geographies
- Lifecycle stage weight ranges for stage transitions
- TGC, FCR, Mortality models with stage-specific values
- Biological constraints (optional but recommended)

This should run ONCE after infrastructure setup, before any batch generation.

Usage:
    python scripts/data_generation/01_initialize_scenario_master_data.py
"""
import os, sys, django
import numpy as np
import random

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from decimal import Decimal
from apps.batch.models import LifeCycleStage, Species
from apps.scenario.models import (
    TemperatureProfile, TemperatureReading,
    TGCModel, FCRModel, MortalityModel,
    FCRModelStage, TGCModelStage, MortalityModelStage,
    BiologicalConstraints, StageConstraint
)
from apps.infrastructure.models import Geography
from django.contrib.auth import get_user_model

User = get_user_model()


def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def populate_lifecycle_weight_ranges():
    """
    Populate weight ranges for lifecycle stages.
    Required for scenario projection stage transitions.
    """
    print_section("LIFECYCLE STAGE WEIGHT RANGES")
    
    # Weight ranges based on industry standards and event engine caps
    weight_ranges = {
        'Egg&Alevin': (0.05, 0.5),     # Yolk sac stage, minimal growth
        'Fry': (0.5, 6),                # Early feeding, rapid growth
        'Parr': (6, 60),                # Freshwater growth phase
        'Smolt': (60, 180),             # Smoltification, prepare for sea
        'Post-Smolt': (180, 500),       # Early sea growth
        'Adult': (500, 7000),           # Grow-out to harvest (4-6kg typical)
    }
    
    updated = 0
    for stage in LifeCycleStage.objects.order_by('order'):
        if stage.name in weight_ranges:
            min_w, max_w = weight_ranges[stage.name]
            
            stage.expected_weight_min_g = Decimal(str(min_w))
            stage.expected_weight_max_g = Decimal(str(max_w))
            stage.save()
            
            print(f"✓ {stage.name:15s}: {min_w:7.2f}g - {max_w:7,.0f}g")
            updated += 1
        else:
            print(f"⚠ {stage.name:15s}: Unrecognized name (skipped)")
    
    print(f"\n✅ Updated {updated} lifecycle stages with weight ranges")


def populate_temperature_profiles():
    """
    Populate temperature profiles with realistic daily readings.
    Required for TGC growth calculations in scenarios.
    """
    print_section("TEMPERATURE PROFILES")
    
    # Get or create profiles for both geographies
    profiles_config = [
        ('Faroe Islands Sea Temperature', 'faroe', 9.5, 1.0),  # Stable Gulf Stream
        ('Scotland Sea Temperature', 'scotland', 10.0, 3.0),    # More variable
    ]
    
    created_profiles = 0
    populated_profiles = 0
    
    for profile_name, geo_type, base_temp, variation in profiles_config:
        profile, created = TemperatureProfile.objects.get_or_create(
            name=profile_name
        )
        
        if created:
            print(f"✓ Created profile: {profile_name}")
            created_profiles += 1
        
        # Check if readings exist
        existing_readings = TemperatureReading.objects.filter(profile=profile).count()
        
        if existing_readings == 0:
            print(f"  Generating 450 days of temperature data...")
            
            temps = []
            for day in range(450):
                if geo_type == 'faroe':
                    # Faroe: Stable Gulf Stream (8-11°C)
                    seasonal = variation * np.sin(2 * np.pi * day / 365)
                    daily_var = random.uniform(-0.3, 0.3)
                else:
                    # Scotland: Variable (6-14°C, peak in summer)
                    seasonal = variation * np.sin(2 * np.pi * (day - 90) / 365)
                    daily_var = random.uniform(-0.5, 0.5)
                
                temp = base_temp + seasonal + daily_var
                temps.append(max(6.0, min(14.0, temp)))
            
            # Bulk create
            readings = [
                TemperatureReading(
                    profile=profile,
                    day_number=i + 1,
                    temperature=temps[i]
                )
                for i in range(450)
            ]
            TemperatureReading.objects.bulk_create(readings, batch_size=500)
            
            avg_temp = sum(temps) / len(temps)
            print(f"  ✓ Created {len(readings)} readings (avg: {avg_temp:.1f}°C)")
            populated_profiles += 1
        else:
            print(f"  ✓ {profile_name}: Already has {existing_readings} readings")
    
    print(f"\n✅ {created_profiles} profiles created, {populated_profiles} profiles populated")


def populate_biological_constraints():
    """
    Create BiologicalConstraints with stage-specific rules.
    Provides time-based AND weight-based stage transition logic.
    """
    print_section("BIOLOGICAL CONSTRAINTS")
    
    # Create Bakkafrost Standard constraint set
    bc, created = BiologicalConstraints.objects.get_or_create(
        name='Bakkafrost Standard',
        defaults={
            'description': 'Standard biological constraints for Bakkafrost operations',
            'is_active': True
        }
    )
    
    if created:
        print(f"✓ Created constraint set: {bc.name}")
    else:
        print(f"  Constraint set exists: {bc.name}")
    
    # Define stage constraints (time AND weight based)
    stage_configs = [
        # (stage_name, min_weight, max_weight, min_days, max_days, max_fw_days)
        ('Egg&Alevin', 0.05, 0.5, 60, 100, 90),
        ('Fry', 0.5, 6, 70, 110, 90),
        ('Parr', 6, 60, 70, 110, 90),
        ('Smolt', 60, 180, 70, 110, 90),
        ('Post-Smolt', 180, 500, 70, 110, 90),
        ('Adult', 500, 7000, 400, 600, None),  # No freshwater limit for Adult
    ]
    
    stages_created = 0
    for stage_name, min_w, max_w, min_d, max_d, max_fw in stage_configs:
        stage = LifeCycleStage.objects.filter(name=stage_name).first()
        if not stage:
            print(f"  ⚠ Stage '{stage_name}' not found, skipping")
            continue
        
        sc, created = StageConstraint.objects.get_or_create(
            constraint_set=bc,  # FIX: Use correct FK name
            lifecycle_stage=stage,
            defaults={
                'min_weight_g': Decimal(str(min_w)),
                'max_weight_g': Decimal(str(max_w)),
                'typical_duration_days': (min_d + max_d) // 2,  # Use average
                'max_freshwater_weight_g': Decimal(str(max_w)) if max_fw else None
            }
        )
        
        if created:
            print(f"  ✓ {stage_name:15s}: {min_w}g-{max_w}g, {min_d}-{max_d} days")
            stages_created += 1
    
    print(f"\n✅ Created {stages_created} stage constraints")


def verify_scenario_dependencies():
    """
    Verify all scenario dependencies are properly configured.
    """
    print_section("SCENARIO DEPENDENCY VERIFICATION")
    
    checks = []
    
    # 1. Temperature Profiles
    profiles = TemperatureProfile.objects.all()
    profiles_with_data = sum(
        1 for p in profiles 
        if TemperatureReading.objects.filter(profile=p).exists()
    )
    checks.append(("Temperature Profiles with data", profiles_with_data, profiles.count()))
    
    # 2. Lifecycle Stages with weight ranges
    stages = LifeCycleStage.objects.all()
    stages_with_ranges = stages.exclude(
        expected_weight_min_g__isnull=True
    ).exclude(
        expected_weight_max_g__isnull=True
    ).count()
    checks.append(("Lifecycle Stages with weight ranges", stages_with_ranges, stages.count()))
    
    # 3. TGC Models
    tgc_count = TGCModel.objects.count()
    checks.append(("TGC Models", tgc_count, 2))
    
    # 4. FCR Models with stage data
    fcr_models = FCRModel.objects.all()
    fcr_with_stages = sum(
        1 for m in fcr_models 
        if FCRModelStage.objects.filter(model=m).count() >= 6
    )
    checks.append(("FCR Models with all 6 stages", fcr_with_stages, fcr_models.count()))
    
    # 5. Mortality Models
    mort_count = MortalityModel.objects.count()
    checks.append(("Mortality Models", mort_count, 1))
    
    # 6. Biological Constraints (optional)
    bc_count = BiologicalConstraints.objects.count()
    checks.append(("Biological Constraint Sets", bc_count, 1))
    
    all_good = True
    for name, actual, expected in checks:
        if actual >= expected:
            print(f"✓ {name}: {actual}/{expected}")
        else:
            print(f"⚠ {name}: {actual}/{expected} (missing {expected - actual})")
            all_good = False
    
    if all_good:
        print(f"\n✅ All scenario dependencies properly configured!")
    else:
        print(f"\n⚠️  Some dependencies missing or incomplete")
    
    return all_good


def main():
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Scenario Master Data Initialization".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Step 1: Populate lifecycle weight ranges
        populate_lifecycle_weight_ranges()
        
        # Step 2: Populate temperature profiles
        populate_temperature_profiles()
        
        # Step 3: Create biological constraints (optional - skip if fails)
        try:
            populate_biological_constraints()
        except Exception as e:
            print(f"\n⚠️  BiologicalConstraints creation failed (optional): {e}")
            print("   Continuing without biological constraints...")
        
        # Step 4: Verify everything
        all_good = verify_scenario_dependencies()
        
        print_section("INITIALIZATION COMPLETE")
        
        if all_good:
            print("✅ All scenario master data initialized successfully!")
            print("\nScenarios can now:")
            print("  ✓ Transition through lifecycle stages correctly")
            print("  ✓ Calculate TGC-based growth with temperature data")
            print("  ✓ Apply stage-specific FCR and mortality rates")
            print("  ✓ Generate realistic 900-day projections (0.1g → 5000g)")
            print("\nNext steps:")
            print("  1. Generate test batches with scenarios")
            print("  2. Scenarios will automatically compute projection data")
            print("  3. UI will show all 3 series on Growth Analysis chart")
        else:
            print("⚠️  Some configuration missing - review output above")
            print("\nYou may need to:")
            print("  - Run Phase 2 master data initialization")
            print("  - Create additional TGC models")
            print("  - Verify species and lifecycle stages exist")
        
        return 0 if all_good else 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

