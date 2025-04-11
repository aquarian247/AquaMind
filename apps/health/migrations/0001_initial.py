# Generated by Django 4.2.11 on 2025-04-11 13:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('batch', '0006_batchcontainerassignment_lifecycle_stage'),
        ('infrastructure', '0004_container_feed_recommendations_enabled_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MortalityReason',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'Mortality Reasons',
            },
        ),
        migrations.CreateModel(
            name='SampleType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'Sample Types',
            },
        ),
        migrations.CreateModel(
            name='VaccinationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('manufacturer', models.CharField(blank=True, max_length=100)),
                ('dosage', models.CharField(blank=True, max_length=50)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'Vaccination Types',
            },
        ),
        migrations.CreateModel(
            name='Treatment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('treatment_date', models.DateTimeField(auto_now_add=True)),
                ('treatment_type', models.CharField(choices=[('medication', 'Medication'), ('vaccination', 'Vaccination'), ('delicing', 'Delicing'), ('other', 'Other')], default='medication', max_length=20)),
                ('description', models.TextField()),
                ('dosage', models.CharField(blank=True, max_length=100)),
                ('duration_days', models.PositiveIntegerField(default=0)),
                ('withholding_period_days', models.PositiveIntegerField(default=0, help_text='Days before fish can be harvested after treatment.')),
                ('outcome', models.TextField(blank=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='treatments', to='batch.batch')),
                ('batch_assignment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='treatments', to='batch.batchcontainerassignment')),
                ('container', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='treatments', to='infrastructure.container')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='treatments', to=settings.AUTH_USER_MODEL)),
                ('vaccination_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='treatments', to='health.vaccinationtype')),
            ],
            options={
                'verbose_name_plural': 'Treatments',
                'ordering': ['-treatment_date'],
            },
        ),
        migrations.CreateModel(
            name='MortalityRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_date', models.DateTimeField(auto_now_add=True)),
                ('count', models.PositiveIntegerField()),
                ('notes', models.TextField(blank=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mortality_records', to='batch.batch')),
                ('container', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mortality_records', to='infrastructure.container')),
                ('reason', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mortality_records', to='health.mortalityreason')),
            ],
            options={
                'verbose_name_plural': 'Mortality Records',
                'ordering': ['-event_date'],
            },
        ),
        migrations.CreateModel(
            name='LiceCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_date', models.DateTimeField(auto_now_add=True)),
                ('adult_female_count', models.PositiveIntegerField(default=0)),
                ('adult_male_count', models.PositiveIntegerField(default=0)),
                ('juvenile_count', models.PositiveIntegerField(default=0)),
                ('fish_sampled', models.PositiveIntegerField(default=1)),
                ('notes', models.TextField(blank=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lice_counts', to='batch.batch')),
                ('container', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lice_counts', to='infrastructure.container')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lice_counts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Lice Counts',
                'ordering': ['-count_date'],
            },
        ),
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_date', models.DateTimeField(auto_now_add=True)),
                ('category', models.CharField(choices=[('observation', 'Observation'), ('issue', 'Issue'), ('action', 'Action')], default='observation', max_length=20)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low', max_length=10)),
                ('description', models.TextField()),
                ('resolution_status', models.BooleanField(default=False)),
                ('resolution_notes', models.TextField(blank=True)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='journal_entries', to='batch.batch')),
                ('container', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='journal_entries', to='infrastructure.container')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='journal_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Journal Entries',
                'ordering': ['-entry_date'],
            },
        ),
    ]
