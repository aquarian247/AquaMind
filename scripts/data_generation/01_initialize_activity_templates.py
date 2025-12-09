#!/usr/bin/env python3
"""
Initialize Activity Templates for Operational Scheduling.

This script creates standard lifecycle activity templates for Atlantic salmon
production. Templates define the operational rhythm for batches and are used
to auto-generate PlannedActivity records when new batches are created.

Templates are aligned with:
- Stage durations: ~90 days freshwater stages, 300-450 days Adult
- Feed progression: Starter (0.5mm, 1.0mm) → Grower (2.0mm, 3.0mm) → Finisher (4.5mm, 6.0mm)
- Single vaccination before smoltification (Parr → Smolt transfer)
- Lice treatments in Adult sea stage
- Harvest at target weight (~5kg, typically Day 750-850)

Lifecycle Timeline (900 days total):
- Day 0-89: Egg/Alevin (order=1) - NO FEED, incubation only
- Day 90-179: Fry (order=2) - First feeding, Starter Feed 0.5mm → 1.0mm
- Day 180-269: Parr (order=3) - Grower Feed 2.0mm
- Day 270-359: Smolt (order=4) - Grower Feed 3.0mm, freshwater
- Day 360-449: Post-Smolt (order=5) - Sea transfer, Finisher Feed 4.5mm
- Day 450-900: Adult (order=6) - Grow-out, Finisher Feed 6.0mm, harvest

Usage:
    python scripts/data_generation/01_initialize_activity_templates.py
    python scripts/data_generation/01_initialize_activity_templates.py --dry-run
"""
import os
import sys
import argparse
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from django.db import transaction
from apps.planning.models import ActivityTemplate
from apps.batch.models.species import LifeCycleStage


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================
# Based on realistic Atlantic salmon lifecycle
# Stage order: 1=Egg&Alevin, 2=Fry, 3=Parr, 4=Smolt, 5=Post-Smolt, 6=Adult

