# Generated by Django 4.2.11 on 2025-04-30 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0011_growthsample_sampling_event_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='growthsample',
            name='sampling_event_id',
        ),
        migrations.AlterField(
            model_name='growthsample',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
