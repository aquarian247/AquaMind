#!/usr/bin/env python3
"""
Validate Test Data Generation Enhancements

Checks that finance facts and scenarios are being generated correctly.
Run after executing 03_event_engine_core.py to validate enhancements.

Usage:
    python scripts/data_generation/validate_enhancements.py
"""

import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.finance.models import FactHarvest, DimCompany, DimSite
from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, MortalityModel,
    TemperatureProfile, TemperatureReading, FCRModelStage
)
from apps.batch.models import Batch
from apps.harvest.models import HarvestEvent, HarvestLot


def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def validate_finance_facts():
    """Validate finance harvest fact generation."""
    print_section("Finance Harvest Facts Validation")
    
    # Count records
    facts = FactHarvest.objects.count()
    companies = DimCompany.objects.count()
    sites = DimSite.objects.count()
    harvest_events = HarvestEvent.objects.count()
    harvest_lots = HarvestLot.objects.count()
    
    print(f"Finance Facts:    {facts}")
    print(f"Companies:        {companies}")
    print(f"Sites:            {sites}")
    print(f"Harvest Events:   {harvest_events}")
    print(f"Harvest Lots:     {harvest_lots}")
    print()
    
    # Validation
    if facts == 0 and harvest_lots > 0:
        print("❌ FAIL: Harvest lots exist but no finance facts generated")
        print("   Check: Finance dimension initialization")
        return False
    elif facts > 0:
        print(f"✅ PASS: Finance facts generated")
        
        # Check ratio (should be 1:1 with lots)
        if facts == harvest_lots:
            print(f"✅ PASS: Facts match lots (1:1 ratio)")
        else:
            print(f"⚠️  WARNING: Facts ({facts}) != Lots ({harvest_lots})")
        
        # Sample fact
        sample = FactHarvest.objects.select_related(
            'dim_company', 'dim_site', 'product_grade'
        ).first()
        if sample:
            print(f"\nSample Fact:")
            print(f"  Company: {sample.dim_company.display_name}")
            print(f"  Site: {sample.dim_site.site_name}")
            print(f"  Grade: {sample.product_grade.code}")
            print(f"  Quantity: {sample.quantity_kg}kg")
            print(f"  Units: {sample.unit_count}")
        
        return True
    else:
        print("ℹ️  INFO: No harvest events yet (batches still growing)")
        return True


