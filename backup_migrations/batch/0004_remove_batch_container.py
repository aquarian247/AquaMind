# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0003_update_batchtransfer'),
    ]

    operations = [
        # Remove container field from Batch
        migrations.RemoveField(
            model_name='batch',
            name='container',
        ),
    ]
