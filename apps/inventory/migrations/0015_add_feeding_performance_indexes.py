# Generated migration for growth analysis performance optimization
# Issue: Growth analysis recomputation times out after 300s per batch
# Solution: Add composite indexes for common query patterns

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0014_remove_feedstock'),
    ]

    operations = [
        # FeedingEvent: Used in _get_feed() - filter by container and feeding_date
        migrations.AddIndex(
            model_name='feedingevent',
            index=models.Index(
                fields=['container', 'feeding_date'],
                name='idx_feeding_container_date'
            ),
        ),
        # FeedingEvent: Also commonly filtered by batch
        migrations.AddIndex(
            model_name='feedingevent',
            index=models.Index(
                fields=['batch', 'feeding_date'],
                name='idx_feeding_batch_date'
            ),
        ),
    ]
















