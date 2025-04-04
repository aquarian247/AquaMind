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

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Set environment variable to disable TimescaleDB testing
os.environ['USE_TIMESCALEDB_TESTING'] = 'false'

# Configure Django settings
# Use the test settings file in the scripts/testing directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scripts.testing.test_settings')

import django
from django.core.management import call_command
from django.db import connection
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

def run_tests(app_name=None):
    """Run the tests."""
    print("Running tests with Django test runner...")
    
    # Use the Python executable from the virtual environment
    python_exe = sys.executable
    
    test_command = [python_exe, 'manage.py', 'test']
    if app_name:
        test_command.append(app_name)
    
    # Use the correct settings module path
    test_command.extend(['--settings=scripts.testing.test_settings', '--noinput', '--testrunner=apps.core.test_runner.TimescaleDBTestRunner'])
    
    try:
        subprocess.run(test_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == '__main__':
    # Fake the problematic TimescaleDB migrations
    fake_timescaledb_migrations()
    
    # Run the tests
    app_name = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_tests(app_name))
