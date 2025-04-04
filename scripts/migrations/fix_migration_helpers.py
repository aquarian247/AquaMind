#!/usr/bin/env python
"""
Script to fix the TimescaleDB migration helpers to properly respect both
TIMESCALE_ENABLED and USE_TIMESCALEDB settings.
"""
import os
import sys

# Add the project root to the Python path
sys.path.append('/workspaces/AquaMind')

def fix_migration_helpers():
    """Fix the migration helpers to check both setting names."""
    file_path = "/workspaces/AquaMind/apps/environmental/migrations_helpers.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update the check for TimescaleDB settings to include both names
    old_check = """    # Skip if explicitly disabled in settings
    if hasattr(settings, 'USE_TIMESCALEDB') and not settings.USE_TIMESCALEDB:
        return False"""
    
    new_check = """    # Skip if explicitly disabled in settings (check both setting names)
    if (hasattr(settings, 'USE_TIMESCALEDB') and not settings.USE_TIMESCALEDB) or \
       (hasattr(settings, 'TIMESCALE_ENABLED') and not settings.TIMESCALE_ENABLED):
        return False"""
    
    if old_check in content:
        updated_content = content.replace(old_check, new_check)
        
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print(f"✅ Updated {file_path} to check both 'USE_TIMESCALEDB' and 'TIMESCALE_ENABLED' settings")
        return True
    else:
        print(f"❌ Could not find the code to update in {file_path}")
        return False

if __name__ == "__main__":
    fix_migration_helpers()
