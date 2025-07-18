# AquaMind Project Metrics Report

**Generated:** 2025-07-18 14:22:40

## Executive Summary

### Project-Wide Metrics
- **Total Lines of Code:** 39,829
- **Total Source Lines of Code (SLOC):** 26,874
- **Total Python Files Analyzed:** 288
- **Total Functions/Methods:** 1766
- **Average Cyclomatic Complexity:** 2.36
- **Maximum Cyclomatic Complexity:** 22
- **Average Maintainability Index:** 81.19

### App Complexity Overview

| App | LOC | SLOC | Files | Avg CC | Max CC | Avg MI | Risk Level |
|-----|-----|------|-------|--------|--------|--------|------------|
| batch | 7,315 | 5,194 | 47 | 2.53 | 22 | 74.58 | 🟡 Medium |
| broodstock | 3,080 | 2,090 | 16 | 2.35 | 11 | 75.78 | 🟡 Medium |
| environmental | 4,065 | 2,919 | 29 | 2.14 | 14 | 84.09 | 🟢 Low |
| health | 5,700 | 3,742 | 42 | 2.73 | 20 | 82.53 | 🟢 Low |
| infrastructure | 4,550 | 3,164 | 49 | 1.65 | 9 | 87.32 | 🟢 Low |
| inventory | 6,730 | 4,507 | 50 | 2.30 | 17 | 79.40 | 🟡 Medium |
| operational | 7 | 5 | 9 | 1.00 | 1 | 100.00 | 🟢 Low |
| scenario | 6,668 | 4,305 | 27 | 2.76 | 17 | 73.77 | 🟡 Medium |
| users | 1,714 | 948 | 19 | 1.92 | 9 | 85.30 | 🟢 Low |

## Detailed App Analysis

### Batch App

#### Complexity Assessment
- **Overall Risk Level:** 🟡 Medium
- **Total Lines of Code:** 7,315
- **Source Lines of Code:** 5,194
- **Comment Lines:** 397
- **Blank Lines:** 1,041
- **Number of Files:** 47
- **Number of Functions/Methods:** 305

#### Cyclomatic Complexity
- **Average:** 2.53
- **Maximum:** 22
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `compare` in `viewsets.py`: CC = 22
- `BatchCompositionSerializer` in `composition.py`: CC = 21
- `validate` in `composition.py`: CC = 20
- `_process_individual_measurements` in `growth.py`: CC = 19
- `validate` in `transfer.py`: CC = 17

#### Maintainability Index
- **Average:** 74.58
- **Minimum:** 21.80
- **Interpretation:** Moderately maintainable

#### Recommendations
- Priority refactoring needed for functions with CC > 20
- Increase code documentation - current comment ratio is below 10%

### Broodstock App

#### Complexity Assessment
- **Overall Risk Level:** 🟡 Medium
- **Total Lines of Code:** 3,080
- **Source Lines of Code:** 2,090
- **Comment Lines:** 121
- **Blank Lines:** 522
- **Number of Files:** 16
- **Number of Functions/Methods:** 137

#### Cyclomatic Complexity
- **Average:** 2.35
- **Maximum:** 11
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `assign_eggs_to_batch` in `egg_management_service.py`: CC = 11

#### Maintainability Index
- **Average:** 75.78
- **Minimum:** 38.86
- **Interpretation:** Moderately maintainable

#### Recommendations
- Increase code documentation - current comment ratio is below 10%

### Environmental App

#### Complexity Assessment
- **Overall Risk Level:** 🟢 Low
- **Total Lines of Code:** 4,065
- **Source Lines of Code:** 2,919
- **Comment Lines:** 317
- **Blank Lines:** 548
- **Number of Files:** 29
- **Number of Functions/Methods:** 167

#### Cyclomatic Complexity
- **Average:** 2.14
- **Maximum:** 14
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `EnvironmentalParameterSerializer` in `serializers.py`: CC = 14
- `validate` in `serializers.py`: CC = 13
- `WeatherDataSerializer` in `serializers.py`: CC = 11
- `StageTransitionEnvironmentalSerializer` in `serializers.py`: CC = 11

#### Maintainability Index
- **Average:** 84.09
- **Minimum:** 37.58
- **Interpretation:** Moderately maintainable

#### Recommendations
- Code quality is good - maintain current standards

### Health App

#### Complexity Assessment
- **Overall Risk Level:** 🟢 Low
- **Total Lines of Code:** 5,700
- **Source Lines of Code:** 3,742
- **Comment Lines:** 427
- **Blank Lines:** 842
- **Number of Files:** 42
- **Number of Functions/Methods:** 230

#### Cyclomatic Complexity
- **Average:** 2.73
- **Maximum:** 20
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `setUp` in `test_api.py`: CC = 20
- `setUp` in `test_models.py`: CC = 16
- `calculate_aggregate_metrics` in `health_observation.py`: CC = 15
- `validate` in `lab_sample.py`: CC = 13
- `clean` in `admin.py`: CC = 12

