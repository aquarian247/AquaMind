#!/usr/bin/env python
"""
Clear all test data from migration database while keeping schema
"""

import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import connection

def clear_database():
    """Clear all test data while keeping schema"""
    cursor = connection.cursor()

    # Switch to migr_dev database
    connection.settings_dict.update({
        'NAME': 'aquamind_db_migr_dev',
        'USER': 'postgres',
        'PASSWORD': 'adminpass1234',
        'HOST': 'localhost',
        'PORT': '5432'
    })

    # Tables to clear (in dependency order)
    tables_to_clear = [
        # Most dependent first
        'batch_individualgrowthobservation',
        'batch_growthsample',
        'batch_transferaction',
        'batch_batchtransferworkflow',
        'batch_batchcontainerassignment',
        'batch_batchcomposition',
        'batch_mortalityevent',
        'batch_batch',
        'inventory_feedingevent',
        'inventory_feedcontainerstock',
        'inventory_containerfeedingsummary',
        'inventory_batchfeedingsummary',
        'inventory_feedpurchase',
        'inventory_feed',
        'health_fishparameterscore',
        'health_individualfishobservation',
        'health_healthsamplingevent',
        'health_parameterscoredefinition',
        'health_healthparameter',
        'health_mortalityrecord',
        'health_licecount',
        'health_licetype',
        'health_treatment',
        'health_healthlabsample',
        'health_vaccinationtype',
        'health_journalentry',
        'health_sampletype',
        'health_mortalityreason',
        'broodstock_batchparentage',
        'broodstock_externaleggbatch',
        'broodstock_eggproduction',
        'broodstock_breedingpair',
        'broodstock_breedingtraitpriority',
        'broodstock_breedingplan',
        'broodstock_maintenancetask',
        'broodstock_fishmovement',
        'broodstock_broodstockfish',
        'harvest_harvestwaste',
        'harvest_harvestlot',
        'harvest_harvestevent',
        'harvest_productgrade',
        'finance_navexportline',
        'finance_navexportbatch',
        'finance_intercompanytransaction',
        'finance_intercompanypolicy',
        'finance_factharvest',
        'finance_dimsite',
        'finance_dimcompany',
        'environmental_stagetransitionenvironmental',
        'environmental_photoperioddata',
        'environmental_weatherdata',
        'environmental_environmentalreading',
        'environmental_environmentalparameter',
        'scenario_fcr_model_stage_override',
        'scenario_mortality_model_stage',
        'scenario_tgc_model_stage',
        'scenario_stage_constraint',
        'scenario_biological_constraints',
        'scenario_scenarioprojection',
        'scenario_scenariomodelchange',
        'scenario_mortalitymodel',
        'scenario_fcrmodelstage',
        'scenario_fcrmodel',
        'scenario_tgcmodel',
        'scenario_temperaturereading',
        'scenario_temperatureprofile',
        'scenario',
        'users_userprofile',
        # Keep master data
        # 'batch_species',
        # 'batch_lifecyclestage',
        # 'infrastructure_*' (keep infrastructure)
        # 'auth_*' (keep users)
    ]

    print("Clearing database tables...")
    for table in tables_to_clear:
        try:
            cursor.execute(f'DELETE FROM {table}')
            print(f'✓ Cleared {table}')
        except Exception as e:
            print(f'✗ Error clearing {table}: {e}')

    # Reset sequences
    print("\nResetting sequences...")
    cursor.execute("""
    SELECT 'SELECT setval(''' || quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(S.relname)) || ''', 1);'
    FROM pg_class AS S, pg_depend AS D, pg_class AS T, pg_attribute AS C, pg_tables AS PGT
    WHERE S.relkind = 'S'
        AND S.oid = D.objid
        AND D.refobjid = T.oid
        AND D.refobjsubid = C.attnum
        AND T.relname = PGT.tablename
        AND PGT.schemaname = 'public'
    ORDER BY S.relname;
    """)

    reset_commands = [row[0] for row in cursor.fetchall()]
    for cmd in reset_commands:
        try:
            cursor.execute(cmd)
            # Extract sequence name for logging
            seq_name = cmd.split("'")[1]
            print(f'✓ Reset {seq_name}')
        except Exception as e:
            print(f'✗ Error resetting sequence: {e}')

    print("\n✅ Database cleared and sequences reset!")

if __name__ == '__main__':
    clear_database()








