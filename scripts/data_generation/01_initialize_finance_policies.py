#!/usr/bin/env python3
"""
Initialize Finance Intercompany Policies

Creates intercompany policies for realistic finance flows between subsidiaries:
- Freshwater → Farming (smolt delivery at stage transition)
- Farming → Harvest (harvest events at end of life)

These policies determine pricing/markup for intercompany transactions.
Must exist before finance_project command can create IntercompanyTransaction records.

Usage:
    python scripts/data_generation/01_initialize_finance_policies.py
"""
import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from decimal import Decimal
from apps.finance.models import IntercompanyPolicy, DimCompany, DimSite
from apps.harvest.models import ProductGrade
from apps.infrastructure.models import Geography


def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def ensure_finance_dimensions():
    """
    Verify DimCompany and DimSite records exist.
    These should be created by migrations, but we check and create if needed.
    
    DimSite is required for harvest fact projection (links harvest to site).
    """
    print_section("FINANCE DIMENSION VERIFICATION")
    
    from apps.infrastructure.models import FreshwaterStation, Area
    
    geographies = Geography.objects.all()
    subsidiaries = ['FW', 'FM', 'LG']  # Freshwater, Farming, Logistics
    
    # Create DimCompany records
    print("📦 DimCompany Records:")
    for geo in geographies:
        for sub in subsidiaries:
            company, created = DimCompany.objects.get_or_create(
                geography=geo,
                subsidiary=sub,
                defaults={
                    'display_name': f"{geo.name} - {sub}",
                    'currency': 'EUR' if geo.name == 'Faroe Islands' else 'GBP',
                }
            )
            
            if created:
                print(f"  ✓ Created company: {company.display_name}")
            else:
                print(f"    Company exists: {company.display_name}")
    
    total_companies = DimCompany.objects.count()
    print(f"\n  ✅ Total companies: {total_companies} (expected: {len(geographies) * len(subsidiaries)})")
    
    # Create DimSite records for all stations and areas
    print("\n📍 DimSite Records:")
    sites_created = 0
    sites_existing = 0
    
    # Create sites for freshwater stations
    for station in FreshwaterStation.objects.all():
        company = DimCompany.objects.filter(
            geography=station.geography,
            subsidiary='FW'
        ).first()
        
        if company:
            site, created = DimSite.objects.get_or_create(
                source_model='station',
                source_pk=station.pk,
                defaults={
                    'company': company,
                    'site_name': station.name,
                }
            )
            if created:
                sites_created += 1
    
    # Create sites for sea areas
    for area in Area.objects.all():
        company = DimCompany.objects.filter(
            geography=area.geography,
            subsidiary='FM'
        ).first()
        
        if company:
            site, created = DimSite.objects.get_or_create(
                source_model='area',
                source_pk=area.pk,
                defaults={
                    'company': company,
                    'site_name': area.name,
                }
            )
            if created:
                sites_created += 1
            else:
                sites_existing += 1
    
    total_sites = DimSite.objects.count()
    print(f"  ✅ Total sites: {total_sites} (created {sites_created}, existing {sites_existing})")
    print(f"     Stations: {FreshwaterStation.objects.count()}")
    print(f"     Areas: {Area.objects.count()}")


