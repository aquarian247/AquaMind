# Generated migration for batch growth assimilation - Issue #112
# Phase 1: Add measured weight fields to TransferAction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0030_batch_creation_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferaction',
            name='measured_avg_weight_g',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Measured average weight during transfer (grams). Used as anchor for daily state calculations.",
                max_digits=10,
                null=True,
                verbose_name="Measured Average Weight (g)"
            ),
        ),
        migrations.AddField(
            model_name='transferaction',
            name='measured_std_dev_weight_g',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Standard deviation of measured weights (grams).",
                max_digits=10,
                null=True,
                verbose_name="Measured Std Dev Weight (g)"
            ),
        ),
        migrations.AddField(
            model_name='transferaction',
            name='measured_sample_size',
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Number of fish sampled for weight measurement.",
                null=True,
                verbose_name="Measured Sample Size"
            ),
        ),
        migrations.AddField(
            model_name='transferaction',
            name='measured_avg_length_cm',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Measured average length during transfer (cm).",
                max_digits=10,
                null=True,
                verbose_name="Measured Average Length (cm)"
            ),
        ),
        migrations.AddField(
            model_name='transferaction',
            name='measured_notes',
            field=models.TextField(
                blank=True,
                help_text="Notes about the weight measurements taken during transfer.",
                verbose_name="Measurement Notes"
            ),
        ),
        migrations.AddField(
            model_name='transferaction',
            name='selection_method',
            field=models.CharField(
                blank=True,
                choices=[
                    ('AVERAGE', 'Average - Representative Sample'),
                    ('LARGEST', 'Largest - Selection Bias Towards Larger Fish'),
                    ('SMALLEST', 'Smallest - Selection Bias Towards Smaller Fish'),
                ],
                default='AVERAGE',
                help_text="Method used to select fish for transfer. Affects weight calculation bias.",
                max_length=16,
                verbose_name="Selection Method"
            ),
        ),
        # Add fields to historical table as well
        migrations.AddField(
            model_name='historicaltransferaction',
            name='measured_avg_weight_g',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Measured average weight during transfer (grams). Used as anchor for daily state calculations.",
                max_digits=10,
                null=True,
                verbose_name="Measured Average Weight (g)"
            ),
        ),
        migrations.AddField(
            model_name='historicaltransferaction',
            name='measured_std_dev_weight_g',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Standard deviation of measured weights (grams).",
                max_digits=10,
                null=True,
                verbose_name="Measured Std Dev Weight (g)"
            ),
        ),
        migrations.AddField(
            model_name='historicaltransferaction',
            name='measured_sample_size',
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Number of fish sampled for weight measurement.",
                null=True,
                verbose_name="Measured Sample Size"
            ),
        ),
        migrations.AddField(
            model_name='historicaltransferaction',
            name='measured_avg_length_cm',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Measured average length during transfer (cm).",
                max_digits=10,
                null=True,
                verbose_name="Measured Average Length (cm)"
            ),
        ),
        migrations.AddField(
            model_name='historicaltransferaction',
            name='measured_notes',
            field=models.TextField(
                blank=True,
                help_text="Notes about the weight measurements taken during transfer.",
                verbose_name="Measurement Notes"
            ),
        ),
        migrations.AddField(
            model_name='historicaltransferaction',
            name='selection_method',
            field=models.CharField(
                blank=True,
                choices=[
                    ('AVERAGE', 'Average - Representative Sample'),
                    ('LARGEST', 'Largest - Selection Bias Towards Larger Fish'),
                    ('SMALLEST', 'Smallest - Selection Bias Towards Smaller Fish'),
                ],
                default='AVERAGE',
                help_text="Method used to select fish for transfer. Affects weight calculation bias.",
                max_length=16,
                verbose_name="Selection Method"
            ),
        ),
    ]

