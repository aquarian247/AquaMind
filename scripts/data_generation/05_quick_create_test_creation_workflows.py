#!/usr/bin/env python3
"""
Quick creation of test batch creation workflows.

Creates 5 workflows covering all statuses (DRAFT → COMPLETED) for UAT testing.
Fast execution (~30 seconds) with no broodstock dependencies.
"""
import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import transaction
from apps.batch.models import (
    Batch,
    Species,
    LifeCycleStage,
    BatchContainerAssignment,
    BatchCreationWorkflow,
    CreationAction,
)
from apps.infrastructure.models import Geography, FreshwaterStation, Container
from apps.broodstock.models import EggSupplier
from django.contrib.auth import get_user_model

User = get_user_model()


def create_test_workflows():
    """Create 5 test batch creation workflows with various statuses."""
    
    print("\n" + "="*80)
    print("Quick Create: Batch Creation Workflow Test Data")
    print("="*80 + "\n")
    
    # Get required objects
    user = User.objects.first()
    if not user:
        print("❌ Error: No users found. Run bootstrap first.")
        return
    
    geography = Geography.objects.first()
    if not geography:
        print("❌ Error: No geography found. Run bootstrap first.")
        return
    
    station = FreshwaterStation.objects.filter(geography=geography).first()
    if not station:
        print("❌ Error: No freshwater station found. Run bootstrap first.")
        return
    
    species = Species.objects.filter(name="Atlantic Salmon").first()
    if not species:
        print("❌ Error: Atlantic Salmon species not found. Run master data init first.")
        return
    
    egg_stage = LifeCycleStage.objects.filter(species=species, order=1).first()
    if not egg_stage:
        print("❌ Error: Egg/Alevin stage not found. Run master data init first.")
        return
    
    print(f"✓ Geography: {geography.name}")
    print(f"✓ Station: {station.name}")
    print(f"✓ Species: {species.name}")
    print(f"✓ Stage: {egg_stage.name}")
    print()
    
    # Create or get external supplier
    supplier, created = EggSupplier.objects.get_or_create(
        name='AquaGen Norway',
        defaults={
            'contact_details': 'Contact: eggs@aquagen.no, +47 123 45678',
            'certifications': 'ASC Certified, ISO 9001'
        }
    )
    print(f"✓ Egg Supplier: {supplier.name} {'(created)' if created else '(existing)'}")
    
    # Get containers (trays for egg/alevin)
    trays = Container.objects.filter(
        hall__freshwater_station__geography=geography,
        container_type__category='TRAY',
        active=True
    )[:15]
    
    if trays.count() < 5:
        print(f"⚠️  Warning: Only {trays.count()} trays found. Need at least 5 for realistic actions.")
        if trays.count() == 0:
            print("❌ Error: No trays found. Run bootstrap first.")
            return
    
    print(f"✓ Found {trays.count()} trays for egg deliveries\n")
    
    # Workflow scenarios
    workflows_data = [
        {
            'name': 'DRAFT Workflow',
            'status': 'DRAFT',
            'eggs': 500000,
            'actions': 0,  # No actions yet
            'executed': 0,
            'days_offset': 30,  # Future delivery
            'description': 'New workflow, no actions added yet'
        },
        {
            'name': 'PLANNED Workflow',
            'status': 'PLANNED',
            'eggs': 800000,
            'actions': 6,
            'executed': 0,  # Actions planned but not executed
            'days_offset': 15,
            'description': 'Ready for execution, 6 deliveries planned'
        },
        {
            'name': 'IN_PROGRESS Workflow',
            'status': 'IN_PROGRESS',
            'eggs': 1200000,
            'actions': 10,
            'executed': 4,  # Partial execution
            'days_offset': 7,
            'description': 'Active deliveries, 4 of 10 completed'
        },
        {
            'name': 'COMPLETED Workflow',
            'status': 'COMPLETED',
            'eggs': 600000,
            'actions': 5,
            'executed': 5,  # All executed
            'days_offset': -7,  # Started in past
            'description': 'All eggs delivered successfully'
        },
        {
            'name': 'CANCELLED Workflow',
            'status': 'CANCELLED',
            'eggs': 400000,
            'actions': 3,
            'executed': 0,  # Cancelled before execution
            'days_offset': 45,
            'description': 'Cancelled due to supplier delay'
        },
    ]
    
    print("Creating test workflows...\n")
    
    for idx, wf_data in enumerate(workflows_data, 1):
        try:
            with transaction.atomic():
                # Determine batch status
                if wf_data['status'] in ['DRAFT', 'PLANNED']:
                    batch_status = 'PLANNED'
                elif wf_data['status'] == 'CANCELLED':
                    batch_status = 'CANCELLED'
                elif wf_data['status'] == 'IN_PROGRESS':
                    batch_status = 'RECEIVING'
                else:  # COMPLETED
                    batch_status = 'ACTIVE'
                
                # Create batch
                batch = Batch.objects.create(
                    batch_number=f'TEST-CRT-2025-{idx:03d}',
                    species=species,
                    lifecycle_stage=egg_stage,
                    status=batch_status,
                    start_date=date.today() + timedelta(days=wf_data['days_offset'])
                )
                
                # Create workflow
                workflow = BatchCreationWorkflow.objects.create(
                    workflow_number=f'CRT-2025-TEST-{idx:03d}',
                    batch=batch,
                    status=wf_data['status'],
                    egg_source_type='EXTERNAL',
                    external_supplier=supplier,
                    external_supplier_batch_number=f'AQUA-{idx:03d}-2025',
                    external_cost_per_thousand=Decimal('120.00'),
                    total_eggs_planned=wf_data['eggs'],
                    planned_start_date=date.today() + timedelta(days=wf_data['days_offset']),
                    planned_completion_date=date.today() + timedelta(days=wf_data['days_offset'] + 7),
                    created_by=user,
                    notes=wf_data['description'],
                )
                
                # Add actions
                eggs_per_action = wf_data['eggs'] // max(wf_data['actions'], 1)
                
                for i in range(wf_data['actions']):
                    tray = trays[i % trays.count()]
                    delivery_day = i  # Spread over days
                    
                    # Create or get assignment
                    assignment, _ = BatchContainerAssignment.objects.get_or_create(
                        batch=batch,
                        container=tray,
                        lifecycle_stage=egg_stage,
                        defaults={
                            'population_count': 0,
                            'biomass_kg': Decimal('0.00'),
                            'assignment_date': workflow.planned_start_date,
                            'is_active': False,
                        }
                    )
                    
                    # Create action
                    action = CreationAction.objects.create(
                        workflow=workflow,
                        action_number=i + 1,
                        dest_assignment=assignment,
                        egg_count_planned=eggs_per_action,
                        expected_delivery_date=workflow.planned_start_date + timedelta(days=delivery_day),
                        status='PENDING',
                    )
                    
                    # Execute if needed
                    if i < wf_data['executed']:
                        mortality = int(eggs_per_action * 0.01)  # 1% mortality
                        action.execute(
                            mortality_on_arrival=mortality,
                            delivery_method='TRANSPORT',
                            water_temp_on_arrival=Decimal('8.5'),
                            egg_quality_score=4,
                            execution_duration_minutes=45,
                            executed_by=user,
                            notes=f'Test delivery {i+1}'
                        )
                
                # Update workflow totals
                workflow.total_actions = wf_data['actions']
                if wf_data['executed'] > 0:
                    workflow.refresh_from_db()  # Get updated counters from actions
                else:
                    workflow.save(update_fields=['total_actions'])
                
                # Handle cancellation
                if wf_data['status'] == 'CANCELLED':
                    workflow.cancellation_reason = 'Supplier delayed delivery by 3 weeks'
                    workflow.cancelled_at = timezone.now()
                    workflow.cancelled_by = user
                    workflow.save(update_fields=['cancellation_reason', 'cancelled_at', 'cancelled_by'])
                
                print(f"✅ {workflow.workflow_number} - {wf_data['name']}")
                print(f"   Batch: {batch.batch_number} (status: {batch.status})")
                print(f"   Actions: {wf_data['executed']}/{wf_data['actions']} executed")
                print(f"   Eggs: {workflow.total_eggs_received:,} / {workflow.total_eggs_planned:,}")
                print()
                
        except Exception as e:
            print(f"❌ Error creating workflow {idx}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("="*80)
    print("✅ Test Creation Workflows Generated Successfully!")
    print("="*80)
    print()
    print("Summary:")
    print(f"  - Workflows created: {BatchCreationWorkflow.objects.count()}")
    print(f"  - Actions created: {CreationAction.objects.count()}")
    print(f"  - Batches in PLANNED: {Batch.objects.filter(status='PLANNED').count()}")
    print(f"  - Batches in RECEIVING: {Batch.objects.filter(status='RECEIVING').count()}")
    print(f"  - Batches in ACTIVE: {Batch.objects.filter(status='ACTIVE').count()}")
    print(f"  - Batches in CANCELLED: {Batch.objects.filter(status='CANCELLED').count()}")
    print()
    print("Next Steps:")
    print("  1. View workflows at: http://localhost:5001/batch-creation-workflows")
    print("  2. Run batch orchestrator for infrastructure saturation (optional)")
    print("  3. Test action execution through UI")
    print()


if __name__ == '__main__':
    from django.utils import timezone
    create_test_workflows()

