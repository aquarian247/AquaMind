#!/usr/bin/env python
"""
Clear all generated data from the database while preserving user accounts.
This script uses TRUNCATE CASCADE for fast deletion.
"""

import os
import sys
import django
from django.db import connection, transaction

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

def clear_all_data():
    """Clear all generated data while preserving user accounts."""
    
    print("=" * 70)
    print("           AQUAMIND DATA CLEARING UTILITY")
    print("=" * 70)
    print("This will clear all generated data while preserving:")
    print("  • User accounts (admin users)")
    print("  • Authentication groups and permissions")
    print("  • Django system tables")
    print("=" * 70)
    
    # Tables to truncate, organized by app
    tables_to_clear = [
        # Health app tables
        'health_treatment',
        'health_vaccinationtype',
        
        # Inventory app tables  
        'inventory_feedingevent',
        'inventory_feedpurchase',
        'inventory_feedstock',
        'inventory_feed',
        
        # Batch app tables (in dependency order)
        'batch_growthsample',
        'batch_mortalityevent',
        'batch_batchtransfer',
        'batch_batchcontainerassignment',
        'batch_batch',
        'batch_lifecyclestage',
        'batch_species',
        
        # Environmental app tables
        'environmental_environmentalreading',
        'environmental_environmentalparameter',
        
        # Infrastructure app tables (in dependency order)
        'infrastructure_sensor',
        'infrastructure_container',
        'infrastructure_hall',
        'infrastructure_freshwaterstation',
        'infrastructure_area',
        'infrastructure_geography',
        'infrastructure_containertype',
    ]
    
    # Get confirmation
    response = input("\nAre you sure you want to clear all data? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    print("\nClearing data...")
    
    with connection.cursor() as cursor:
        try:
            # Use a single transaction for speed
            with transaction.atomic():
                # Build the TRUNCATE statement
                # CASCADE will handle foreign key dependencies
                table_list = ', '.join(tables_to_clear)
                sql = f"TRUNCATE TABLE {table_list} CASCADE"
                
                print(f"Executing TRUNCATE on {len(tables_to_clear)} tables...")
                cursor.execute(sql)
                
                # Reset sequences for auto-increment fields
                for table in tables_to_clear:
                    try:
                        # Try to reset the primary key sequence
                        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)")
                    except Exception:
                        # Some tables might not have an 'id' field or sequence
                        pass
                
                print("✓ All data cleared successfully!")
                
                # Show what remains
                cursor.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM auth_user) as users,
                        (SELECT COUNT(*) FROM infrastructure_container) as containers,
                        (SELECT COUNT(*) FROM batch_batch) as batches,
                        (SELECT COUNT(*) FROM inventory_feedingevent) as feed_events
                """)
                result = cursor.fetchone()
                
                print("\n" + "=" * 70)
                print("Database Status:")
                print(f"  • User accounts preserved: {result[0]}")
                print(f"  • Containers remaining: {result[1]}")
                print(f"  • Batches remaining: {result[2]}")
                print(f"  • Feed events remaining: {result[3]}")
                print("=" * 70)
                
        except Exception as e:
            print(f"Error clearing data: {e}")
            print("\nTrying alternative method...")
            
            # Alternative: Clear tables one by one if TRUNCATE fails
            cleared = 0
            failed = []
            
            for table in reversed(tables_to_clear):  # Reverse order to handle dependencies
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    cleared += 1
                    print(f"  ✓ Cleared {table}")
                except Exception as e:
                    failed.append((table, str(e)))
                    print(f"  ✗ Failed to clear {table}: {e}")
            
            print(f"\nCleared {cleared}/{len(tables_to_clear)} tables")
            if failed:
                print("\nFailed tables:")
                for table, error in failed:
                    print(f"  - {table}: {error}")

def quick_clear():
    """Quick clear without confirmation - for use in scripts."""
    print("Quick clearing all data...")
    
    with connection.cursor() as cursor:
        tables_to_clear = [
            'health_treatment',
            'health_vaccinationtype',
            'inventory_feedingevent',
            'inventory_feedpurchase',
            'inventory_feedstock',
            'inventory_feed',
            'batch_growthsample',
            'batch_mortalityevent',
            'batch_batchtransfer',
            'batch_batchcontainerassignment',
            'batch_batch',
            'batch_lifecyclestage',
            'batch_species',
            'environmental_environmentalreading',
            'environmental_environmentalparameter',
            'infrastructure_sensor',
            'infrastructure_container',
            'infrastructure_hall',
            'infrastructure_freshwaterstation',
            'infrastructure_area',
            'infrastructure_geography',
            'infrastructure_containertype',
        ]
        
        table_list = ', '.join(tables_to_clear)
        sql = f"TRUNCATE TABLE {table_list} CASCADE"
        
        try:
            cursor.execute(sql)
            print("✓ Data cleared successfully!")
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear AquaMind database')
    parser.add_argument('--quick', action='store_true', 
                       help='Quick clear without confirmation')
    
    args = parser.parse_args()
    
    if args.quick:
        quick_clear()
    else:
        clear_all_data()
