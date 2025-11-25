#!/usr/bin/env python3
"""
Initialize Health Parameters and Score Definitions

Creates comprehensive health assessment parameters based on veterinary feedback:
- 9 health parameters (gill, eye, wounds, fin, body, swimming, appetite, mucous, color)
- Score definitions (0-3 scale) for each parameter with clinical descriptions
- Supports monthly health sampling with 75 fish per sample

These parameters enable:
- Systematic health monitoring across lifecycle stages
- Early disease detection and intervention
- Regulatory compliance and welfare tracking
- Data-driven treatment decisions

Usage:
    python scripts/data_generation/01_initialize_health_parameters.py
"""
import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.health.models import HealthParameter, ParameterScoreDefinition


def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def create_health_parameters():
    """
    Create all 9 health parameters with detailed score definitions.
    Based on veterinary feedback and aquaculture best practices.
    """
    print_section("HEALTH PARAMETER CREATION")
    
    # Parameter configurations with score definitions
    parameters_config = [
        {
            'name': 'Gill Health',
            'description': 'Critical indicator of fish health, sensitive to environmental conditions, '
                          'pathogens (AGD), and water quality. Impacts oxygen uptake and welfare.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Gills are bright red, uniform, with no visible lesions or mucus'),
                (1, 'Fair', 'Moderate mucus, some pale areas, or small lesions visible'),
                (2, 'Poor', 'Significant mucus buildup, pale or darkened gills, multiple lesions'),
                (3, 'Critical', 'Severe lesions, heavy mucus, or gill necrosis; labored breathing'),
            ]
        },
        {
            'name': 'Eye Condition',
            'description': 'Visible indicator of systemic health. Eye abnormalities signal infections, '
                          'nutritional deficiencies, environmental stress, or physical damage.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Eyes are clear, bright, with no cloudiness or damage'),
                (1, 'Fair', 'Moderate cloudiness, some bulging (exophthalmia), or slight damage'),
                (2, 'Poor', 'Significant cloudiness, bulging, or unilateral damage (one eye affected)'),
                (3, 'Critical', 'Severe cloudiness, bilateral damage, or complete loss of vision (cataracts, infections)'),
            ]
        },
        {
            'name': 'Wounds and Skin Condition',
            'description': 'Reflects handling stress, overcrowding, predation, or pathogen exposure. '
                          'Wounds can lead to secondary infections and reduce market value.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Skin is smooth, scales intact, no visible wounds or lesions'),
                (1, 'Fair', 'Moderate scale loss, small open wounds, or early signs of ulceration'),
                (2, 'Poor', 'Significant wounds, multiple ulcers, or signs of infection (redness, swelling)'),
                (3, 'Critical', 'Severe wounds, large ulcers, or secondary infections (fungal growth, necrosis)'),
            ]
        },
        {
            'name': 'Fin Condition',
            'description': 'Standard welfare parameter prone to damage from environmental factors, aggression, '
                          'or disease (fin rot). Impacts swimming ability, feeding, and growth.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Fins are intact, no fraying or discoloration'),
                (1, 'Fair', 'Moderate fraying, some fin erosion, or localized discoloration'),
                (2, 'Poor', 'Significant fin erosion, missing fin sections, or signs of infection'),
                (3, 'Critical', 'Severe fin rot, extensive damage, or complete loss of fins'),
            ]
        },
        {
            'name': 'Body Condition',
            'description': 'Reflects overall health, nutrition, and growth. Integrates multiple factors '
                          '(nutrition, disease, genetics) into single metric. Used for welfare assessment.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Robust, well-proportioned body, no visible deformities'),
                (1, 'Fair', 'Moderate thinning, noticeable deformities, or reduced muscle mass'),
                (2, 'Poor', 'Significant thinning, severe deformities (scoliosis), or emaciation'),
                (3, 'Critical', 'Extreme emaciation, severe deformities, or inability to swim properly'),
            ]
        },
        {
            'name': 'Swimming Behavior',
            'description': 'Behavioral indicator affected by environmental stress, disease, or neurological issues. '
                          'Abnormal patterns signal underlying problems (hypoxia, infections, toxins).',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Normal, active swimming; appropriate response to stimuli'),
                (1, 'Fair', 'Moderate lethargy, slow response, or occasional erratic movement'),
                (2, 'Poor', 'Significant lethargy, minimal response, or frequent erratic swimming (circling)'),
                (3, 'Critical', 'Complete lethargy, inability to swim, or constant erratic behavior (flashing, spinning)'),
            ]
        },
        {
            'name': 'Appetite and Feeding Response',
            'description': 'Direct indicator of health and stress. Reduced feeding signals disease, poor water quality, '
                          'or environmental stress. Critical for growth and survival rates.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Strong feeding response; fish actively consume all feed offered'),
                (1, 'Fair', 'Moderate reduction; delayed or inconsistent feeding'),
                (2, 'Poor', 'Significant reduction; minimal feeding response, most feed uneaten'),
                (3, 'Critical', 'No feeding response; fish ignore feed entirely'),
            ]
        },
        {
            'name': 'Mucous Membrane Condition',
            'description': 'Mucous layer protects against pathogens and environmental stress. Excessive or reduced '
                          'mucus indicates stress, infections, or poor water quality.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Normal mucus layer; skin appears glossy and healthy'),
                (1, 'Fair', 'Moderate mucus buildup or slight reduction in mucus'),
                (2, 'Poor', 'Heavy mucus buildup, patchy distribution, or significant mucus loss'),
                (3, 'Critical', 'Extreme mucus buildup (slimy appearance) or complete mucus loss (dry, dull skin)'),
            ]
        },
        {
            'name': 'Color and Pigmentation',
            'description': 'Visible indicator of stress, disease, or nutritional issues. Pale coloration suggests '
                          'anemia or poor water quality; darkening indicates stress or infection.',
            'min_score': 0,
            'max_score': 3,
            'scores': [
                (0, 'Great', 'Normal, vibrant coloration typical of the species'),
                (1, 'Fair', 'Moderate paling, darkening, or uneven pigmentation'),
                (2, 'Poor', 'Significant paling (anemia), darkening, or abnormal spots (lesions)'),
                (3, 'Critical', 'Extreme discoloration, completely pale, or severe abnormal pigmentation'),
            ]
        },
    ]
    
    params_created = 0
    params_existing = 0
    scores_created = 0
    
    for config in parameters_config:
        # Create parameter
        param, created = HealthParameter.objects.get_or_create(
            name=config['name'],
            defaults={
                'description': config['description'],
                'min_score': config['min_score'],
                'max_score': config['max_score'],
                'is_active': True,
            }
        )
        
        if created:
            print(f"✓ Created parameter: {param.name}")
            params_created += 1
        else:
            print(f"  Parameter exists: {param.name}")
            params_existing += 1
        
        # Create score definitions
        for score_value, label, description in config['scores']:
            score_def, created = ParameterScoreDefinition.objects.get_or_create(
                parameter=param,
                score_value=score_value,
                defaults={
                    'label': label,
                    'description': description,
                    'display_order': score_value,
                }
            )
            
            if created:
                print(f"    {score_value} - {label}: {description[:60]}...")
                scores_created += 1
    
    print(f"\n✅ Parameters: {params_created} created, {params_existing} existing")
    print(f"✅ Score definitions: {scores_created} created")