ACTIVITY_TEMPLATES = [
    # =========================================================================
    # STAGE TRANSFERS (5 transfers in lifecycle)
    # =========================================================================
    {
        'name': 'Stage Transfer: Egg/Alevin → Fry',
        'description': 'Transfer from incubation to first feeding tanks. Marks start of active feeding phase.',
        'activity_type': 'TRANSFER',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 90,
        'target_lifecycle_stage_order': 2,  # To Fry
        'notes_template': 'Transfer from Egg/Alevin incubators to Fry tanks. Begin first feeding with Starter Feed 0.5mm.',
    },
    {
        'name': 'Stage Transfer: Fry → Parr',
        'description': 'Transfer to Parr stage tanks. Fish developing parr marks.',
        'activity_type': 'TRANSFER',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 180,
        'target_lifecycle_stage_order': 3,  # To Parr
        'notes_template': 'Transfer from Fry to Parr tanks. Continue with Grower Feed 2.0mm.',
    },
    {
        'name': 'Stage Transfer: Parr → Smolt (Smoltification)',
        'description': 'Critical transfer marking smoltification. Fish adapting to seawater.',
        'activity_type': 'TRANSFER',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 270,
        'target_lifecycle_stage_order': 4,  # To Smolt
        'notes_template': 'Smoltification transfer. Fish undergoing physiological adaptation for seawater. Verify silver coloration and readiness.',
    },
    {
        'name': 'Stage Transfer: Smolt → Post-Smolt (Sea Transfer)',
        'description': 'Transfer from freshwater to sea cages. Major logistics event.',
        'activity_type': 'TRANSFER',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 360,
        'target_lifecycle_stage_order': 5,  # To Post-Smolt
        'notes_template': 'Sea transfer from freshwater facility to sea cages. Coordinate wellboat, verify stocking density, monitor stress indicators.',
    },
    {
        'name': 'Stage Transfer: Post-Smolt → Adult',
        'description': 'Transfer to adult grow-out phase in sea cages.',
        'activity_type': 'TRANSFER',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 450,
        'target_lifecycle_stage_order': 6,  # To Adult
        'notes_template': 'Transition to Adult grow-out stage. Begin monitoring for harvest readiness.',
    },
    
    # =========================================================================
    # VACCINATION (1 only - before smoltification)
    # =========================================================================
    {
        'name': 'Pre-Smoltification Vaccination',
        'description': 'Single vaccination event before Parr → Smolt transfer. Protects against IPN, PD, and other diseases.',
        'activity_type': 'VACCINATION',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 265,  # 5 days before smoltification transfer
        'notes_template': 'Administer combined vaccine (IPN, PD, Vibriosis). Allow 5 days recovery before smoltification transfer.',
    },
    
    # =========================================================================
    # FEED CHANGES (aligned with feed types in inventory)
    # Feed types: Starter 0.5mm, Starter 1.0mm, Grower 2.0mm, Grower 3.0mm, Finisher 4.5mm, Finisher 6.0mm
    # =========================================================================
    {
        'name': 'Feed Change: Start First Feeding (0.5mm)',
        'description': 'Begin first feeding as fish transition from Egg/Alevin to Fry.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 90,  # Same day as Egg/Alevin → Fry transfer
        'notes_template': 'Start first feeding with Starter Feed 0.5mm. Monitor feeding response closely for first 7 days.',
    },
    {
        'name': 'Feed Change: Upgrade to Starter 1.0mm',
        'description': 'Increase pellet size as Fry grow.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 135,  # Mid-Fry stage
        'notes_template': 'Transition to Starter Feed 1.0mm. Typical fish weight: 2-5g.',
    },
    {
        'name': 'Feed Change: Upgrade to Grower 2.0mm',
        'description': 'Transition to grower feed as fish enter Parr stage.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 180,  # Same day as Fry → Parr transfer
        'notes_template': 'Transition to Grower Feed 2.0mm. Typical fish weight: 10-20g.',
    },
    {
        'name': 'Feed Change: Upgrade to Grower 3.0mm',
        'description': 'Increase pellet size during Smolt stage.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 315,  # Mid-Smolt stage
        'notes_template': 'Transition to Grower Feed 3.0mm. Typical fish weight: 50-80g.',
    },
    {
        'name': 'Feed Change: Upgrade to Finisher 4.5mm',
        'description': 'Transition to finisher feed after sea transfer.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 405,  # Mid-Post-Smolt stage
        'notes_template': 'Transition to Finisher Feed 4.5mm. Typical fish weight: 200-500g.',
    },
    {
        'name': 'Feed Change: Upgrade to Finisher 6.0mm',
        'description': 'Final pellet size for adult grow-out.',
        'activity_type': 'FEED_CHANGE',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 550,  # Early Adult stage
        'notes_template': 'Transition to Finisher Feed 6.0mm. Typical fish weight: 1.5-2.5kg.',
    },
    
    # =========================================================================
    # SAMPLING (key milestones only - monthly sampling is operational, not planned)
    # =========================================================================
    {
        'name': 'Pre-Transfer Growth Sampling: Fry → Parr',
        'description': 'Growth sampling before Fry to Parr transfer.',
        'activity_type': 'SAMPLING',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 175,  # 5 days before transfer
        'notes_template': 'Sample 50 fish for weight/length. Verify readiness for Parr stage transfer.',
    },
    {
        'name': 'Pre-Vaccination Health Sampling',
        'description': 'Health assessment before vaccination.',
        'activity_type': 'SAMPLING',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 260,  # 5 days before vaccination
        'notes_template': 'Health sampling to verify fish condition before vaccination. Sample 30 fish.',
    },
    {
        'name': 'Pre-Sea Transfer Sampling',
        'description': 'Comprehensive sampling before sea transfer.',
        'activity_type': 'SAMPLING',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 355,  # 5 days before sea transfer
        'notes_template': 'Pre-sea transfer sampling. Sample 75 fish for weight, length, and smolt index. Verify seawater readiness.',
    },
    {
        'name': 'Mid-Cycle Growth Assessment',
        'description': 'Growth assessment at mid-point of sea grow-out.',
        'activity_type': 'SAMPLING',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 600,  # Mid Adult stage
        'notes_template': 'Mid-cycle growth assessment. Sample 75 fish. Update harvest date projections based on TGC.',
    },
    {
        'name': 'Pre-Harvest Quality Sampling',
        'description': 'Quality assessment before harvest.',
        'activity_type': 'SAMPLING',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 780,  # ~2-3 weeks before typical harvest
        'notes_template': 'Pre-harvest quality sampling. Sample 50 fish for weight distribution, fillet quality, and maturation status.',
    },
    
    # =========================================================================
    # TREATMENTS (Lice treatments in Adult sea stage)
    # =========================================================================
    {
        'name': 'Lice Treatment #1',
        'description': 'First scheduled lice treatment in Adult stage.',
        'activity_type': 'TREATMENT',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 520,  # Early Adult stage
        'notes_template': 'Scheduled lice treatment. Options: Thermolicer, hydrogen peroxide bath, or mechanical delousing. Record lice counts before and after.',
    },
    {
        'name': 'Lice Treatment #2',
        'description': 'Second scheduled lice treatment in Adult stage.',
        'activity_type': 'TREATMENT',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 650,  # Mid Adult stage
        'notes_template': 'Scheduled lice treatment. Rotate treatment method if resistance suspected. Record lice counts before and after.',
    },
    
    # =========================================================================
    # HARVEST (lifecycle endpoint)
    # =========================================================================
    {
        'name': 'Planned Harvest',
        'description': 'Target harvest date based on growth projections. Typical weight: 4.5-6kg.',
        'activity_type': 'HARVEST',
        'trigger_type': 'DAY_OFFSET',
        'day_offset': 800,  # Typical harvest timing
        'weight_threshold_g': Decimal('5000.00'),  # 5kg target
        'notes_template': 'Planned harvest. Coordinate wellboat, processing plant capacity, and market timing. Target weight: 5kg. Verify withdrawal periods for any treatments.',
    },
]


