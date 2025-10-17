# Lice Tracking Guide for AquaMind Operators

## Overview

AquaMind provides two methods for tracking sea lice counts:
1. **Legacy Format** (Simple - for quick data entry)
2. **Normalized Format** (Detailed - for regulatory reporting and analysis)

This guide explains when to use each format and how to properly record lice counts.

---

## Lice Types in AquaMind

The system tracks the following lice species and development stages:

### Lepeophtheirus salmonis (Salmon Louse)
- **Copepodid**: Free-swimming larval stage, infectious to fish
- **Chalimus**: Attached juvenile stage (chalimus I-IV)
- **Pre-adult**: Mobile pre-adult stage
- **Adult**: Mature lice (gravid females are regulatory focus)

### Caligus elongatus
- **Juvenile**: Combined early stages
- **Adult**: Mature Caligus lice

### Unknown Species
- For cases where species identification is uncertain

---

## Recording Lice Counts

### Legacy Format (Quick Entry)

**When to Use:**
- Quick field counts where detailed classification isn't needed
- Existing workflows that aggregate by maturity/gender only
- Situations where species identification isn't critical

**Fields:**
- `adult_female_count`: Total adult female lice
- `adult_male_count`: Total adult male lice
- `juvenile_count`: Total juvenile/immature lice
- `fish_sampled`: Number of fish examined

**Example:**
```
Batch: B-2024-001
Container: Pen 12
Fish Sampled: 20
Adult Females: 45
Adult Males: 30
Juveniles: 125
```

### Normalized Format (Detailed Tracking)

**When to Use:**
- Regulatory reporting (Scottish, Faroese authorities)
- Integration with Tidal system
- Detailed lice management programs
- Research and analysis requiring species-level data

**Fields:**
- `lice_type`: Select from dropdown (species + gender + development stage)
- `count_value`: Total count for selected lice type
- `detection_method`: How lice were counted
  - `automated`: Automated detection system
  - `manual`: Manual visual count under microscope
  - `visual`: Visual estimation in water
  - `camera`: Camera-based counting
- `confidence_level`: 0.00-1.00 (1.00 = highest confidence)
- `fish_sampled`: Number of fish examined

**Example:**
```
Batch: B-2024-001
Container: Pen 12
Fish Sampled: 20
Lice Type: L. salmonis - Female - Adult
Count: 45
Detection Method: Manual
Confidence: 0.95
```

**Multiple Entries for Same Sample:**
You'll create multiple LiceCount records for the same sampling event,
one for each lice type observed:

```
Entry 1: L. salmonis - Female - Adult (45 lice)
Entry 2: L. salmonis - Male - Adult (30 lice)
Entry 3: L. salmonis - unknown - Chalimus (125 lice)
```

---

## Regulatory Reporting

### Scottish Authorities
- Require detailed species and development stage breakdown
- **Use Normalized Format**
- Focus on L. salmonis adult females (gravid)

### Faroese Authorities
- Accept broader categories
- **Either Format Acceptable**
- Total mature lice counts are primary metric

---

## API Endpoints

### Create Lice Count (Legacy)
```
POST /api/v1/health/lice-counts/
{
  "batch": 123,
  "container": 456,
  "fish_sampled": 20,
  "adult_female_count": 45,
  "adult_male_count": 30,
  "juvenile_count": 125,
  "notes": "Routine monitoring"
}
```

### Create Lice Count (Normalized)
```
POST /api/v1/health/lice-counts/
{
  "batch": 123,
  "container": 456,
  "fish_sampled": 20,
  "lice_type": 4,
  "count_value": 45,
  "detection_method": "manual",
  "confidence_level": 0.95,
  "notes": "Adult females only"
}
```

### Get Lice Types
```
GET /api/v1/health/lice-types/
GET /api/v1/health/lice-types/?species=Lepeophtheirus salmonis
GET /api/v1/health/lice-types/?development_stage=adult
```

### Get Lice Count Summary
```
GET /api/v1/health/lice-counts/summary/
GET /api/v1/health/lice-counts/summary/?geography=1
GET /api/v1/health/lice-counts/summary/?area=5
GET /api/v1/health/lice-counts/summary/?start_date=2024-01-01&end_date=2024-12-31

Response:
{
  "total_counts": 1250,
  "average_per_fish": 6.25,
  "fish_sampled": 200,
  "by_species": {
    "Lepeophtheirus salmonis": 1100,
    "Caligus elongatus": 150
  },
  "by_development_stage": {
    "adult": 450,
    "chalimus": 500,
    "copepodid": 150,
    "pre-adult": 150
  },
  "alert_level": "critical"
}
```

### Get Lice Count Trends
```
GET /api/v1/health/lice-counts/trends/?interval=weekly
GET /api/v1/health/lice-counts/trends/?interval=monthly&geography=1
GET /api/v1/health/lice-counts/trends/?start_date=2023-01-01&end_date=2024-12-31

Response:
{
  "trends": [
    {
      "period": "2024-01-01",
      "average_per_fish": 3.5,
      "total_counts": 700,
      "fish_sampled": 200
    },
    {
      "period": "2024-01-08",
      "average_per_fish": 4.2,
      "total_counts": 840,
      "fish_sampled": 200
    }
  ]
}
```

---

## Alert Levels

The system automatically calculates alert levels based on mature lice thresholds:

| Average Lice Per Fish | Alert Level | Action Required |
|----------------------|-------------|----------------|
| < 0.5 | Good (Green) | Continue monitoring |
| 0.5 - 1.0 | Warning (Yellow) | Increase sampling frequency |
| > 1.0 | Critical (Red) | Treatment recommended |

---

## Best Practices

1. **Consistency**: Choose one format per facility/region and stick with it
2. **Accuracy**: Record counts immediately after sampling
3. **Confidence**: Note detection method and confidence level for normalized format
4. **Notes**: Document any unusual findings or sampling conditions
5. **Frequency**: Sample at regular intervals (weekly recommended)
6. **Migration**: Consider migrating to normalized format for better analytics

---

## Migration from Legacy to Normalized Format

If transitioning from legacy to normalized format:

1. **Training**: Ensure operators can identify lice species and stages
2. **Equipment**: Provide magnification tools for accurate identification
3. **Reference Cards**: Distribute lice identification guides
4. **Parallel Tracking**: Run both formats briefly to verify consistency
5. **Data Quality**: Monitor confidence levels during transition

---

## Support

For questions about lice tracking or assistance with the system, contact:
- Technical Support: IT Department
- Operational Questions: Veterinary Staff
- System Issues: AquaMind Development Team

