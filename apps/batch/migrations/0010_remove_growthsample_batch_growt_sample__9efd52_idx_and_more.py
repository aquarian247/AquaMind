# Generated by Django 4.2.11 on 2025-04-30 09:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0009_growthsample_sampling_event_id_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='growthsample',
            name='batch_growt_sample__9efd52_idx',
        ),
        migrations.RemoveField(
            model_name='growthsample',
            name='sampling_event_id',
        ),
    ]
