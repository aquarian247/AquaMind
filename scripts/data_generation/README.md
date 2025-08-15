# AquaMind Test Data Generation Scripts

This directory contains scripts for generating comprehensive test data for the AquaMind system, following the established data model and application architecture.

## Main Script

- `generate_batch_lifecycle.py` - Primary script that generates complete test data including batches with full lifecycle progression, environmental readings, growth metrics, feeding events, and mortality records.

## Module Structure

The data generation system is organized into modules for better maintainability and extensibility:

- `modules/batch_manager.py` - Manages batch creation, lifecycle progression, and container assignments
- `modules/environmental_manager.py` - Generates environmental readings with appropriate parameters by lifecycle stage
- `modules/feed_manager.py` - Handles feed types, feeding events, and feed consumption patterns
- `modules/growth_manager.py` - Creates growth samples and metrics with realistic growth curves
- `modules/mortality_manager.py` - Generates mortality events with appropriate patterns and causes
- `modules/health_manager.py` - Produces health-related data such as veterinary journal entries, sampling events, lice counts, treatments, and lab samples

## Running the Scripts

The proper way to run these scripts is through the provided utility script to ensure all imports work correctly:

```bash
# From project root
python -m scripts.utils.run_data_generation

# With options
python -m scripts.utils.run_data_generation --days 900 --start-date 2023-01-01
```

You can also run the data generation script directly (if you know what you're doing):

```bash
# From project root
python -m scripts.data_generation.generate_batch_lifecycle
```

### Options

- `--days N` - Number of days to generate data for (default: 900)
- `--start-date YYYY-MM-DD` - Start date for data generation (default: 900 days ago)

## Generated Data

This script generates:

1. **Batch Lifecycle**: Complete batch with progression through all lifecycle stages (Egg&Alevin → Fry → Parr → Smolt → Post-Smolt → Adult)
2. **Environmental Readings**: Time-series environmental data (8 readings per day) with stage-appropriate parameters:
   - Temperature, pH, Oxygen, and Salinity values appropriate for each lifecycle stage
   - Values follow natural daily and seasonal patterns
3. **Growth Samples**: Weekly growth metrics showing realistic growth patterns:
   - Linear growth in freshwater stages
   - Sigmoid growth curve in sea pens
   - Appropriate weight and length ranges for each stage
4. **Feeding Events**: Regular feeding (4 times daily) with:
   - Stage-appropriate feed types
   - Feeding rates as percentage of biomass
   - Feed Conversion Ratio (FCR) calculations
5. **Mortality Events**: Daily mortality records with:
   - Stage-appropriate mortality rates
   - Realistic causes of mortality
6. **Health Monitoring**:
   - **Journal Entries**: Weekly veterinary notes with issue severity and tags
   - **Health Sampling Events**: Monthly sampling with 10-30 individual fish assessed (weight, length, K-factor, parameter scores)
   - **Lice Counts**: Bi-weekly counts for sea stages with seasonal variation
   - **Treatments**: Generated when thresholds are exceeded – includes vaccinations, lice treatments (freshwater/chemical/thermal/mechanical), antibiotics, and supportive care
   - **Lab Samples**: Quarterly blood, gill, tissue, fecal, or water samples with realistic results
   - Occasional mortality spikes

## Technical Notes

- The scripts are designed to work with both PostgreSQL/TimescaleDB and SQLite databases
- TimescaleDB-specific operations are conditionally executed based on database detection
- Environmental readings are stored in TimescaleDB hypertables when available
- All data generation follows a realistic temporal progression
- Health data follows industry practices:
  - Higher lice pressure during warmer months (May–September)
  - Lice treatments only applied when adult female counts exceed threshold (0.5 per fish) and respect minimum 14-day intervals
  - Vaccinations scheduled once per batch during Parr/Smolt freshwater stages
  - Treatments include dosage, duration, withholding periods, and outcome success rates
  - Lab sample “abnormal” flags correlate with journal issues to create meaningful follow-ups

## Data Validity

The generated test data:
- Follows industry-standard metrics and progression patterns for Atlantic Salmon farming
- Includes realistic environmental parameters for each lifecycle stage
- Models growth using established patterns (linear in freshwater, sigmoid in sea)
- Accounts for appropriate biomass loading in containers

## Extending the System

To extend the data generation system:
1. Add new functionality to the appropriate module in the `modules/` directory
2. Update the main orchestration script to call your new functionality
3. Add any needed command-line arguments to both the main script and utility wrapper
