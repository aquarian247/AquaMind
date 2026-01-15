from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0044_live_forward_projection'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferaction',
            name='allow_mixed',
            field=models.BooleanField(
                default=False,
                help_text='Allow mixing with other batches if destination is occupied at execution'
            ),
        ),
    ]
