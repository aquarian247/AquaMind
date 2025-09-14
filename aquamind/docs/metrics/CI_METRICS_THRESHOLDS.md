# AquaMind Backend CI Metrics Thresholds

**Last Updated:** 2025-09-14
**Purpose:** Define quality gates and thresholds for continuous monitoring of code maintainability

## Overview

This document defines the thresholds and quality gates used by the CI pipeline to monitor code quality metrics. All thresholds are currently **warn-only** to allow for gradual improvement while maintaining continuous visibility.

## Metrics Monitored

### 1. Cyclomatic Complexity (CC)
- **Tool:** Radon
- **Source:** `scripts/run_radon_metrics.py`
- **Artifact:** `backend_radon_cc_YYYY-MM-DD.json`

#### Thresholds
| Complexity Range | Rating | Action |
|------------------|--------|--------|
| 1-5 | A (Low) | ✅ Acceptable |
| 6-10 | B (Medium) | ✅ Acceptable |
| 11-20 | C (High) | ⚠️ Warning - Consider refactoring |
| 21-50 | D (Very High) | 🚨 Critical - Requires refactoring |
| >50 | F (Unmaintainable) | 🚨 Critical - Immediate refactoring required |

#### Per-App Thresholds (Warn-Only)
- **Warning:** CC average > 15 per app
- **Critical:** CC average > 25 per app
- **Max CC per function:** 30 (absolute limit to investigate)

### 2. Maintainability Index (MI)
- **Tool:** Radon
- **Source:** `scripts/run_radon_metrics.py`
- **Artifact:** `backend_radon_mi_YYYY-MM-DD.json`

#### Thresholds
| MI Range | Rating | Interpretation | Action |
|----------|--------|----------------|--------|
| >85 | A (Highly Maintainable) | Code is easy to maintain | ✅ Acceptable |
| 65-85 | B (Moderately Maintainable) | Code is reasonably maintainable | ✅ Acceptable |
| 50-65 | C (Difficult to Maintain) | Code requires attention | ⚠️ Warning - Review |
| <50 | D (Very Difficult to Maintain) | Code is hard to maintain | 🚨 Critical - Refactor |

#### Per-App Thresholds (Warn-Only)
- **Warning:** MI average < 60 per app
- **Critical:** MI average < 45 per app
- **Minimum MI per file:** 30 (absolute limit to investigate)

### 3. Cognitive Complexity
- **Tool:** flake8-cognitive-complexity (C90)
- **Source:** `scripts/run_cognitive_metrics.py`
- **Artifact:** `backend_cognitive_YYYY-MM-DD.txt`

#### Thresholds
| Complexity | Action |
|------------|--------|
| ≤ 15 | ✅ Acceptable |
| 16-25 | ⚠️ Warning - Consider simplifying |
| > 25 | 🚨 Critical - Requires refactoring |

#### Per-App Thresholds (Warn-Only)
- **Warning:** > 5 cognitive complexity violations per app
- **Critical:** > 15 cognitive complexity violations per app

### 4. Halstead Metrics
- **Tool:** Radon
- **Source:** `scripts/run_radon_metrics.py`
- **Artifact:** `backend_radon_hal_YYYY-MM-DD.json`

#### Key Metrics Monitored
- **Volume:** Program size (lines of code equivalent)
- **Difficulty:** How difficult the code is to understand
- **Effort:** Mental effort required to develop/maintain

#### Thresholds (Reference Only - No CI Blocking)
- **Volume:** Monitor trends, no absolute thresholds
- **Difficulty:** Monitor trends, no absolute thresholds
- **Effort:** Monitor trends, no absolute thresholds

### 5. Raw Metrics
- **Tool:** Radon
- **Source:** `scripts/run_radon_metrics.py`
- **Artifact:** `backend_radon_raw_YYYY-MM-DD.json`

#### Key Metrics Monitored
- **LOC (Lines of Code):** Total lines
- **SLOC (Source Lines of Code):** Non-comment, non-blank lines
- **Comments:** Documentation lines
- **Comment Ratio:** Comments / SLOC

#### Thresholds (Reference Only - No CI Blocking)
- **Comment Ratio Target:** > 10%
- **Large File Warning:** > 500 SLOC per file
- **Very Large File Critical:** > 1000 SLOC per file

