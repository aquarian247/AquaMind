# Generated by Django 4.2.11 on 2025-04-30 09:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0008_create_sampling_event_sequence'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='journalentry',
            name='sampling_event_id',
        ),
    ]
