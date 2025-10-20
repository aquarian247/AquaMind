"""
Management command to seed intercompany pricing policies for smolt transfers.

Creates lifecycle-based pricing policies for:
- Parr: €8.50/kg (Freshwater → Farming)
- Smolt: €12.50/kg (Freshwater → Farming)  
- Post-Smolt: €15.00/kg (Freshwater → Farming)

Run: python manage.py seed_smolt_policies
"""

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.batch.models import LifeCycleStage
from apps.finance.models import DimCompany, IntercompanyPolicy
from apps.infrastructure.models import Geography
from apps.users.models import Subsidiary


class Command(BaseCommand):
    help = 'Seed intercompany pricing policies for smolt/parr transfers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY RUN MODE - No changes will be saved'
            ))

        try:
            with transaction.atomic():
                created_count = self._create_policies()

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        f'\nWould create {created_count} policies '
                        '(rolling back due to --dry-run)'
                    ))
                    transaction.set_rollback(True)
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'\nSuccessfully created {created_count} '
                        'intercompany pricing policies'
                    ))

        except Exception as e:
            raise CommandError(f'Failed to seed policies: {e}')

    def _create_policies(self):
        """Create pricing policies for all geographies."""
        created_count = 0

        # Define lifecycle stage pricing
        # Note: These are PLACEHOLDER prices - adjust in admin interface
        # Prices shown in local currency equivalent
        lifecycle_pricing = {
            'Parr': {
                'DKK': Decimal('63.00'),    # ~€8.50 equivalent
                'GBP': Decimal('7.50'),     # ~€8.50 equivalent
                'NOK': Decimal('95.00'),    # ~€8.50 equivalent
                'ISK': Decimal('1200.00'),  # ~€8.50 equivalent
                'EUR': Decimal('8.50'),     # Default
            },
            'Smolt': {
                'DKK': Decimal('93.00'),    # ~€12.50 equivalent
                'GBP': Decimal('11.00'),    # ~€12.50 equivalent
                'NOK': Decimal('140.00'),   # ~€12.50 equivalent
                'ISK': Decimal('1750.00'),  # ~€12.50 equivalent
                'EUR': Decimal('12.50'),    # Default
            },
            'Post-Smolt': {
                'DKK': Decimal('112.00'),   # ~€15.00 equivalent
                'GBP': Decimal('13.00'),    # ~€15.00 equivalent
                'NOK': Decimal('168.00'),   # ~€15.00 equivalent
                'ISK': Decimal('2100.00'),  # ~€15.00 equivalent
                'EUR': Decimal('15.00'),    # Default
            },
        }

        # Get all geographies
        geographies = Geography.objects.all()

        if not geographies.exists():
            self.stdout.write(self.style.WARNING(
                'No geographies found. Run data generation first.'
            ))
            return 0

        for geography in geographies:
            self.stdout.write(
                f'\nProcessing geography: {geography.name}'
            )

            # Get or verify companies exist
            try:
                freshwater_company = DimCompany.objects.get(
                    geography=geography,
                    subsidiary=Subsidiary.FRESHWATER,
                )
                farming_company = DimCompany.objects.get(
                    geography=geography,
                    subsidiary=Subsidiary.FARMING,
                )
            except DimCompany.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  Skipping {geography.name}: Companies not found'
                ))
                continue

            # Get currency for this geography's companies
            currency = farming_company.currency or 'EUR'

            # Create policies for each lifecycle stage
            for stage_name, prices_by_currency in lifecycle_pricing.items():
                # Get price for this geography's currency
                price_per_kg = prices_by_currency.get(currency, prices_by_currency['EUR'])

                created = self._create_lifecycle_policy(
                    geography,
                    freshwater_company,
                    farming_company,
                    stage_name,
                    price_per_kg,
                    currency,
                )
                if created:
                    created_count += 1

        return created_count

    def _create_lifecycle_policy(
        self,
        geography,
        from_company,
        to_company,
        stage_name,
        price_per_kg,
        currency,
    ):
        """Create a single lifecycle-based pricing policy."""
        # Get lifecycle stage
        try:
            lifecycle_stage = LifeCycleStage.objects.get(
                stage_name=stage_name
            )
        except LifeCycleStage.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f'  Lifecycle stage "{stage_name}" not found'
            ))
            return False

        # Check if policy already exists
        existing = IntercompanyPolicy.objects.filter(
            from_company=from_company,
            to_company=to_company,
            pricing_basis=IntercompanyPolicy.PricingBasis.LIFECYCLE,
            lifecycle_stage=lifecycle_stage,
        ).first()

        if existing:
            self.stdout.write(
                f'  Policy exists: {from_company.display_name} → '
                f'{to_company.display_name} ({stage_name})'
            )
            return False

        # Create new policy
        policy = IntercompanyPolicy.objects.create(
            from_company=from_company,
            to_company=to_company,
            pricing_basis=IntercompanyPolicy.PricingBasis.LIFECYCLE,
            lifecycle_stage=lifecycle_stage,
            method=IntercompanyPolicy.Method.STANDARD,
            price_per_kg=price_per_kg,
        )

        # Currency symbols for display
        currency_symbols = {
            'EUR': '€',
            'GBP': '£',
            'DKK': 'kr',
            'NOK': 'kr',
            'ISK': 'kr',
        }
        symbol = currency_symbols.get(currency, currency)

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Created: {from_company.display_name} → '
            f'{to_company.display_name} ({stage_name}) @ '
            f'{symbol}{price_per_kg}/kg ({currency})'
        ))

        return True

