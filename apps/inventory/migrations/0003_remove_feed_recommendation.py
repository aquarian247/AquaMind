from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_feedrecommendation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='feedrecommendation',
            name='batch_container_assignment',
        ),
        migrations.RemoveField(
            model_name='feedrecommendation',
            name='feed',
        ),
        migrations.DeleteModel(
            name='FeedRecommendation',
        ),
    ]