def create_activity_templates(dry_run=False):
    """Create all activity templates."""
    print("=" * 80)
    print("INITIALIZE ACTIVITY TEMPLATES")
    print("=" * 80)
    print()
    
    if dry_run:
        print("DRY RUN - No records will be created")
        print()
    
    # Get lifecycle stages for linking
    stages = {s.order: s for s in LifeCycleStage.objects.all()}
    
    if not stages:
        print("❌ Error: No lifecycle stages found. Run 01_bootstrap_infrastructure.py first.")
        return {'success': False, 'error': 'no lifecycle stages'}
    
    print(f"Found {len(stages)} lifecycle stages:")
    for order, stage in sorted(stages.items()):
        print(f"  Order {order}: {stage.name}")
    print()
    
    created = 0
    updated = 0
    skipped = 0
    
    for template_data in ACTIVITY_TEMPLATES:
        name = template_data['name']
        
        # Extract target stage if specified
        target_stage = None
        if 'target_lifecycle_stage_order' in template_data:
            order = template_data.pop('target_lifecycle_stage_order')
            target_stage = stages.get(order)
            if not target_stage:
                print(f"⚠️  Warning: No stage found for order {order}, skipping target_lifecycle_stage")
        
        # Check if template exists
        existing = ActivityTemplate.objects.filter(name=name).first()
        
        if dry_run:
            if existing:
                print(f"  Would UPDATE: {name}")
                updated += 1
            else:
                print(f"  Would CREATE: {name}")
                created += 1
            continue
        
        if existing:
            # Update existing template
            for key, value in template_data.items():
                if key != 'name':
                    setattr(existing, key, value)
            if target_stage:
                existing.target_lifecycle_stage = target_stage
            existing.save()
            print(f"  ✅ Updated: {name}")
            updated += 1
        else:
            # Create new template
            template = ActivityTemplate(
                **template_data,
                target_lifecycle_stage=target_stage
            )
            template.save()
            print(f"  ✅ Created: {name}")
            created += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Templates created: {created}")
    print(f"Templates updated: {updated}")
    print(f"Templates skipped: {skipped}")
    print(f"Total templates: {ActivityTemplate.objects.count()}")
    print()
    
    if not dry_run:
        print("✅ ACTIVITY TEMPLATES INITIALIZED SUCCESSFULLY")
    
    return {
        'success': True,
        'created': created,
        'updated': updated,
        'total': ActivityTemplate.objects.count()
    }


def main():
    parser = argparse.ArgumentParser(
        description='Initialize Activity Templates for Operational Scheduling'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating'
    )
    args = parser.parse_args()
    
    result = create_activity_templates(dry_run=args.dry_run)
    
    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()

