# Generated by Django 4.2.11 on 2025-04-14 14:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('health', '0003_healthparameter_remove_journalentry_health_scores_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalentry',
            name='user',
            field=models.ForeignKey(help_text='User who created the entry.', on_delete=django.db.models.deletion.PROTECT, related_name='journal_entries', to=settings.AUTH_USER_MODEL),
        ),
    ]
