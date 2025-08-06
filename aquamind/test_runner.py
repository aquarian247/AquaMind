"""
Custom Django test runner with enhanced database cleanup.

This module provides a custom test runner that extends Django's DiscoverRunner
to properly clean up database connections after parallel tests complete.
This solves the common "database is being accessed by other users" error
that occurs when Django's parallel test runner doesn't properly close
all database connections before attempting to drop the test database.
"""

import time
import logging

from django.test.runner import DiscoverRunner
from django.db import connections

logger = logging.getLogger(__name__)


class CleanupTestRunner(DiscoverRunner):
    """
    Custom test runner that ensures all database connections are properly closed.
    
    When running tests in parallel mode, Django creates multiple worker processes
    that sometimes don't properly close their database connections before the
    main process tries to drop the test database. This runner forcibly terminates
    any lingering connections before attempting to drop the database.
    """
    
    def teardown_databases(self, old_config, **kwargs):
        """
        Override teardown_databases to terminate connections before dropping databases.
        
        Args:
            old_config: The database configuration to restore after tests
            **kwargs: Additional arguments passed to the parent method
        """
        # Get the default connection
        connection = connections['default']
        
        # Get the test database name(s)
        test_databases = set()
        for alias in connections:
            test_databases.add(connections[alias].settings_dict['NAME'])
        
        # Log what we're doing
        if len(test_databases) > 1:
            logger.info(f"Terminating connections to {len(test_databases)} test databases: {', '.join(test_databases)}")
        else:
            logger.info(f"Terminating connections to test database: {next(iter(test_databases))}")
        
        # Terminate all connections to the test database(s)
        try:
            with connection.cursor() as cursor:
                for db_name in test_databases:
                    # Skip if the database name doesn't look like a test database
                    if not db_name.startswith('test_'):
                        continue
                    
                    # Terminate all connections to this test database
                    cursor.execute(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = %s AND pid <> pg_backend_pid()",
                        [db_name]
                    )
                    
                    # Log how many connections were terminated
                    results = cursor.fetchall()
                    if results:
                        terminated = sum(1 for result in results if result[0])
                        logger.info(f"Terminated {terminated} connection(s) to {db_name}")
        except Exception as e:
            # Don't fail if we can't terminate connections (database might not exist)
            logger.warning(f"Error terminating database connections: {e}")
        
        # Add a small delay to ensure connections are fully closed
        time.sleep(0.5)
        
        # Now call the parent implementation to actually drop the databases
        return super().teardown_databases(old_config, **kwargs)
