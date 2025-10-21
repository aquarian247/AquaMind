#!/usr/bin/env python3
"""
Backfill Transfer Workflows from Existing Assignment Data

Creates COMPLETED transfer workflows for all historical stage transitions.
This avoids re-running the 5-7 hour data generation scripts.

Usage:
    python scripts/data_generation/backfill_transfer_workflows.py
    python scripts/data_generation/backfill_transfer_workflows.py --dry-run
    python scripts/data_generation/backfill_transfer_workflows.py --batch 205
"""

import os
import sys
import django
import argparse
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchTransferWorkflow,
    TransferAction,
)

User = get_user_model()


class WorkflowBackfiller:
    """Backfills transfer workflows from existing assignment data."""

    def __init__(self, dry_run=False, batch_id=None):
        self.dry_run = dry_run
        self.batch_id = batch_id
        self.stats = {
            'batches_processed': 0,
            'workflows_created': 0,
            'actions_created': 0,
            'intercompany_workflows': 0,
            'finance_transactions_created': 0,
        }
        self.user = self._get_system_user()

    def _get_system_user(self):
        """Get or create system admin user for initiated_by."""
        user, _ = User.objects.get_or_create(
            username='system_admin',
            defaults={
                'email': 'system@aquamind.com',
                'is_staff': True,
            }
        )
        return user

    def run(self):
        """Main execution method."""
        print("\n" + "=" * 80)
        print("Transfer Workflow Backfill Script")
        print("=" * 80)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No changes will be saved")
        
        print()

        # Get batches to process
        batches = self._get_batches()
        print(f"Found {batches.count()} batches to process\n")

        for batch in batches:
            self._process_batch(batch)

        # Print summary
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"Batches Processed: {self.stats['batches_processed']}")
        print(f"Workflows Created: {self.stats['workflows_created']}")
        print(f"Actions Created: {self.stats['actions_created']}")
        print(f"Intercompany Workflows: {self.stats['intercompany_workflows']}")
        print(f"Finance Transactions: {self.stats['finance_transactions_created']}")
        
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes were saved")
        else:
            print("\n✅ Backfill complete!")

    def _get_batches(self):
        """Get batches to process."""
        if self.batch_id:
            return Batch.objects.filter(id=self.batch_id)
        return Batch.objects.all().order_by('id')

    def _process_batch(self, batch):
        """Process a single batch."""
        print(f"\nProcessing Batch: {batch.batch_number} (ID: {batch.id})")

        # Find actual completed transitions
        # A transition is real when:
        # 1. Source stage has CLOSED assignments (departure_date NOT NULL)
        # 2. Dest stage assignments started on same day (assignment_date = departure_date)
        transitions = self._find_completed_transitions(batch)
        
        if not transitions:
            print(f"  ⊘ Skipped: No completed transitions")
            return

        print(f"  Found {len(transitions)} completed transition(s)")

        # Create workflow for each transition
        for transition in transitions:
            self._create_workflow_for_transition(
                batch,
                transition['source_assignments'],
                transition['dest_assignments'],
            )

        self.stats['batches_processed'] += 1

    def _find_completed_transitions(self, batch):
        """
        Find actual completed transitions by detecting closed→opened pairs.
        
        A transition is real when:
        1. Source assignments have departure_date (closed)
        2. Dest assignments start on same date (assignment_date = departure_date)
        3. Different lifecycle stages
        
        Returns:
            List of dicts with 'source_assignments' and 'dest_assignments'
        """
        # Get all assignments
        assignments = batch.batch_assignments.select_related(
            'lifecycle_stage',
            'container',
            'container__hall',
            'container__area',
        ).order_by('assignment_date', 'id')
        
        # Group by lifecycle stage AND whether they're closed
        closed_by_stage = defaultdict(list)
        opened_by_date_stage = defaultdict(list)
        
        for assignment in assignments:
            stage_id = assignment.lifecycle_stage_id
            
            # Track closed assignments
            if assignment.departure_date:
                closed_by_stage[stage_id].append(assignment)
            
            # Track when assignments opened (for matching)
            key = (assignment.assignment_date, assignment.lifecycle_stage_id)
            opened_by_date_stage[key].append(assignment)
        
        # Find transitions: closed source + opened dest on same date
        transitions = []
        
        for source_stage_id, source_assignments in closed_by_stage.items():
            # Group source assignments by departure date
            by_departure = defaultdict(list)
            for a in source_assignments:
                by_departure[a.departure_date].append(a)
            
            # For each departure date, look for assignments that opened
            for departure_date, src_group in by_departure.items():
                # Find dest assignments that opened on this date
                # (any stage different from source)
                for dest_stage_id in opened_by_date_stage.keys():
                    assignment_date, stage_id = dest_stage_id
                    
                    if assignment_date == departure_date and stage_id != source_stage_id:
                        dest_group = opened_by_date_stage[dest_stage_id]
                        
                        transitions.append({
                            'source_assignments': src_group,
                            'dest_assignments': dest_group,
                        })
        
        return transitions

    def _create_workflow_for_transition(
        self,
        batch,
        source_assignments,
        dest_assignments,
    ):
        """Create a workflow for a stage transition."""
        if not source_assignments or not dest_assignments:
            return

        # Get stage info
        source_stage = source_assignments[0].lifecycle_stage
        dest_stage = dest_assignments[0].lifecycle_stage

        # Determine transition date (when fish moved)
        transition_date = dest_assignments[0].assignment_date

        # Check if workflow already exists
        existing = BatchTransferWorkflow.objects.filter(
            batch=batch,
            source_lifecycle_stage=source_stage,
            dest_lifecycle_stage=dest_stage,
            actual_start_date=transition_date,
        ).first()

        if existing:
            print(f"  ⊘ Workflow exists: {source_stage.name} → {dest_stage.name}")
            return

        print(f"  → Creating: {source_stage.name} → {dest_stage.name} ({transition_date})")

        if self.dry_run:
            print(f"     DRY RUN: Would create workflow with {min(len(source_assignments), len(dest_assignments))} actions")
            return

        with transaction.atomic():
            # Create workflow
            workflow = self._create_workflow_record(
                batch,
                source_stage,
                dest_stage,
                transition_date,
            )

            # Create actions (pair source and dest containers)
            actions_created = self._create_actions(
                workflow,
                source_assignments,
                dest_assignments,
                transition_date,
            )

            # Update workflow totals
            workflow.recalculate_totals()
            workflow.save()

            # Detect intercompany AFTER actions are created
            workflow.detect_intercompany()
            workflow.refresh_from_db()

            # Create finance transaction if intercompany
            if workflow.is_intercompany:
                self._handle_finance_transaction(workflow)

            print(f"     ✓ Created workflow with {actions_created} actions")
            self.stats['workflows_created'] += 1
            self.stats['actions_created'] += actions_created

    def _create_workflow_record(
        self,
        batch,
        source_stage,
        dest_stage,
        transition_date,
    ):
        """Create the workflow record."""
        # Generate workflow number
        year = transition_date.year
        last_workflow = BatchTransferWorkflow.objects.filter(
            workflow_number__startswith=f'TRF-{year}-'
        ).order_by('-workflow_number').first()

        if last_workflow:
            last_num = int(last_workflow.workflow_number.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        workflow_number = f'TRF-{year}-{next_num:03d}'

        workflow = BatchTransferWorkflow.objects.create(
            workflow_number=workflow_number,
            batch=batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=source_stage,
            dest_lifecycle_stage=dest_stage,
            status='COMPLETED',
            planned_start_date=transition_date,
            planned_completion_date=transition_date,
            actual_start_date=transition_date,
            actual_completion_date=transition_date,
            initiated_by=self.user,
            completed_by=self.user,
            notes='Backfilled from historical assignment data',
        )

        # Note: detect_intercompany() called AFTER actions are created
        return workflow

    def _create_actions(
        self,
        workflow,
        source_assignments,
        dest_assignments,
        transition_date,
    ):
        """Create transfer actions by pairing containers."""
        actions_created = 0
        action_number = 1

        # Sort both lists by container name for consistent pairing
        source_sorted = sorted(source_assignments, key=lambda a: a.container.name)
        dest_sorted = sorted(dest_assignments, key=lambda a: a.container.name)

        # Pair containers (one-to-one mapping)
        pairs = list(zip(source_sorted, dest_sorted))

        for source_assignment, dest_assignment in pairs:
            # Calculate biomass transferred
            biomass = dest_assignment.biomass_kg or Decimal('0.00')

            # Estimate mortality (difference in population)
            transferred = dest_assignment.population_count
            source_pop = source_assignment.population_count
            mortality = max(0, source_pop - transferred)

            TransferAction.objects.create(
                workflow=workflow,
                action_number=action_number,
                source_assignment=source_assignment,
                dest_assignment=dest_assignment,
                source_population_before=source_pop,
                transferred_count=transferred,
                mortality_during_transfer=mortality,
                transferred_biomass_kg=biomass,
                status='COMPLETED',
                planned_date=transition_date,
                actual_execution_date=transition_date,
                executed_by=self.user,
                notes='Backfilled from historical data',
            )

            action_number += 1
            actions_created += 1

        # Update workflow action counts
        workflow.total_actions_planned = actions_created
        workflow.actions_completed = actions_created
        workflow.completion_percentage = Decimal('100.00')
        workflow.save()

        return actions_created

    def _handle_finance_transaction(self, workflow):
        """Handle finance transaction creation for intercompany workflows."""
        print(f"     💰 Intercompany detected: {workflow.source_subsidiary} → {workflow.dest_subsidiary}")

        # Check if this is Post-Smolt → Adult (the only one that creates transaction)
        is_post_smolt_to_adult = (
            workflow.source_lifecycle_stage.name == 'Post-Smolt' and
            workflow.dest_lifecycle_stage.name == 'Adult'
        )

        if is_post_smolt_to_adult:
            # Finance transaction creation will happen via the workflow's
            # _create_intercompany_transaction() method
            # We need to trigger it manually for backfilled data
            try:
                workflow._create_intercompany_transaction()
                if workflow.finance_transaction:
                    print(f"     ✓ Finance transaction created: {workflow.finance_transaction.tx_id}")
                    self.stats['finance_transactions_created'] += 1
                else:
                    print(f"     ⚠ Finance transaction not created (check pricing policy)")
            except Exception as e:
                print(f"     ⚠ Finance transaction failed: {e}")
        else:
            print(f"     ℹ Internal freshwater transfer - no finance transaction")

        self.stats['intercompany_workflows'] += 1


def main():
    parser = argparse.ArgumentParser(
        description='Backfill transfer workflows from existing assignment data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating it'
    )
    parser.add_argument(
        '--batch',
        type=int,
        help='Process only specific batch ID'
    )

    args = parser.parse_args()

    backfiller = WorkflowBackfiller(
        dry_run=args.dry_run,
        batch_id=args.batch,
    )

    try:
        backfiller.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

