"""
Custom test runner for AquaMind that completely bypasses TimescaleDB operations.

This test runner is designed to support standard Django testing without 
requiring TimescaleDB functionality. TimescaleDB features will be tested manually.
"""

from django.test.runner import DiscoverRunner
from django.db import connections


class TimescaleDBTestRunner(DiscoverRunner):
    """
    Custom test runner that skips TimescaleDB setup for testing.
    
    This test runner is designed to run standard Django tests without
    relying on TimescaleDB features, which will be tested manually instead.
    """
    
    def setup_databases(self, **kwargs):
        """
        Set up the test databases while skipping TimescaleDB-specific operations.
        """
        # First, destructively drop the test database to avoid interactive prompts
        # and to ensure we start fresh without TimescaleDB setup conflicts
        for connection_name in connections:
            connection = connections[connection_name]
            try:
                test_db_name = connection.settings_dict['TEST']['NAME']
                # Only try this for PostgreSQL connections
                if connection.vendor == 'postgresql':
                    with connection.cursor() as cursor:
                        cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name};")
                    print(f"Dropped test database {test_db_name}")
            except Exception as e:
                print(f"Note: Could not drop test database {connection_name}: {e}")
                
        # Call the parent method to set up the test database
        result = super().setup_databases(**kwargs)
        
        print("TimescaleDB setup skipped for test database (will be tested manually).")
        return result
