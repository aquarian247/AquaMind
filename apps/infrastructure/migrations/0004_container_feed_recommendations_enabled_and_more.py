# Generated by Django 4.2.11 on 2025-04-08 08:52

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0003_alter_area_max_biomass'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='feed_recommendations_enabled',
            field=models.BooleanField(default=False, help_text='Whether feed recommendations should be generated for this container'),
        ),
        migrations.AlterField(
            model_name='container',
            name='container_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='containers', to='infrastructure.containertype'),
        ),
        migrations.AlterField(
            model_name='container',
            name='volume_m3',
            field=models.DecimalField(decimal_places=2, help_text='Container volume in cubic meters', max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)]),
        ),
    ]