#### Maintainability Index
- **Average:** 82.53
- **Minimum:** 40.26
- **Interpretation:** Moderately maintainable

#### Recommendations
- Code quality is good - maintain current standards

### Infrastructure App

#### Complexity Assessment
- **Overall Risk Level:** 🟢 Low
- **Total Lines of Code:** 4,550
- **Source Lines of Code:** 3,164
- **Comment Lines:** 208
- **Blank Lines:** 631
- **Number of Files:** 49
- **Number of Functions/Methods:** 249

#### Cyclomatic Complexity
- **Average:** 1.65
- **Maximum:** 9
- **Interpretation:** Simple, easy to test and maintain

#### Maintainability Index
- **Average:** 87.32
- **Minimum:** 52.12
- **Interpretation:** Highly maintainable code

#### Recommendations
- Increase code documentation - current comment ratio is below 10%

### Inventory App

#### Complexity Assessment
- **Overall Risk Level:** 🟡 Medium
- **Total Lines of Code:** 6,730
- **Source Lines of Code:** 4,507
- **Comment Lines:** 526
- **Blank Lines:** 998
- **Number of Files:** 50
- **Number of Functions/Methods:** 267

#### Cyclomatic Complexity
- **Average:** 2.30
- **Maximum:** 17
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `_setup_assignments` in `setup_feed_recommendations.py`: CC = 17
- `test_feed_viewset_filtering` in `test_backward_compatibility.py`: CC = 15
- `validate` in `feeding.py`: CC = 14
- `test_feed_viewset_searching` in `test_backward_compatibility.py`: CC = 13
- `_setup_batches` in `setup_feed_recommendations.py`: CC = 11

#### Maintainability Index
- **Average:** 79.40
- **Minimum:** 42.27
- **Interpretation:** Moderately maintainable

#### Recommendations
- Code quality is good - maintain current standards

### Operational App

#### Complexity Assessment
- **Overall Risk Level:** 🟢 Low
- **Total Lines of Code:** 7
- **Source Lines of Code:** 5
- **Comment Lines:** 0
- **Blank Lines:** 2
- **Number of Files:** 9
- **Number of Functions/Methods:** 1

#### Cyclomatic Complexity
- **Average:** 1.00
- **Maximum:** 1
- **Interpretation:** Simple, easy to test and maintain

#### Maintainability Index
- **Average:** 100.00
- **Minimum:** 100.00
- **Interpretation:** Highly maintainable code

#### Recommendations
- Increase code documentation - current comment ratio is below 10%

### Scenario App

#### Complexity Assessment
- **Overall Risk Level:** 🟡 Medium
- **Total Lines of Code:** 6,668
- **Source Lines of Code:** 4,305
- **Comment Lines:** 474
- **Blank Lines:** 1,118
- **Number of Files:** 27
- **Number of Functions/Methods:** 322

#### Cyclomatic Complexity
- **Average:** 2.76
- **Maximum:** 17
- **Interpretation:** Simple, easy to test and maintain

**Most Complex Functions:**
- `run_sensitivity_analysis` in `projection_engine.py`: CC = 17
- `run_projection` in `projection_engine.py`: CC = 15
- `import_temperature_data` in `bulk_import.py`: CC = 13
- `clean` in `models.py`: CC = 12
- `get_initial_stage` in `serializers.py`: CC = 11

#### Maintainability Index
- **Average:** 73.77
- **Minimum:** 11.92
- **Interpretation:** Moderately maintainable

#### Recommendations
- Code quality is good - maintain current standards

### Users App

#### Complexity Assessment
- **Overall Risk Level:** 🟢 Low
- **Total Lines of Code:** 1,714
- **Source Lines of Code:** 948
- **Comment Lines:** 118
- **Blank Lines:** 316
- **Number of Files:** 19
- **Number of Functions/Methods:** 88

#### Cyclomatic Complexity
- **Average:** 1.92
- **Maximum:** 9
- **Interpretation:** Simple, easy to test and maintain

#### Maintainability Index
- **Average:** 85.30
- **Minimum:** 54.51
- **Interpretation:** Highly maintainable code

#### Recommendations
- Code quality is good - maintain current standards

## Overall Recommendations

### High Priority Refactoring Targets
- All apps are within acceptable complexity thresholds.

## Methodology

### Metrics Explained

#### Cyclomatic Complexity (CC)
- **1-10:** Simple, low risk
- **11-20:** Moderate complexity, medium risk
- **21-50:** Complex, high risk
- **>50:** Very complex, untestable, very high risk

#### Maintainability Index (MI)
- **>85:** Highly maintainable
- **65-85:** Moderately maintainable
- **<65:** Difficult to maintain

#### Halstead Metrics
- **Volume:** Measures the size of the implementation
- **Difficulty:** Indicates how difficult the code is to write or understand
- **Effort:** Represents the mental effort required to develop or maintain the code