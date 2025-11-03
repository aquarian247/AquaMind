"""API tests for NAV export endpoints."""

from decimal import Decimal

from django.db import connection
from rest_framework import status
from unittest import skipIf

from apps.finance.models import NavExportLine
from apps.users.models import Role
from tests.api.test_finance_read_apis import FinanceAPITestDataMixin
from tests.base import BaseAPITestCase


@skipIf(connection.vendor == "sqlite", "Finance API tests require PostgreSQL features")
class FinanceNavExportPermissionTest(FinanceAPITestDataMixin, BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.export_url = self.get_api_url("finance", "nav-exports")

        # Create a user without finance permissions (OPERATOR role)
        self.non_finance_user = self._create_user(
            username='nonfinance',
            email='nonfinance@example.com',
            password='testpass123',
            role=Role.OPERATOR
        )
        # Switch to the non-finance user for permission tests
        self.client.force_authenticate(user=self.non_finance_user)

    def test_nav_export_requires_finance_role(self):
        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        response = self.client.post(self.export_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@skipIf(connection.vendor == "sqlite", "Finance API tests require PostgreSQL features")
class FinanceNavExportAPITest(FinanceAPITestDataMixin, BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user.profile.role = Role.FINANCE
        self.user.profile.save()
        self.export_url = self.get_api_url("finance", "nav-exports")

    def test_create_nav_export_batch(self):
        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        response = self.client.post(self.export_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["line_count"], 1)
        self.tx_pending.refresh_from_db()
        self.assertEqual(self.tx_pending.state, self.tx_pending.State.EXPORTED)

    def test_duplicate_request_without_force_returns_400(self):
        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        first = self.client.post(self.export_url, payload)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.export_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_force_query_reprocesses_existing_batch(self):
        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        initial = self.client.post(self.export_url, payload)
        self.assertEqual(initial.status_code, status.HTTP_201_CREATED)

        self.tx_pending.refresh_from_db()
        self.tx_pending.amount = Decimal("2500.00")
        self.tx_pending.save(update_fields=["amount"])

        response = self.client.post(f"{self.export_url}?force=true", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        batch_id = response.data["id"]
        line = NavExportLine.objects.get(batch_id=batch_id)
        self.assertEqual(line.amount, Decimal("2500.00"))

    def test_download_returns_csv_content(self):
        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        response = self.client.post(self.export_url, payload)
        batch_id = response.data["id"]

        download_url = self.get_action_url(
            "finance",
            "nav-exports",
            batch_id,
            "download",
        )
        resp = self.client.get(download_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"export_id", b"".join(resp.streaming_content))

    def test_create_without_pending_transactions_returns_400(self):
        self.tx_pending.state = self.tx_pending.State.EXPORTED
        self.tx_pending.save(update_fields=["state"])

        payload = {
            "company": self.source_company.company_id,
            "date_from": self.tx_pending.posting_date.isoformat(),
            "date_to": self.tx_pending.posting_date.isoformat(),
        }
        response = self.client.post(self.export_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
