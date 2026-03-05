"""Cleanup deprecated modal-era dynamic transport records."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.batch.models import BatchContainerAssignment, BatchTransferWorkflow, TransferAction

LEGACY_SKIP_MARKER = "[legacy_cleanup] reason=deprecated_dynamic_modal_flow"
LEGACY_ARCHIVE_MARKER = "[legacy_cleanup_archived]"
PLACEHOLDER_NOTE_TOKEN = "Dynamic transport placeholder"


class Command(BaseCommand):
    help = (
        "Cleanup stale modal-era dynamic transport records. "
        "Supports dry-run and optional hard-delete for orphan placeholders."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--workflow-id",
            default="all",
            help='Workflow ID to clean, or "all". Default: all',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report affected records without writing changes.",
        )
        parser.add_argument(
            "--apply-hard-delete",
            action="store_true",
            help="Hard-delete orphan placeholder assignments (use with care).",
        )
        parser.add_argument(
            "--stale-days",
            type=int,
            default=2,
            help="Pending action age threshold in days. Default: 2.",
        )

    def handle(self, *args, **options):
        workflow_arg = str(options["workflow_id"]).strip()
        dry_run = bool(options["dry_run"])
        hard_delete = bool(options["apply_hard_delete"])
        stale_days = int(options["stale_days"])

        workflows = BatchTransferWorkflow.objects.filter(is_dynamic_execution=True)
        if workflow_arg.lower() != "all":
            try:
                workflow_id = int(workflow_arg)
            except ValueError as exc:
                raise CommandError("--workflow-id must be an integer or 'all'.") from exc
            workflows = workflows.filter(id=workflow_id)

        if not workflows.exists():
            raise CommandError("No matching dynamic workflows found.")

        stale_cutoff = timezone.now() - timedelta(days=stale_days)
        action_candidates = (
            TransferAction.objects.select_related("workflow")
            .filter(
                workflow__in=workflows,
                status="PENDING",
                created_at__lt=stale_cutoff,
            )
            .order_by("workflow_id", "action_number")
        )

        archived_actions = 0
        skipped_actions = 0

        placeholder_candidates = (
            BatchContainerAssignment.objects.filter(
                batch__transfer_workflows__in=workflows,
                is_active=False,
                population_count=0,
                biomass_kg=0,
                notes__icontains=PLACEHOLDER_NOTE_TOKEN,
            )
            .distinct()
            .order_by("id")
        )

        placeholder_soft_archived = 0
        placeholder_deleted = 0
        placeholder_skipped = 0

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode. No data will be changed."))

        with transaction.atomic():
            for action in action_candidates:
                if LEGACY_SKIP_MARKER in (action.notes or ""):
                    skipped_actions += 1
                    continue

                if not dry_run:
                    note = (action.notes or "").strip()
                    marker = f"{LEGACY_SKIP_MARKER};at={timezone.now().isoformat()}"
                    action.status = "SKIPPED"
                    action.notes = f"{note}\n{marker}".strip()
                    action.save(update_fields=["status", "notes", "updated_at"])
                archived_actions += 1

            for assignment in placeholder_candidates:
                has_completed_link = assignment.transfer_actions_as_dest.filter(
                    status="COMPLETED"
                ).exists()
                if has_completed_link:
                    placeholder_skipped += 1
                    continue

                if hard_delete and not dry_run:
                    for linked_action in assignment.transfer_actions_as_dest.exclude(
                        status="COMPLETED"
                    ):
                        linked_action.notes = (
                            f"{(linked_action.notes or '').strip()}\n"
                            "[legacy_cleanup] detached_placeholder_assignment=true"
                        ).strip()
                        linked_action.dest_assignment = None
                        linked_action.save(
                            update_fields=["dest_assignment", "notes", "updated_at"]
                        )
                    assignment.delete()
                    placeholder_deleted += 1
                    continue

                if LEGACY_ARCHIVE_MARKER in (assignment.notes or ""):
                    placeholder_skipped += 1
                    continue

                if not dry_run:
                    assignment.notes = (
                        f"{(assignment.notes or '').strip()}\n"
                        f"{LEGACY_ARCHIVE_MARKER};at={timezone.now().isoformat()}"
                    ).strip()
                    assignment.save(update_fields=["notes", "updated_at"])
                placeholder_soft_archived += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("cleanup_dynamic_transport_legacy summary"))
        self.stdout.write(f"- Workflows scanned: {workflows.count()}")
        self.stdout.write(f"- Stale pending actions marked SKIPPED: {archived_actions}")
        self.stdout.write(f"- Stale pending actions already handled: {skipped_actions}")
        self.stdout.write(f"- Placeholder assignments soft-archived: {placeholder_soft_archived}")
        self.stdout.write(f"- Placeholder assignments hard-deleted: {placeholder_deleted}")
        self.stdout.write(f"- Placeholder assignments skipped (linked/already handled): {placeholder_skipped}")
