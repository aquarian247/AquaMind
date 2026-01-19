from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0045_add_allow_mixed_to_transferaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaltransferaction',
            name='allow_mixed',
            field=models.BooleanField(
                default=False,
                help_text='Allow mixing with other batches if destination is occupied at execution',
            ),
        ),
    ]
