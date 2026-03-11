"""Service tests for finance core."""

from io import StringIO
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.batch.models import GrowthSample
from apps.finance_core.services import (
    build_allocation_preview,
    build_movement_report,
    build_preclose_summary,
    create_allocation_preview_run,
    finalize_valuation_run,
    import_nav_costs,
    lock_period,
)
from apps.finance_core.tests.base import FinanceCoreDomainMixin

User = get_user_model()


class FinanceCoreServiceTests(FinanceCoreDomainMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="finance-service",
            email="finance-service@example.com",
            password="testpass123",
        )
        self.create_finance_core_domain(user=self.user)

    def test_import_nav_costs_replaces_period_rows(self):
        import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1000.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )
        second_batch = import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1500.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )

        self.assertEqual(second_batch.lines.count(), 1)
        self.assertEqual(second_batch.lines.first().amount, Decimal("1500.00"))
        self.assertEqual(
            sum(line.amount for line in second_batch.lines.all()),
            Decimal("1500.00"),
        )

    def test_build_allocation_preview_uses_auto_created_cost_center(self):
        import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1200.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )

        preview = build_allocation_preview(
            year=2026,
            month=3,
            operating_unit_id=self.site.site_id,
            company_id=self.company.company_id,
        )

        self.assertEqual(preview["totals"]["imported_amount"], "1200.00")
        self.assertEqual(len(preview["biology_snapshot"]), 1)
        self.assertEqual(preview["biology_snapshot"][0]["cost_center_code"], self.cost_center.code)
        self.assertEqual(preview["allocations"][0]["allocated_amount"], "1200.00")

    def test_finalize_valuation_run_builds_nav_preview(self):
        import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1200.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )

        valuation_run = finalize_valuation_run(
            budget=self.budget,
            month=3,
            operating_unit=self.site,
            user=self.user,
            mortality_adjustments={str(self.cost_center.cost_center_id): "10"},
        )

        self.assertEqual(valuation_run.status, "APPROVED")
        self.assertEqual(valuation_run.totals_snapshot["allocated_total"], "1200.00")
        self.assertEqual(len(valuation_run.nav_posting["lines"]), 2)
        self.assertEqual(valuation_run.nav_posting["psg"], "SMOLT")

    def test_lock_period_blocks_growth_sample_write(self):
        lock_period(
            company=self.company,
            operating_unit=self.site,
            year=2026,
            month=3,
            user=self.user,
            reason="Month close",
        )

        with self.assertRaises(ValidationError):
            GrowthSample.objects.create(
                assignment=self.assignment,
                sample_date=self.assignment.assignment_date.replace(month=3, day=10),
                sample_size=25,
                avg_weight_g=Decimal("110.00"),
            )

    def test_preclose_summary_tracks_readiness_and_latest_runs(self):
        import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1200.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )

        summary = build_preclose_summary(
            company_id=self.company.company_id,
            operating_unit_id=self.site.site_id,
            year=2026,
            month=3,
            budget_id=self.budget.budget_id,
        )
        self.assertTrue(summary["actions"]["can_allocate"])
        self.assertFalse(summary["actions"]["can_valuate"])
        self.assertIsNotNone(summary["latest_import"])

        preview_run = create_allocation_preview_run(
            budget=self.budget,
            month=3,
            operating_unit=self.site,
            user=self.user,
        )
        approved_run = finalize_valuation_run(
            budget=self.budget,
            month=3,
            operating_unit=self.site,
            user=self.user,
        )

        summary = build_preclose_summary(
            company_id=self.company.company_id,
            operating_unit_id=self.site.site_id,
            year=2026,
            month=3,
            budget_id=self.budget.budget_id,
        )
        self.assertEqual(summary["latest_preview_run"]["run_id"], preview_run.run_id)
        self.assertEqual(summary["latest_approved_run"]["run_id"], approved_run.run_id)
        self.assertTrue(summary["actions"]["can_lock"])

    def test_build_movement_report_can_filter_by_run(self):
        import_nav_costs(
            uploaded_file=self.make_cost_import_file(amount="1200.00"),
            year=2026,
            month=3,
            uploaded_by=self.user,
        )
        valuation_run = finalize_valuation_run(
            budget=self.budget,
            month=3,
            operating_unit=self.site,
            user=self.user,
        )

        rows = build_movement_report(run_id=valuation_run.run_id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["run_id"], valuation_run.run_id)

    def test_seed_finance_core_demo_command_is_idempotent(self):
        stdout = StringIO()
        call_command("seed_finance_core_demo", prefix="FCDEMO", stdout=stdout)
        first_output = stdout.getvalue()
        self.assertIn("Finance-core demo data seeded successfully.", first_output)

        budget_count = self.budget.__class__.objects.count()
        stdout = StringIO()
        call_command("seed_finance_core_demo", prefix="FCDEMO", stdout=stdout)

        self.assertEqual(self.budget.__class__.objects.count(), budget_count)