## CI Pipeline Integration

### Workflow Steps
1. **Run Radon Metrics** - Collects CC, MI, Halstead, Raw metrics
2. **Run Cognitive Complexity** - Analyzes cognitive complexity violations
3. **Upload Artifacts** - Saves JSON/text files for trend analysis
4. **Generate Reports** - Creates summary reports for developers

### Artifact Structure
```
aquamind/docs/metrics/
├── backend_radon_cc_YYYY-MM-DD.json     # Cyclomatic complexity
├── backend_radon_mi_YYYY-MM-DD.json     # Maintainability index
├── backend_radon_hal_YYYY-MM-DD.json    # Halstead metrics
├── backend_radon_raw_YYYY-MM-DD.json    # Raw metrics
├── backend_cognitive_YYYY-MM-DD.txt     # Cognitive complexity report
└── CI_METRICS_THRESHOLDS.md            # This thresholds document
```

### Failure Behavior
- **Current:** All thresholds are warn-only
- **Future:** May introduce blocking thresholds based on:
  - Trend analysis over time
  - Critical complexity hotspots
  - UAT readiness requirements

## Remediation Guidelines

### When Thresholds Are Exceeded

#### Cyclomatic Complexity Issues
1. **Extract Methods:** Break large functions into smaller, focused methods
2. **Replace Conditionals:** Use polymorphism or strategy patterns
3. **Early Returns:** Use guard clauses to reduce nesting
4. **Table-Driven Methods:** Replace complex conditionals with lookup tables

#### Maintainability Index Issues
1. **Add Documentation:** Improve docstrings and comments
2. **Reduce Complexity:** Apply the fixes above for CC issues
3. **Extract Classes:** Split large classes into smaller, focused classes
4. **Remove Dead Code:** Eliminate unused imports, variables, and functions

#### Cognitive Complexity Issues
1. **Extract Helper Methods:** Break complex logic into smaller functions
2. **Use Early Returns:** Simplify conditional logic
3. **Replace Nested Conditionals:** Use guard clauses or early returns
4. **Improve Variable Names:** Use descriptive names to reduce mental load

### Priority Ranking
1. **Critical Priority:** Functions with CC > 30 or MI < 40
2. **High Priority:** Functions with CC > 20 or cognitive complexity > 25
3. **Medium Priority:** Functions with CC > 15 or MI < 60
4. **Low Priority:** Functions with CC > 10 or minor cognitive complexity issues

## Trend Analysis

### Monitoring Goals
- **CC Average:** Trend should be downward or stable
- **MI Average:** Trend should be upward or stable
- **Cognitive Violations:** Trend should be downward
- **Large Functions:** Number should decrease over time

### Reporting
- **Daily Reports:** Generated by CI pipeline
- **Weekly Summary:** Review of trends and hotspots
- **Monthly Assessment:** Overall code quality improvement

## Tools and Commands

### Local Analysis
```bash
# Run radon metrics locally
python scripts/run_radon_metrics.py

# Run cognitive complexity locally
python scripts/run_cognitive_metrics.py

# Run flake8 with cognitive complexity
flake8 --select=C90 --max-cognitive-complexity=15 apps/
```

### CI Integration
- **Workflow:** `.github/workflows/django-tests.yml`
- **Artifacts:** Available in GitHub Actions runs
- **Retention:** 30 days (GitHub default)

## Future Enhancements

### Planned Improvements
1. **Blocking Thresholds:** Introduce hard limits for critical issues
2. **Trend Alerts:** Automatic notifications for negative trends
3. **Historical Analysis:** Compare current metrics against baselines
4. **Interactive Reports:** Web-based dashboards for metric visualization

### Integration Points
- **SonarQube:** Potential integration for advanced analysis
- **Code Climate:** Alternative quality monitoring platform
- **Custom Dashboards:** Internal metrics visualization

## Contact and Support

- **Documentation:** `aquamind/docs/quality_assurance/`
- **Scripts:** `scripts/run_radon_metrics.py`, `scripts/run_cognitive_metrics.py`
- **CI Config:** `.github/workflows/django-tests.yml`

---

**Note:** This document should be updated as thresholds evolve and new metrics are introduced. All changes should be reviewed and approved by the development team.
