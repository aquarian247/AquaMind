# Generated manually 
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0001_initial'),
        ('batch', '0001_initial'),
    ]

    operations = [
        # Add batch_type to Batch model
        migrations.AddField(
            model_name='batch',
            name='batch_type',
            field=models.CharField(choices=[('STANDARD', 'Standard'), ('MIXED', 'Mixed Population')], default='STANDARD', max_length=20),
        ),
        
        # Create BatchContainerAssignment model
        migrations.CreateModel(
            name='BatchContainerAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('population_count', models.PositiveIntegerField(validators=[MinValueValidator(0)])),
                ('biomass_kg', models.DecimalField(decimal_places=2, max_digits=10)),
                ('assignment_date', models.DateField()),
                ('is_active', models.BooleanField(default=True, help_text='Whether this assignment is current/active')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='container_assignments', to='batch.batch')),
                ('container', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batch_assignments', to='infrastructure.container')),
            ],
            options={
                'ordering': ['-assignment_date'],
            },
        ),
        
        # Create constraint
        migrations.AddConstraint(
            model_name='batchcontainerassignment',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('batch', 'container'), name='unique_active_batch_container'),
        ),
        
        # Create BatchComposition model
        migrations.CreateModel(
            name='BatchComposition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentage', models.DecimalField(decimal_places=2, help_text='Percentage of this source batch in the mixed batch', max_digits=5, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ('population_count', models.PositiveIntegerField(help_text='Number of fish from this source batch in the mixed batch', validators=[MinValueValidator(0)])),
                ('biomass_kg', models.DecimalField(decimal_places=2, help_text='Biomass from this source batch in the mixed batch', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mixed_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='components', to='batch.batch')),
                ('source_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mixed_into', to='batch.batch')),
            ],
            options={
                'verbose_name_plural': 'Batch compositions',
                'ordering': ['-percentage'],
            },
        ),
    ]
