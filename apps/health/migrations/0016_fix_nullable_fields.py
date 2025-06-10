# Generated manually to fix nullable field issues

from django.db import migrations, models
import django.db.models.deletion


def create_unknown_reason_and_fix_nulls(apps, schema_editor):
    """Create UNKNOWN mortality reason and fix NULL values."""
    MortalityReason = apps.get_model('health', 'MortalityReason')
    MortalityRecord = apps.get_model('health', 'MortalityRecord')
    
    # Create or get UNKNOWN reason
    unknown_reason, created = MortalityReason.objects.get_or_create(
        name='UNKNOWN',
        defaults={'description': 'Unknown or unspecified mortality reason'}
    )
    
    # Update any NULL reason fields to point to UNKNOWN
    MortalityRecord.objects.filter(reason__isnull=True).update(reason=unknown_reason)


def reverse_unknown_reason_fix(apps, schema_editor):
    """Reverse the fix by setting reason back to NULL."""
    MortalityRecord = apps.get_model('health', 'MortalityRecord')
    MortalityReason = apps.get_model('health', 'MortalityReason')
    
    try:
        unknown_reason = MortalityReason.objects.get(name='UNKNOWN')
        MortalityRecord.objects.filter(reason=unknown_reason).update(reason=None)
    except MortalityReason.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0015_healthlabsample'),
    ]

    operations = [
        # First, create UNKNOWN reason and fix NULL values
        migrations.RunPython(
            create_unknown_reason_and_fix_nulls,
            reverse_unknown_reason_fix
        ),
        
        # Then make the reason field non-nullable
        migrations.AlterField(
            model_name='mortalityrecord',
            name='reason',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mortality_records',
                to='health.mortalityreason'
            ),
        ),
        
        # Make the user field non-nullable for LiceCount
        # (This is safe since the table is empty)
        migrations.AlterField(
            model_name='licecount',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='lice_counts',
                to='auth.user',
                help_text="User who performed the count."
            ),
        ),
    ] 