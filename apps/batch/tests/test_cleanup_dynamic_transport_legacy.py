"""Tests for cleanup_dynamic_transport_legacy management command."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.batch.models import BatchContainerAssignment, BatchTransferWorkflow, TransferAction
from apps.batch.tests.models.test_utils import (
    create_test_batch,
    create_test_container,
    create_test_lifecycle_stage,
    create_test_species,
    create_test_user,
)
from apps.users.models import Geography as UserGeography, Role


class CleanupDynamicTransportLegacyCommandTests(TestCase):
    def setUp(self):
        self.user = create_test_user(
            geography=UserGeography.ALL,
            role=Role.ADMIN,
            username="cleanup_admin",
        )
        species = create_test_species("Cleanup Species")
        smolt = create_test_lifecycle_stage(species=species, name="Smolt", order=3)
        adult = create_test_lifecycle_stage(species=species, name="Adult", order=6)
        batch = create_test_batch(
            species=species,
            lifecycle_stage=smolt,
            batch_number="CLEAN-BATCH-001",
        )
        source_container = create_test_container(name="Cleanup-Source")
        dest_container = create_test_container(name="Cleanup-Dest")

        self.source_assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=source_container,
            lifecycle_stage=smolt,
            population_count=1000,
            avg_weight_g=Decimal("40.00"),
            assignment_date=timezone.now().date(),
            is_active=True,
            notes="source",
        )
        self.placeholder_assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=dest_container,
            lifecycle_stage=adult,
            population_count=0,
            avg_weight_g=Decimal("0.00"),
            assignment_date=timezone.now().date(),
            is_active=False,
            notes="Dynamic transport placeholder for legacy modal",
        )

        self.workflow = BatchTransferWorkflow.objects.create(
            workflow_number="TRF-CLEAN-001",
            batch=batch,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=smolt,
            dest_lifecycle_stage=adult,
            planned_start_date=timezone.now().date(),
            status="IN_PROGRESS",
            is_dynamic_execution=True,
            dynamic_route_mode="VIA_TRUCK_TO_VESSEL",
            initiated_by=self.user,
        )
        self.pending_action = TransferAction.objects.create(
            workflow=self.workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            source_population_before=1000,
            dest_assignment=self.placeholder_assignment,
            dest_container=self.placeholder_assignment.container,
            transferred_count=500,
            transferred_biomass_kg=Decimal("20.00"),
            status="PENDING",
            created_via="PLANNED",
            notes="[STATION_TO_TRUCK]",
        )
        TransferAction.objects.filter(pk=self.pending_action.pk).update(
            created_at=timezone.now() - timedelta(days=4)
        )

    def test_dry_run_is_non_destructive(self):
        output = StringIO()
        call_command(
            "cleanup_dynamic_transport_legacy",
            "--workflow-id",
            str(self.workflow.id),
            "--dry-run",
            stdout=output,
        )

        self.pending_action.refresh_from_db()
        self.assertEqual(self.pending_action.status, "PENDING")
        self.assertNotIn("[legacy_cleanup]", self.pending_action.notes)
        self.placeholder_assignment.refresh_from_db()
        self.assertNotIn("[legacy_cleanup_archived]", self.placeholder_assignment.notes)

    def test_apply_soft_cleanup_is_idempotent(self):
        call_command(
            "cleanup_dynamic_transport_legacy",
            "--workflow-id",
            str(self.workflow.id),
        )

        self.pending_action.refresh_from_db()
        self.assertEqual(self.pending_action.status, "SKIPPED")
        self.assertIn("[legacy_cleanup]", self.pending_action.notes)

        self.placeholder_assignment.refresh_from_db()
        self.assertIn("[legacy_cleanup_archived]", self.placeholder_assignment.notes)

        first_notes = self.placeholder_assignment.notes
        call_command(
            "cleanup_dynamic_transport_legacy",
            "--workflow-id",
            str(self.workflow.id),
        )
        self.placeholder_assignment.refresh_from_db()
        self.assertEqual(self.placeholder_assignment.notes, first_notes)

    def test_apply_hard_delete_removes_orphan_placeholder(self):
        call_command(
            "cleanup_dynamic_transport_legacy",
            "--workflow-id",
            str(self.workflow.id),
            "--apply-hard-delete",
        )
        self.assertFalse(
            BatchContainerAssignment.objects.filter(
                pk=self.placeholder_assignment.pk
            ).exists()
        )
