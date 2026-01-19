#!/usr/bin/env python
"""Clear migration data from the migration database while keeping schema."""

import os
import sys

import django
from django.db import connection

from scripts.migration.safety import (
    assert_default_db_is_migration_db,
    configure_migration_environment,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

configure_migration_environment()
django.setup()
assert_default_db_is_migration_db()


def clear_database():
    """Clear all migration data while keeping schema."""
    cursor = connection.cursor()

    # Tables to clear (truncate with CASCADE to satisfy dependencies)
    tables_to_clear = [
        # Most dependent first
        "batch_individualgrowthobservation",
        "batch_growthsample",
        "batch_transferaction",
        "batch_batchtransferworkflow",
        "batch_batchcontainerassignment",
        "batch_batchcomposition",
        "batch_mortalityevent",
        "batch_batch",
        "inventory_feedingevent",
        "inventory_feedcontainerstock",
        "inventory_containerfeedingsummary",
        "inventory_batchfeedingsummary",
        "inventory_feedpurchase",
        "inventory_feed",
        "health_fishparameterscore",
        "health_individualfishobservation",
        "health_healthsamplingevent",
        "health_parameterscoredefinition",
        "health_healthparameter",
        "health_mortalityrecord",
        "health_licecount",
        "health_licetype",
        "health_treatment",
        "health_healthlabsample",
        "health_vaccinationtype",
        "health_journalentry",
        "health_sampletype",
        "health_mortalityreason",
        "broodstock_batchparentage",
        "broodstock_externaleggbatch",
        "broodstock_eggproduction",
        "broodstock_breedingpair",
        "broodstock_breedingtraitpriority",
        "broodstock_breedingplan",
        "broodstock_maintenancetask",
        "broodstock_fishmovement",
        "broodstock_broodstockfish",
        "harvest_harvestwaste",
        "harvest_harvestlot",
        "harvest_harvestevent",
        "harvest_productgrade",
        "finance_navexportline",
        "finance_navexportbatch",
        "finance_intercompanytransaction",
        "finance_intercompanypolicy",
        "finance_factharvest",
        "finance_dimsite",
        "finance_dimcompany",
        "environmental_stagetransitionenvironmental",
        "environmental_photoperioddata",
        "environmental_weatherdata",
        "environmental_environmentalreading",
        "environmental_environmentalparameter",
        "scenario_fcr_model_stage_override",
        "scenario_mortality_model_stage",
        "scenario_tgc_model_stage",
        "scenario_stage_constraint",
        "scenario_biological_constraints",
        "scenario_scenarioprojection",
        "scenario_scenariomodelchange",
        "scenario_mortalitymodel",
        "scenario_fcrmodelstage",
        "scenario_fcrmodel",
        "scenario_tgcmodel",
        "scenario_temperaturereading",
        "scenario_temperatureprofile",
        "migration_support_externalidmap",
        "infrastructure_sensor",
        "infrastructure_container",
        "infrastructure_area",
        "infrastructure_hall",
        "infrastructure_freshwaterstation",
        "scenario",
        # Keep master data
        # 'batch_species',
        # 'infrastructure_*' (keep infrastructure)
        # 'auth_*' (keep users)
        # 'users_userprofile' (keep system_admin profile)
    ]

    print("Clearing database tables...")
    for table in tables_to_clear:
        try:
            cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"✓ Truncated {table}")
        except Exception as e:
            print(f"✗ Error truncating {table}: {e}")

    print("\n✅ Database cleared!")


if __name__ == "__main__":
    clear_database()
