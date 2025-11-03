# Generated manually on 2025-10-31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0024_remove_batchtransfer'),
    ]

    operations = [
        migrations.CreateModel(
            name='IndividualGrowthObservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fish_identifier', models.CharField(help_text='Identifier for the fish (e.g., sequential number).', max_length=50)),
                ('weight_g', models.DecimalField(decimal_places=2, help_text='Weight in grams.', max_digits=10)),
                ('length_cm', models.DecimalField(decimal_places=2, help_text='Length in centimeters.', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('growth_sample', models.ForeignKey(help_text='The growth sample this observation belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='individual_observations', to='batch.growthsample')),
            ],
            options={
                'verbose_name': 'Individual Growth Observation',
                'verbose_name_plural': 'Individual Growth Observations',
                'ordering': ['growth_sample', 'fish_identifier'],
                'unique_together': {('growth_sample', 'fish_identifier')},
            },
        ),
        migrations.CreateModel(
            name='HistoricalIndividualGrowthObservation',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('fish_identifier', models.CharField(help_text='Identifier for the fish (e.g., sequential number).', max_length=50)),
                ('weight_g', models.DecimalField(decimal_places=2, help_text='Weight in grams.', max_digits=10)),
                ('length_cm', models.DecimalField(decimal_places=2, help_text='Length in centimeters.', max_digits=10)),
                ('created_at', models.DateTimeField(blank=True, editable=False)),
                ('updated_at', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('growth_sample', models.ForeignKey(blank=True, db_constraint=False, help_text='The growth sample this observation belongs to.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='batch.growthsample')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical Individual Growth Observation',
                'verbose_name_plural': 'historical Individual Growth Observations',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]

