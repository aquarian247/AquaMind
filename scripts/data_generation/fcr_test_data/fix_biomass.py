#!/usr/bin/env python3
"""
Fix Biomass Calculation Bug

This script corrects the biomass values in BatchContainerAssignment records.
The bug was storing individual fish weight instead of total biomass per container.
"""

import os
import sys
import django
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import BatchContainerAssignment, LifeCycleStage

def get_weight_for_stage(stage_name, days_into_stage):
    """Get estimated weight for a stage at given days"""
    if stage_name == 'Egg':
        return Decimal('0.001')  # 1mg eggs
    elif stage_name == 'Alevin':
        return Decimal('0.005')  # 5mg alevin
    elif stage_name == 'Fry':
        # Linear progression from 0.05g to 5g over 90 days
        progress = min(days_into_stage / 90, 1.0)
        return Decimal('0.05') + (Decimal('5') - Decimal('0.05')) * Decimal(str(progress))
    elif stage_name == 'Parr':
        # Linear progression from 5g to 50g over 90 days
        progress = min(days_into_stage / 90, 1.0)
        return Decimal('5') + (Decimal('50') - Decimal('5')) * Decimal(str(progress))
    elif stage_name == 'Smolt':
        # Linear progression from 50g to 150g over 90 days
        progress = min(days_into_stage / 90, 1.0)
        return Decimal('50') + (Decimal('150') - Decimal('50')) * Decimal(str(progress))
    elif stage_name == 'Post-Smolt':
        # Linear progression from 150g to 400g over 90 days
        progress = min(days_into_stage / 90, 1.0)
        return Decimal('150') + (Decimal('400') - Decimal('150')) * Decimal(str(progress))
    elif stage_name == 'Adult':
        # Linear progression from 400g to 6000g over 400 days
        progress = min(days_into_stage / 400, 1.0)
        return Decimal('400') + (Decimal('6000') - Decimal('400')) * Decimal(str(progress))
    else:
        return Decimal('1.0')  # Default

def fix_biomass_values():
    """Fix biomass values for all assignments"""
    print("Fixing biomass values...")

    assignments = BatchContainerAssignment.objects.select_related('batch', 'lifecycle_stage').order_by('assignment_date')

    fixed_count = 0
    total_old_biomass = Decimal('0')
    total_new_biomass = Decimal('0')

    for assignment in assignments:
        stage_name = assignment.lifecycle_stage.name
        days_into_stage = (assignment.assignment_date - assignment.batch.start_date).days

        # Calculate correct weight per fish (in grams)
        weight_per_fish_g = get_weight_for_stage(stage_name, days_into_stage)

        # Calculate correct biomass (population × weight_per_fish / 1000 for kg)
        correct_biomass = (assignment.population_count * weight_per_fish_g) / 1000

        old_biomass = assignment.biomass_kg or Decimal('0')
        total_old_biomass += old_biomass
        total_new_biomass += correct_biomass

        # Update the biomass
        assignment.biomass_kg = correct_biomass
        assignment.save()

        fixed_count += 1

        if fixed_count % 10 == 0:
            print(f"  Processed {fixed_count} assignments...")

    print(f"Fixed {fixed_count} assignments")
    print(".2f")
    print(".2f")
    print(".1f")

    return fixed_count, total_old_biomass, total_new_biomass

def verify_fix():
    """Verify the biomass fix worked"""
    print("\nVerifying biomass fix...")

    # Check adult stage specifically
    adult_assignments = BatchContainerAssignment.objects.filter(lifecycle_stage__name='Adult')
    total_adult_biomass = sum(a.biomass_kg or 0 for a in adult_assignments)
    avg_adult_biomass = total_adult_biomass / adult_assignments.count() if adult_assignments.count() > 0 else 0

    print("Adult stage verification:")
    print(f"  Containers: {adult_assignments.count()}")
    print(".2f")
    print(".2f")

    # Calculate expected biomass
    total_population = sum(a.population_count for a in adult_assignments)
    expected_biomass_per_fish = 6.0  # kg at harvest
    expected_total_biomass = total_population * expected_biomass_per_fish / 1000  # Convert to tons

    print("Expected values:")
    print(f"  Total population: {total_population:,}")
    print(".1f")
    print(".2f")

    return total_adult_biomass, expected_total_biomass

def main():
    """Main execution"""
    print("Starting Biomass Fix...")
    print("=" * 50)

    try:
        # Fix biomass values
        fixed_count, old_total, new_total = fix_biomass_values()

        # Verify the fix
        actual_biomass, expected_biomass = verify_fix()

        print("=" * 50)
        print("Biomass Fix Summary:")
        print(f"- Assignments fixed: {fixed_count}")
        print(".2f")
        print(".2f")
        print(".1f")

        if abs(actual_biomass - expected_biomass) / expected_biomass < 0.1:  # Within 10%
            print("✅ Biomass fix successful!")
        else:
            print("⚠️  Biomass values may still need adjustment")

    except Exception as e:
        print(f"Error during biomass fix: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
