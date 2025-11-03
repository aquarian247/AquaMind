# Generated migration for Transfer Finance Integration - Phase 1

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_polymorphic_fields(apps, schema_editor):
    """
    Populate content_type and object_id from existing event FK.

    For all existing IntercompanyTransaction records:
    - Set content_type to HarvestEvent ContentType
    - Set object_id to event.id
    """
    IntercompanyTransaction = apps.get_model('finance', 'IntercompanyTransaction')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Get HarvestEvent content type
    try:
        harvest_event_ct = ContentType.objects.get(
            app_label='harvest',
            model='harvestevent'
        )
    except ContentType.DoesNotExist:
        # No content type exists yet, skip migration
        return

    # Update all existing transactions
    transactions = IntercompanyTransaction.objects.filter(
        event__isnull=False
    )

    for tx in transactions:
        tx.content_type = harvest_event_ct
        tx.object_id = tx.event_id
        tx.save(update_fields=['content_type', 'object_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('batch', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('finance', '0004_bi_delivery_views'),
    ]

    operations = [
        # ========================================================================
        # PHASE 1: Update IntercompanyPolicy
        # ========================================================================

        # Add pricing_basis field
        migrations.AddField(
            model_name='intercompanypolicy',
            name='pricing_basis',
            field=models.CharField(
                choices=[
                    ('grade', 'Product Grade (Harvest)'),
                    ('lifecycle', 'Lifecycle Stage (Transfer)')
                ],
                default='grade',
                help_text=(
                    'Whether this policy is for harvest (grade) or '
                    'transfer (lifecycle)'
                ),
                max_length=20,
            ),
        ),

        # Add lifecycle_stage FK (nullable for now)
        migrations.AddField(
            model_name='intercompanypolicy',
            name='lifecycle_stage',
            field=models.ForeignKey(
                blank=True,
                help_text='Required if pricing_basis=LIFECYCLE',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='intercompany_policies',
                to='batch.lifecyclestage',
            ),
        ),

        # Add price_per_kg for STANDARD pricing
        migrations.AddField(
            model_name='intercompanypolicy',
            name='price_per_kg',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Fixed price per kg for STANDARD method',
                max_digits=10,
                null=True,
            ),
        ),

        # Make product_grade nullable (was required before)
        migrations.AlterField(
            model_name='intercompanypolicy',
            name='product_grade',
            field=models.ForeignKey(
                blank=True,
                help_text='Required if pricing_basis=GRADE',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='intercompany_policies',
                to='harvest.productgrade',
            ),
        ),

        # Change default method to STANDARD
        migrations.AlterField(
            model_name='intercompanypolicy',
            name='method',
            field=models.CharField(
                choices=[
                    ('market', 'Market'),
                    ('cost_plus', 'Cost Plus'),
                    ('standard', 'Standard')
                ],
                default='standard',
                max_length=20,
            ),
        ),

        # Remove old unique constraint
        migrations.RemoveConstraint(
            model_name='intercompanypolicy',
            name='intercompany_policy_company_grade_uniq',
        ),

        # Add new conditional unique constraints
        migrations.AddConstraint(
            model_name='intercompanypolicy',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('pricing_basis', 'grade'),
                    ('product_grade__isnull', False)
                ),
                fields=('from_company', 'to_company', 'product_grade'),
                name='intercompany_policy_company_grade_uniq',
            ),
        ),
        migrations.AddConstraint(
            model_name='intercompanypolicy',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('pricing_basis', 'lifecycle'),
                    ('lifecycle_stage__isnull', False)
                ),
                fields=('from_company', 'to_company', 'lifecycle_stage'),
                name='intercompany_policy_company_lifecycle_uniq',
            ),
        ),

        # ========================================================================
        # PHASE 2: Update IntercompanyTransaction - Add Polymorphic Fields
        # ========================================================================

        # Add content_type FK (nullable initially)
        migrations.AddField(
            model_name='intercompanytransaction',
            name='content_type',
            field=models.ForeignKey(
                help_text=(
                    'Source model type (HarvestEvent or '
                    'BatchTransferWorkflow)'
                ),
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='contenttypes.contenttype',
            ),
        ),

        # Add object_id (nullable initially)
        migrations.AddField(
            model_name='intercompanytransaction',
            name='object_id',
            field=models.PositiveIntegerField(
                help_text='Source object ID',
                null=True,
                blank=True,
            ),
        ),

        # Make event FK nullable (for backward compatibility)
        migrations.AlterField(
            model_name='intercompanytransaction',
            name='event',
            field=models.ForeignKey(
                blank=True,
                help_text='DEPRECATED: Use polymorphic source instead',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='intercompany_transactions',
                to='harvest.harvestevent',
            ),
        ),

        # Add approval fields
        migrations.AddField(
            model_name='intercompanytransaction',
            name='approved_by',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Manager who approved this transaction '
                    '(PENDING → POSTED)'
                ),
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='approved_intercompany_transactions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='intercompanytransaction',
            name='approval_date',
            field=models.DateTimeField(
                blank=True,
                help_text='When the transaction was approved',
                null=True,
            ),
        ),

        # Update state choices (reorder: PENDING → POSTED → EXPORTED)
        migrations.AlterField(
            model_name='intercompanytransaction',
            name='state',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Approval'),
                    ('posted', 'Posted (Approved)'),
                    ('exported', 'Exported to NAV')
                ],
                default='pending',
                max_length=20,
            ),
        ),

        # ========================================================================
        # PHASE 3: Data Migration - Populate Polymorphic Fields
        # ========================================================================

        # Populate content_type and object_id from existing event FK
        migrations.RunPython(
            code=populate_polymorphic_fields,
            reverse_code=migrations.RunPython.noop,
        ),

        # ========================================================================
        # PHASE 4: Add Constraints
        # ========================================================================

        # Update old constraint to be conditional
        migrations.RemoveConstraint(
            model_name='intercompanytransaction',
            name='intercompany_transaction_event_policy_uniq',
        ),
        migrations.AddConstraint(
            model_name='intercompanytransaction',
            constraint=models.UniqueConstraint(
                condition=models.Q(('event__isnull', False)),
                fields=('event', 'policy'),
                name='intercompany_transaction_event_policy_uniq',
            ),
        ),

        # Add new polymorphic constraint
        migrations.AddConstraint(
            model_name='intercompanytransaction',
            constraint=models.UniqueConstraint(
                fields=('content_type', 'object_id', 'policy'),
                name='intercompany_transaction_source_policy_uniq',
            ),
        ),

        # Add index for polymorphic lookups
        migrations.AddIndex(
            model_name='intercompanytransaction',
            index=models.Index(
                fields=['content_type', 'object_id'],
                name='ix_interco_ct_objid',
            ),
        ),

        # ========================================================================
        # PHASE 5: Update Historical Models
        # ========================================================================

        # Add fields to historical models (auto-generated by simple-history)
        migrations.AddField(
            model_name='historicalintercompanypolicy',
            name='pricing_basis',
            field=models.CharField(
                choices=[
                    ('grade', 'Product Grade (Harvest)'),
                    ('lifecycle', 'Lifecycle Stage (Transfer)')
                ],
                default='grade',
                help_text=(
                    'Whether this policy is for harvest (grade) or '
                    'transfer (lifecycle)'
                ),
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='historicalintercompanypolicy',
            name='lifecycle_stage',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text='Required if pricing_basis=LIFECYCLE',
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='batch.lifecyclestage',
            ),
        ),
        migrations.AddField(
            model_name='historicalintercompanypolicy',
            name='price_per_kg',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Fixed price per kg for STANDARD method',
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='historicalintercompanypolicy',
            name='product_grade',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text='Required if pricing_basis=GRADE',
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='harvest.productgrade',
            ),
        ),

        migrations.AddField(
            model_name='historicalintercompanytransaction',
            name='content_type',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text=(
                    'Source model type (HarvestEvent or '
                    'BatchTransferWorkflow)'
                ),
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='contenttypes.contenttype',
            ),
        ),
        migrations.AddField(
            model_name='historicalintercompanytransaction',
            name='object_id',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Source object ID',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='historicalintercompanytransaction',
            name='approved_by',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text=(
                    'Manager who approved this transaction '
                    '(PENDING → POSTED)'
                ),
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='historicalintercompanytransaction',
            name='approval_date',
            field=models.DateTimeField(
                blank=True,
                help_text='When the transaction was approved',
                null=True,
            ),
        ),
    ]

