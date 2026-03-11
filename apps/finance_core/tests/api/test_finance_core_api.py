"""API tests for finance core endpoints."""

from rest_framework import status

from apps.users.models import Geography, Role, Subsidiary
from apps.finance_core.models import CostImportBatch
from apps.finance_core.services import finalize_valuation_run
from apps.finance_core.tests.base import FinanceCoreDomainMixin
from tests.base import BaseAPITestCase


class FinanceCoreAPITests(FinanceCoreDomainMixin, BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.create_finance_core_domain(user=self.user)

    def test_cost_import_upload_endpoint(self):
        url = self.get_api_url("finance-core", "cost-imports")
        response = self.client.post(
            url,
            {
                "year": 2026,
                "month": 3,
                "file": self.make_cost_import_file(amount="900.00"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CostImportBatch.objects.count(), 1)
        self.assertEqual(response.data["total_amount"], "900.00")

    def test_budget_allocate_endpoint_creates_preview_run(self):
        self.client.post(
            self.get_api_url("finance-core", "cost-imports"),
            {
                "year": 2026,
                "month": 3,
                "file": self.make_cost_import_file(amount="1200.00"),
            },
            format="multipart",
        )

        url = self.get_action_url("finance-core", "budgets", self.budget.budget_id, "allocate")
        response = self.client.post(
            url,
            {
                "month": 3,
                "operating_unit": self.site.site_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PREVIEW")
        self.assertEqual(response.data["operating_unit_name"], self.site.site_name)

    def test_budget_valuation_run_endpoint_creates_approved_run(self):
        self.client.post(
            self.get_api_url("finance-core", "cost-imports"),
            {
                "year": 2026,
                "month": 3,
                "file": self.make_cost_import_file(amount="1200.00"),
            },
            format="multipart",
        )

        url = self.get_action_url("finance-core", "budgets", self.budget.budget_id, "valuation-run")
        response = self.client.post(
            url,
            {
                "month": 3,
                "operating_unit": self.site.site_id,
                "mortality_adjustments": {
                    str(self.cost_center.cost_center_id): "5"
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "APPROVED")
        self.assertEqual(response.data["nav_posting"]["psg"], "SMOLT")

    def test_period_unlock_requires_admin(self):
        lock_response = self.client.post(
            self.get_api_url("finance-core", "periods/lock"),
            {
                "company": self.company.company_id,
                "operating_unit": self.site.site_id,
                "year": 2026,
                "month": 3,
                "reason": "Month close",
            },
            format="json",
        )
        self.assertEqual(lock_response.status_code, status.HTTP_200_OK)

        finance_user = self._create_user(
            username="finance-user",
            email="finance-user@example.com",
            password="testpass123",
            geography=Geography.SCOTLAND,
            role=Role.FINANCE,
            subsidiary=Subsidiary.ALL,
        )
        self.client.force_authenticate(user=finance_user)

        period_url = self.get_api_url("finance-core", "periods", detail=True, pk=lock_response.data["period_lock_id"])
        unlock_url = f"{period_url}unlock/"
        response = self.client.post(unlock_url, {"reason": "Try reopen"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_preclose_summary_endpoint(self):
        self.client.post(
            self.get_api_url("finance-core", "cost-imports"),
            {
                "year": 2026,
                "month": 3,
                "file": self.make_cost_import_file(amount="1200.00"),
            },
            format="multipart",
        )

        url = self.get_api_url(
            "finance-core",
            "reports/pre-close-summary",
            query_params={
                "company": self.company.company_id,
                "operating_unit": self.site.site_id,
                "year": 2026,
                "month": 3,
                "budget": self.budget.budget_id,
            },
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["period"], "2026-03")
        self.assertTrue(response.data["actions"]["can_allocate"])
        self.assertEqual(response.data["budget"]["budget_id"], self.budget.budget_id)

    def test_movement_report_supports_run_filter(self):
        self.client.post(
            self.get_api_url("finance-core", "cost-imports"),
            {
                "year": 2026,
                "month": 3,
                "file": self.make_cost_import_file(amount="1200.00"),
            },
            format="multipart",
        )
        valuation_run = finalize_valuation_run(
            budget=self.budget,
            month=3,
            operating_unit=self.site,
            user=self.user,
        )

        url = self.get_api_url(
            "finance-core",
            "reports/movement",
            query_params={"run_id": valuation_run.run_id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["run_id"], valuation_run.run_id)