def create_intercompany_policies():
    """
    Create intercompany policies for cross-subsidiary flows.
    
    Typical flows:
    1. Freshwater → Farming: Smolt delivery (when batch moves Post-Smolt → Adult)
    2. Farming → Logistics: Harvest delivery (when batch is harvested)
    
    Each geography operates independently (no cross-geography flows).
    """
    print_section("INTERCOMPANY POLICY CREATION")
    
    # Get all product grades (needed for harvest policies)
    grades = list(ProductGrade.objects.all())
    if not grades:
        print("⚠️  WARNING: No product grades found!")
        print("   Harvest policies will not be created.")
        print("   Run Phase 2 master data initialization first.")
    
    policies_created = 0
    policies_existing = 0
    
    # For each geography, create policies
    for geo in Geography.objects.all():
        print(f"\n--- {geo.name} ---")
        
        # Get companies for this geography
        try:
            fw_company = DimCompany.objects.get(geography=geo, subsidiary='FW')
            fm_company = DimCompany.objects.get(geography=geo, subsidiary='FM')
            lg_company = DimCompany.objects.get(geography=geo, subsidiary='LG')
        except DimCompany.DoesNotExist as e:
            print(f"  ⚠️  Missing company in {geo.name}: {e}")
            continue
        
        # Policy 1: Freshwater → Farming (Smolt delivery)
        # This is for BatchTransferWorkflow when moving Post-Smolt → Adult
        # Currently not linked to product grades (use default grade if needed)
        if grades:
            # Use first grade as default for transfer workflows
            default_grade = grades[0]
            
            policy, created = IntercompanyPolicy.objects.get_or_create(
                from_company=fw_company,
                to_company=fm_company,
                product_grade=default_grade,
                defaults={
                    'method': 'cost_plus',  # Cost plus markup method
                    'markup_percent': Decimal('15.00'),  # 15% markup for smolt delivery
                }
            )
            
            if created:
                print(f"  ✓ FW → FM (Smolt Delivery): 15% markup")
                policies_created += 1
            else:
                policies_existing += 1
        
        # Policy 2: Farming → Logistics (Harvest)
        # One policy per product grade
        for grade in grades:
            policy, created = IntercompanyPolicy.objects.get_or_create(
                from_company=fm_company,
                to_company=lg_company,
                product_grade=grade,
                defaults={
                    'method': 'cost_plus',  # Cost plus markup method
                    'markup_percent': Decimal('10.00'),  # 10% markup for harvest
                }
            )
            
            if created:
                print(f"  ✓ FM → LG ({grade.code}): 10% markup")
                policies_created += 1
            else:
                policies_existing += 1
    
    print(f"\n✅ Created {policies_created} new policies")
    print(f"   ({policies_existing} policies already existed)")


def verify_policies():
    """Verify intercompany policies are ready for use."""
    print_section("POLICY VERIFICATION")
    
    total_policies = IntercompanyPolicy.objects.count()
    
    # Group by from/to company
    by_flow = {}
    for policy in IntercompanyPolicy.objects.select_related(
        'from_company', 'to_company', 'product_grade'
    ):
        flow_key = f"{policy.from_company.subsidiary} → {policy.to_company.subsidiary}"
        if flow_key not in by_flow:
            by_flow[flow_key] = []
        by_flow[flow_key].append(policy)
    
    print(f"Total policies: {total_policies}\n")
    
    for flow, policies in sorted(by_flow.items()):
        print(f"{flow}:")
        for policy in policies[:3]:  # Show first 3
            print(f"  • {policy.product_grade.code}: {policy.markup_percent}% markup")
        if len(policies) > 3:
            print(f"  ... and {len(policies) - 3} more")
        print()
    
    # Check if we have policies for each geography
    geographies = Geography.objects.count()
    grades = ProductGrade.objects.count()
    
    # Expected: 2 geographies × (1 FW→FM + N grades for FM→LG)
    # = 2 × (1 + 5) = 12 policies (if 5 grades)
    expected_min = geographies * (1 + grades)
    
    if total_policies >= expected_min:
        print(f"✅ All expected policies exist ({total_policies} ≥ {expected_min})")
        return True
    else:
        print(f"⚠️  Missing policies ({total_policies} < {expected_min} expected)")
        print(f"   You may need to run Phase 2 master data initialization")
        return False


def main():
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Finance Intercompany Policy Initialization".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Step 1: Ensure DimCompany records exist
        ensure_finance_dimensions()
        
        # Step 2: Create intercompany policies
        create_intercompany_policies()
        
        # Step 3: Verify policies
        all_good = verify_policies()
        
        print_section("INITIALIZATION COMPLETE")
        
        if all_good:
            print("✅ Finance policies initialized successfully!")
            print("\nIntercompany transactions can now be created when:")
            print("  ✓ Batches transfer between subsidiaries (FW → FM)")
            print("  ✓ Batches are harvested (FM → LG)")
            print("\nNext steps:")
            print("  1. Generate test batches")
            print("  2. Run: python manage.py finance_project")
            print("  3. Verify IntercompanyTransaction records created")
        else:
            print("⚠️  Some policies missing - review output above")
            print("\nYou may need to:")
            print("  - Run Phase 2 master data initialization (product grades)")
            print("  - Verify DimCompany records exist for all geographies")
        
        return 0 if all_good else 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