def verify_health_parameters():
    """Verify all health parameters are properly configured."""
    print_section("HEALTH PARAMETER VERIFICATION")
    
    # Check all parameters have score definitions
    params = HealthParameter.objects.filter(is_active=True)
    
    print(f"Total active parameters: {params.count()}\n")
    
    all_complete = True
    for param in params:
        score_defs = ParameterScoreDefinition.objects.filter(parameter=param).count()
        expected_scores = param.max_score - param.min_score + 1
        
        if score_defs == expected_scores:
            print(f"✓ {param.name:30s}: {score_defs}/{expected_scores} scores")
        else:
            print(f"⚠ {param.name:30s}: {score_defs}/{expected_scores} scores (incomplete!)")
            all_complete = False
    
    print()
    
    # Summary
    if params.count() == 9 and all_complete:
        print("✅ All 9 health parameters fully configured!")
        return True
    else:
        print(f"⚠️  Expected 9 parameters, found {params.count()}")
        return False


def print_usage_examples():
    """Print examples of how these parameters will be used."""
    print_section("USAGE IN TEST DATA GENERATION")
    
    print("""
Health Sampling Configuration:
─────────────────────────────
Frequency:        Monthly (every 30 days)
Sample Size:      75 fish per event
Parameters:       All 9 parameters scored per fish
Total Scores:     75 fish × 9 parameters = 675 scores per event

Lifecycle Stage Coverage:
─────────────────────────
✓ Post-Smolt:    Monthly sampling (high growth phase)
✓ Adult:         Monthly sampling (market preparation)

Example Scoring Distribution:
─────────────────────────────
For healthy batch (typical):
  Score 0 (Great):     60% of observations
  Score 1 (Fair):      30% of observations
  Score 2 (Poor):       8% of observations
  Score 3 (Critical):   2% of observations

For stressed batch (warning signs):
  Score 0 (Great):     20% of observations
  Score 1 (Fair):      40% of observations
  Score 2 (Poor):      30% of observations
  Score 3 (Critical):  10% of observations

Integration with AquaMind:
─────────────────────────────
✓ Environmental data:  Correlate health scores with water quality
✓ Feeding data:        Correlate appetite scores with feeding events
✓ Treatment data:      Track health improvements post-treatment
✓ Photo uploads:       Document eye condition, wounds, coloration
✓ Video uploads:       Document swimming behavior over time

Regulatory Compliance:
─────────────────────────────
✓ Faroese regulations:  Welfare monitoring and disease reporting
✓ Scottish regulations: Health assessment and audit trails
✓ ASC Certification:    Comprehensive welfare documentation
""")


def main():
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Health Parameter and Score Definition Initialization".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Step 1: Create health parameters and score definitions
        create_health_parameters()
        
        # Step 2: Verify everything is configured
        all_good = verify_health_parameters()
        
        # Step 3: Show usage examples
        print_usage_examples()
        
        print_section("INITIALIZATION COMPLETE")
        
        if all_good:
            print("✅ All health parameters initialized successfully!")
            print("\nHealth monitoring system ready for:")
            print("  ✓ Monthly health sampling events (75 fish/sample)")
            print("  ✓ Individual fish observations with all 9 parameters")
            print("  ✓ Systematic health scoring (0-3 scale)")
            print("  ✓ Early disease detection and intervention")
            print("  ✓ Regulatory compliance and welfare tracking")
            print("\nNext steps:")
            print("  1. Generate test batches with health sampling")
            print("  2. View health sampling events in GUI")
            print("  3. Analyze health trends correlated with environment/feed")
        else:
            print("⚠️  Some parameters incomplete - review output above")
        
        return 0 if all_good else 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())



