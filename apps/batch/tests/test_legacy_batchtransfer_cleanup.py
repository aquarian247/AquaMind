from django.db import connection
from django.test import TestCase


class LegacyBatchTransferCleanupTestCase(TestCase):
    def test_legacy_batchtransfer_tables_are_absent(self):
        table_names = set(connection.introspection.table_names())

        self.assertNotIn("batch_batchtransfer", table_names)
        self.assertNotIn("batch_historicalbatchtransfer", table_names)