def validate_scenarios():
    """Validate scenario generation at sea transitions."""
    print_section("Scenario Generation Validation")
    
    # Count records
    scenarios = Scenario.objects.count()
    tgc_models = TGCModel.objects.count()
    fcr_models = FCRModel.objects.count()
    mortality_models = MortalityModel.objects.count()
    temp_profiles = TemperatureProfile.objects.count()
    temp_readings = TemperatureReading.objects.count()
    fcr_stages = FCRModelStage.objects.count()
    
    print(f"Scenarios:           {scenarios}")
    print(f"TGC Models:          {tgc_models}")
    print(f"FCR Models:          {fcr_models}")
    print(f"FCR Model Stages:    {fcr_stages}")
    print(f"Mortality Models:    {mortality_models}")
    print(f"Temperature Profiles: {temp_profiles}")
    print(f"Temperature Readings: {temp_readings}")
    print()
    
    # Validation
    if scenarios == 0:
        adult_batches = Batch.objects.filter(lifecycle_stage__name='Adult').count()
        if adult_batches > 0:
            print(f"❌ FAIL: {adult_batches} Adult batches exist but no scenarios created")
            print("   Check: _create_sea_transition_scenario() method")
            return False
        else:
            print("ℹ️  INFO: No Adult batches yet (too early in lifecycle)")
            return True
    
    # Validate model counts
    issues = []
    
    if tgc_models == 0:
        issues.append("No TGC models created")
    elif tgc_models > 2:
        print(f"⚠️  WARNING: {tgc_models} TGC models (expected 2: Faroe + Scotland)")
        print("   Models should be reused, not created per batch")
    else:
        print(f"✅ PASS: TGC model count correct ({tgc_models})")
    
    if fcr_models == 0:
        issues.append("No FCR models created")
    elif fcr_models > 1:
        print(f"⚠️  WARNING: {fcr_models} FCR models (expected 1 shared)")
    else:
        print(f"✅ PASS: FCR model is shared (1 model)")
    
    if fcr_stages < 6:
        issues.append(f"FCR stage values incomplete ({fcr_stages}/6)")
    else:
        print(f"✅ PASS: FCR stage values complete ({fcr_stages} stages)")
    
    if mortality_models == 0:
        issues.append("No Mortality models created")
    elif mortality_models > 1:
        print(f"⚠️  WARNING: {mortality_models} Mortality models (expected 1 shared)")
    else:
        print(f"✅ PASS: Mortality model is shared (1 model)")
    
    if temp_profiles == 0:
        issues.append("No Temperature profiles created")
    elif temp_profiles > 2:
        print(f"⚠️  WARNING: {temp_profiles} Temperature profiles (expected 2)")
    else:
        print(f"✅ PASS: Temperature profile count correct ({temp_profiles})")
    
    # Check temperature readings per profile
    if temp_profiles > 0:
        for profile in TemperatureProfile.objects.all():
            reading_count = profile.readings.count()
            avg_temp = profile.readings.aggregate(
                avg=django.db.models.Avg('temperature')
            )['avg']
            
            print(f"\nTemperature Profile: {profile.name}")
            print(f"  Readings: {reading_count}")
            if avg_temp:
                print(f"  Avg Temp: {avg_temp:.1f}°C")
                
                # Validate temperature ranges
                if 'Faroe' in profile.name:
                    if 8.0 <= avg_temp <= 11.0:
                        print(f"  ✅ PASS: Faroe temp in expected range (8-11°C)")
                    else:
                        print(f"  ⚠️  WARNING: Faroe temp outside expected range")
                elif 'Scotland' in profile.name:
                    if 7.0 <= avg_temp <= 13.0:
                        print(f"  ✅ PASS: Scotland temp in expected range (6-14°C)")
                    else:
                        print(f"  ⚠️  WARNING: Scotland temp outside expected range")
    
    # Sample scenario
    if scenarios > 0:
        print(f"\n✅ PASS: {scenarios} scenarios created")
        
        sample = Scenario.objects.select_related(
            'batch', 'tgc_model', 'fcr_model', 'mortality_model'
        ).first()
        if sample:
            print(f"\nSample Scenario:")
            print(f"  Name: {sample.name}")
            print(f"  Batch: {sample.batch.batch_number}")
            print(f"  Duration: {sample.duration_days} days")
            print(f"  Initial: {sample.initial_count:,} fish @ {sample.initial_weight}g")
            print(f"  TGC Model: {sample.tgc_model.name}")
            print(f"  FCR Model: {sample.fcr_model.name}")
            print(f"  Mortality Model: {sample.mortality_model.name}")
    
    if issues:
        print(f"\n❌ FAIL: {len(issues)} issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    return True


def validate_model_reuse():
    """Validate that models are reused across batches, not duplicated."""
    print_section("Model Reuse Validation")
    
    batches = Batch.objects.count()
    scenarios = Scenario.objects.count()
    
    if scenarios == 0:
        print("ℹ️  INFO: No scenarios yet")
        return True
    
    # Check model reuse
    tgc_per_scenario = Scenario.objects.values('tgc_model').distinct().count()
    fcr_per_scenario = Scenario.objects.values('fcr_model').distinct().count()
    mort_per_scenario = Scenario.objects.values('mortality_model').distinct().count()
    
    print(f"Total Scenarios: {scenarios}")
    print(f"Unique TGC Models: {tgc_per_scenario} (expected: 2)")
    print(f"Unique FCR Models: {fcr_per_scenario} (expected: 1)")
    print(f"Unique Mortality Models: {mort_per_scenario} (expected: 1)")
    print()
    
    if tgc_per_scenario <= 2:
        print("✅ PASS: TGC models reused (not duplicated)")
    else:
        print(f"❌ FAIL: Too many TGC models ({tgc_per_scenario})")
        return False
    
    if fcr_per_scenario == 1:
        print("✅ PASS: FCR model shared across all scenarios")
    else:
        print(f"❌ FAIL: FCR models not shared ({fcr_per_scenario})")
        return False
    
    if mort_per_scenario == 1:
        print("✅ PASS: Mortality model shared across all scenarios")
    else:
        print(f"❌ FAIL: Mortality models not shared ({mort_per_scenario})")
        return False
    
    return True


def main():
    """Run all validations."""
    print(f"\n{'='*80}")
    print("TEST DATA GENERATION ENHANCEMENTS - VALIDATION")
    print(f"{'='*80}")
    
    results = {
        'finance_facts': validate_finance_facts(),
        'scenarios': validate_scenarios(),
        'model_reuse': validate_model_reuse(),
    }
    
    print_section("Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test}")
    
    print()
    print(f"Overall: {passed}/{total} validations passed")
    
    if passed == total:
        print("\n🎉 All enhancements working correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation(s) failed")
        return 1


if __name__ == '__main__':
    import django.db.models
    sys.exit(main())








