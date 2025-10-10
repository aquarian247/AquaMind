from django.db import migrations


HISTORICAL_TABLES = [
    "scenario_historicaltgcmodel",
    "scenario_historicalfcrmodel",
    "scenario_historicalmortalitymodel",
    "scenario_historicalscenario",
    "scenario_historicalscenariomodelchange",
]


class Migration(migrations.Migration):

    dependencies = [
        ("scenario", "0002_biologicalconstraints_fcrmodelstageoverride_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"DROP TABLE IF EXISTS {table};",
            reverse_sql=migrations.RunSQL.noop,
        )
        for table in HISTORICAL_TABLES
    ]
