# Generated migration to remove FeedStock model and related tables
# Option A implementation: Deprecating FeedStock in favor of FIFO-only inventory via FeedContainerStock

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0013_add_history_tracking'),
    ]

    operations = [
        # Remove the feed_stock foreign key from FeedingEvent
        migrations.RemoveField(
            model_name='feedingevent',
            name='feed_stock',
        ),
        migrations.RemoveField(
            model_name='historicalfeedingevent',
            name='feed_stock',
        ),
        
        # Remove FeedStock model
        migrations.DeleteModel(
            name='FeedStock',
        ),
        
        # Remove HistoricalFeedStock model
        migrations.DeleteModel(
            name='HistoricalFeedStock',
        ),
    ]


