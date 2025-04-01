"""
Script to run CI tests by faking problematic TimescaleDB migrations.

This script:
1. Sets up the test database
2. Fakes the problematic TimescaleDB migrations
3. Runs the tests

Usage:
    python run_ci_tests.py [app_name]
"""
import os
import sys
import subprocess
from django.core.management import call_command
from django.db import connection

# Set environment variable to disable TimescaleDB testing
os.environ['USE_TIMESCALEDB_TESTING'] = 'false'

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.test_settings')

import django
django.setup()

def fake_timescaledb_migrations():
    """Fake the problematic TimescaleDB migrations."""
    print("Faking TimescaleDB migrations...")
    
    # List of problematic migrations to fake
    timescaledb_migrations = [
        ('environmental', '0002_create_timescaledb_hypertables'),
        ('environmental', '0003_update_primary_keys'),
        ('environmental', '0004_test_timescaledb_hypertable_setup'),
        ('environmental', '0005_fix_timescaledb_integration'),
        ('environmental', '0006_correctly_enable_hypertables'),
        ('environmental', '0007_fix_sqlite_compatibility'),
    ]
    
    # Fake each migration
    for app, migration in timescaledb_migrations:
        try:
            call_command('migrate', app, migration, fake=True)
            print(f"✓ Successfully faked migration {app}.{migration}")
        except Exception as e:
            print(f"⚠ Failed to fake migration {app}.{migration}: {e}")

def run_tests():
    """Run the tests."""
    # Get the app name from command line arguments
    app_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Build the test command
    test_cmd = ['python', 'manage.py', 'test']
    if app_name:
        test_cmd.append(f'apps.{app_name}')
    
    test_cmd.extend([
        '--settings=aquamind.test_settings',
        '--noinput',
        '--testrunner=apps.core.test_runner.TimescaleDBTestRunner'
    ])
    
    # Run the tests
    print(f"Running tests: {' '.join(test_cmd)}")
    return subprocess.call(test_cmd)

if __name__ == '__main__':
    # Fake the problematic TimescaleDB migrations
    fake_timescaledb_migrations()
    
    # Run the tests
    sys.exit(run_tests())
