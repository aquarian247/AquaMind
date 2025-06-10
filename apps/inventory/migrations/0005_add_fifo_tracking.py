# Generated manually for FIFO tracking implementation

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_update_feedstock_timestamps'),
        ('infrastructure', '0004_container_feed_recommendations_enabled_and_more'),
    ]

    operations = [
        # Create FeedContainerStock model
        migrations.CreateModel(
            name='FeedContainerStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_kg', models.DecimalField(decimal_places=2, help_text='Remaining quantity of this feed batch in the container (kg)', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('entry_date', models.DateTimeField(help_text='Date and time when this feed batch was added to the container')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('feed_container', models.ForeignKey(help_text='Feed container where this batch is stored', on_delete=django.db.models.deletion.CASCADE, related_name='feed_batch_stocks', to='infrastructure.feedcontainer')),
                ('feed_purchase', models.ForeignKey(help_text='Original purchase batch this stock comes from', on_delete=django.db.models.deletion.PROTECT, related_name='container_stocks', to='inventory.feedpurchase')),
            ],
            options={
                'verbose_name': 'Feed Container Stock',
                'verbose_name_plural': 'Feed Container Stocks',
                'ordering': ['feed_container', 'entry_date'],
            },
        ),
        
        # Add indexes for FeedContainerStock
        migrations.AddIndex(
            model_name='feedcontainerstock',
            index=models.Index(fields=['feed_container', 'entry_date'], name='inventory_feedcontainerstock_container_entry_idx'),
        ),
        migrations.AddIndex(
            model_name='feedcontainerstock',
            index=models.Index(fields=['feed_purchase'], name='inventory_feedcontainerstock_purchase_idx'),
        ),
        
        # Add feed_cost to FeedingEvent
        migrations.AddField(
            model_name='feedingevent',
            name='feed_cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Calculated cost of feed used in this feeding event', max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))]),
        ),
        
        # Remove feed_conversion_ratio from FeedingEvent
        migrations.RemoveField(
            model_name='feedingevent',
            name='feed_conversion_ratio',
        ),
        
        # Add new fields to BatchFeedingSummary
        migrations.AddField(
            model_name='batchfeedingsummary',
            name='total_feed_consumed_kg',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total feed consumed by the batch during this period (kg)', max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))]),
        ),
        migrations.AddField(
            model_name='batchfeedingsummary',
            name='total_biomass_gain_kg',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total biomass gain during this period (kg)', max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))]),
        ),
        migrations.AddField(
            model_name='batchfeedingsummary',
            name='fcr',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Feed Conversion Ratio (total_feed_consumed_kg / total_biomass_gain_kg)', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))]),
        ),
    ] 