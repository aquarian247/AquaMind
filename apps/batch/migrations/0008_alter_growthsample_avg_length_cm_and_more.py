# Generated by Django 4.2.11 on 2025-04-15 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("batch", "0007_alter_growthsample_options_remove_growthsample_batch_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="growthsample",
            name="avg_length_cm",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Average length (cm) calculated from individual measurements if provided, otherwise manually entered.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="growthsample",
            name="avg_weight_g",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Average weight (g) calculated from individual measurements if provided, otherwise manually entered.",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="growthsample",
            name="condition_factor",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Average Condition Factor (K) calculated from individual measurements if provided.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="growthsample",
            name="std_deviation_length",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Standard deviation of length (cm) calculated from individual measurements if provided.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="growthsample",
            name="std_deviation_weight",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Standard deviation of weight (g) calculated from individual measurements if provided.",
                max_digits=10,
                null=True,
            ),
        ),
    ]
