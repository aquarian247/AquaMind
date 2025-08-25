"""
Generation Parameters for AquaMind Data Generation

Central configuration for all data generation parameters based on
the technical specification and Bakkafrost operational patterns.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from decimal import Decimal


@dataclass
class GenerationParameters:
    """Central configuration for data generation parameters."""
    
    # ==================== BATCH MANAGEMENT ====================
    
    # Target number of active batches to maintain
    TARGET_ACTIVE_BATCHES = 45  # 40-50 range
    MIN_ACTIVE_BATCHES = 40
    MAX_ACTIVE_BATCHES = 50
    
    # Batch initialization parameters
    EGG_COUNT_MIN = 3_000_000
    EGG_COUNT_MAX = 3_500_000
    EGG_COUNT_MEAN = 3_250_000
    EGG_COUNT_STDDEV = 250_000
    
    # Egg sourcing (60% external, 40% internal)
    EXTERNAL_EGG_PROBABILITY = 0.6
    
    # Batch naming convention
    BATCH_NAME_PREFIX = "BAK"  # Format: BAK{year}{week}{number}
    
    # ==================== LIFECYCLE STAGES ====================
    
    # Stage durations in days (min, max)
    STAGE_DURATIONS = {
        'egg': (85, 95),
        'alevin': (85, 95),
        'fry': (85, 95),
        'parr': (85, 95),
        'smolt': (85, 95),
        'post_smolt': (85, 95),
        'grow_out': (400, 500)
    }
    
    # Container type progression
    CONTAINER_PROGRESSION = {
        'egg': 'incubation tray',
        'alevin': 'start tank',
        'fry': 'circular tank small',
        'parr': 'circular tank large',
        'smolt': 'pre-transfer tank',
        'post_smolt': 'pre-transfer tank',  # FIXED: Post-smolt is freshwater, not sea
        'grower': 'sea_cage_large'
    }
    
    # Infrastructure scaling constants
    SEA_AREAS_PER_GEOGRAPHY = 15
    FRESHWATER_STATIONS_PER_GEOGRAPHY = 15
    HALLS_PER_STATION = 5
    CAGES_PER_SEA_AREA = 20  # 15-25 range per Bakkafrost model, starting at 20
    FEED_SILOS_PER_HALL = 2
    FEED_BARGES_PER_SEA_AREA = 3
    
    # ==================== GROWTH MODELING ====================
    
    # TGC (Thermal Growth Coefficient) values by stage
    TGC_VALUES = {
        'alevin': (0.8, 1.2),
        'fry': (1.0, 1.4),
        'parr': (1.2, 1.6),
        'smolt': (1.4, 1.8),
        'post_smolt': (1.6, 2.0),
        'grow_out': (1.8, 2.2)
    }
    
    # Initial weights by stage (grams)
    INITIAL_WEIGHTS = {
        'egg': 0.1,
        'alevin': 0.15,
        'fry': 0.5,
        'parr': 5.0,
        'smolt': 50.0,
        'post_smolt': 100.0,
        'grow_out': 500.0
    }
    
    # Target harvest weight (grams)
    TARGET_HARVEST_WEIGHT_MIN = 4500  # 4.5 kg
    TARGET_HARVEST_WEIGHT_MAX = 5500  # 5.5 kg
    
    # ==================== MORTALITY RATES ====================
    
    # Base mortality rates (cumulative percentage for stage)
    BASE_MORTALITY_RATES = {
        'egg': 15.0,        # 15% cumulative
        'alevin': 8.0,      # 8% cumulative
        'fry': 5.0,         # 5% cumulative
        'parr': 3.0,        # 3% cumulative
        'smolt': 2.0,       # 2% cumulative
        'post_smolt': 1.5,  # 1.5% monthly
        'grow_out': 0.8     # 0.8% monthly
    }
    
    # Mortality causes and their relative frequencies
    MORTALITY_CAUSES = {
        'freshwater': {
            'Handling': 0.3,
            'Disease': 0.25,
            'Environmental': 0.2,
            'Predation': 0.1,
            'Unknown': 0.15
        },
        'seawater': {
            'Disease': 0.35,
            'Predation': 0.2,
            'Environmental': 0.15,
            'Handling': 0.1,
            'Escape': 0.05,
            'Unknown': 0.15
        }
    }
    
    # ==================== FEED MANAGEMENT ====================
    
    # Feed types and specifications
    FEED_TYPES = {
        'starter_0.5mm': {
            'stages': ['fry'],
            'protein_percent': 55,
            'fat_percent': 18,
            'price_base_eur': 2.8
        },
        'starter_1.0mm': {
            'stages': ['parr'],
            'protein_percent': 52,
            'fat_percent': 20,
            'price_base_eur': 2.6
        },
        'grower_2.0mm': {
            'stages': ['smolt'],
            'protein_percent': 48,
            'fat_percent': 22,
            'price_base_eur': 2.2
        },
        'grower_3.0mm': {
            'stages': ['post_smolt'],
            'protein_percent': 45,
            'fat_percent': 24,
            'price_base_eur': 2.0
        },
        'finisher_4.5mm': {
            'stages': ['grow_out'],
            'protein_percent': 42,
            'fat_percent': 28,
            'price_base_eur': 1.9
        },
        'finisher_6.0mm': {
            'stages': ['grow_out'],
            'protein_percent': 40,
            'fat_percent': 30,
            'price_base_eur': 1.8
        }
    }
    
    # Feed rates as percentage of body weight per day
    FEED_RATES = {
        'fry': 8.0,
        'parr': 6.0,
        'smolt': 4.0,
        'post_smolt': 2.5,
        'grow_out': 1.5
    }
    
    # FCR (Feed Conversion Ratio) targets by stage
    FCR_TARGETS = {
        'fry': 0.8,
        'parr': 0.9,
        'smolt': 1.0,
        'post_smolt': 1.1,
        'grow_out': 1.2
    }
    
    # Feed inventory reorder thresholds (kg)
    REORDER_THRESHOLDS = {
        'starter_0.5mm': 5000,
        'starter_1.0mm': 8000,
        'grower_2.0mm': 15000,
        'grower_3.0mm': 25000,
        'finisher_4.5mm': 50000,
        'finisher_6.0mm': 75000
    }
    
    # ==================== ENVIRONMENTAL PARAMETERS ====================
    
    # Temperature ranges by site type and season (°C)
    TEMPERATURE_RANGES = {
        'freshwater': {
            'winter': (4, 8),
            'spring': (6, 12),
            'summer': (10, 16),
            'autumn': (6, 12)
        },
        'seawater': {
            'winter': (6, 10),
            'spring': (8, 12),
            'summer': (12, 18),
            'autumn': (8, 14)
        }
    }
    
    # Oxygen levels (mg/L)
    OXYGEN_RANGES = {
        'freshwater': (8, 14),
        'seawater': (6, 12)
    }
    
    # pH ranges
    PH_RANGES = {
        'freshwater': (6.5, 8.5),
        'seawater': (7.5, 8.3)
    }
    
    # Salinity (ppt) - seawater only
    SALINITY_RANGE = (32, 36)
    
    # Environmental reading frequency (per day)
    ENVIRONMENTAL_READINGS_PER_DAY = 8
    
    # ==================== FACILITY MANAGEMENT ====================
    
    # Grace periods (days) - time between uses for cleaning/disinfection
    GRACE_PERIODS = {
        'incubation_tray': 7,
        'start_tank': 14,
        'circular_tank': 14,
        'raceway': 21,
        'sea_cage': 30  # Fallowing period
    }
    
    # Facility capacities
    FACILITY_CAPACITIES = {
        'incubation_tray': 500_000,     # eggs
        'start_tank': 250_000,          # alevin/fry
        'circular_tank_small': 100_000,  # fry/parr
        'circular_tank_large': 50_000,   # parr/smolt
        'pre_transfer_tank': 30_000,     # smolt
        'sea_cage_large': 25_000,        # post-smolt
        'sea_cage_standard': 20_000      # grow-out
    }
    
    # ==================== HEALTH MANAGEMENT ====================
    
    # Vaccination protocols
    VACCINATION_TIMING = {
        'standard': {
            'stage': 'smolt',
            'days_before_transfer': 30,
            'vaccines': ['IPN', 'VHS', 'IHNV'],
            'effectiveness': 0.85
        },
        'enhanced': {
            'stage': 'smolt',
            'days_before_transfer': 45,
            'vaccines': ['IPN', 'VHS', 'IHNV', 'PD', 'SRS'],
            'effectiveness': 0.78
        }
    }
    
    # Treatment effectiveness
    TREATMENT_EFFECTIVENESS = {
        'antibiotic_bath': 0.6,
        'freshwater_bath': 0.4,
        'medicated_feed': 0.3,
        'mechanical_delicing': 0.7,
        'thermal_treatment': 0.5
    }
    
    # Lice threshold for treatment (adult females per fish)
    LICE_TREATMENT_THRESHOLD = 0.5
    
    # ==================== SEASONAL PATTERNS ====================
    
    # Batch start frequency multipliers by month
    BATCH_START_MULTIPLIERS = {
        1: 1.3,   # January - higher
        2: 1.2,   # February
        3: 1.1,   # March
        4: 0.9,   # April
        5: 0.8,   # May
        6: 0.7,   # June - lower
        7: 0.7,   # July
        8: 0.8,   # August
        9: 0.9,   # September
        10: 1.0,  # October
        11: 1.1,  # November
        12: 1.2   # December
    }
    
    # Feed price seasonal multipliers (Q1-Q4)
    FEED_PRICE_SEASONAL = {
        'Q1': 1.05,
        'Q2': 0.98,
        'Q3': 1.02,
        'Q4': 1.08
    }
    
    # ==================== DATA GENERATION SETTINGS ====================
    
    # Chunk size for batch processing (days)
    GENERATION_CHUNK_SIZE = 30
    
    # Database batch insert size
    DB_BATCH_SIZE = 5000
    
    # Memory check interval (number of records)
    MEMORY_CHECK_INTERVAL = 10000
    
    # Random seed for reproducibility
    RANDOM_SEED = 42
    
    @classmethod
    def get_stage_duration(cls, stage: str) -> Tuple[int, int]:
        """Get duration range for a lifecycle stage."""
        return cls.STAGE_DURATIONS.get(stage, (90, 90))
    
    @classmethod
    def get_tgc_value(cls, stage: str) -> Tuple[float, float]:
        """Get TGC value range for a stage."""
        return cls.TGC_VALUES.get(stage, (1.0, 1.5))
    
    @classmethod
    def get_feed_type_for_stage(cls, stage: str) -> str:
        """Get appropriate feed type for a lifecycle stage."""
        for feed_type, specs in cls.FEED_TYPES.items():
            if stage in specs['stages']:
                return feed_type
        return 'grower_2.0mm'  # Default
    
    @classmethod
    def get_mortality_cause(cls, is_seawater: bool, random_value: float) -> str:
        """
        Get mortality cause based on probability distribution.
        
        Args:
            is_seawater: Whether the batch is in seawater
            random_value: Random value between 0 and 1
            
        Returns:
            Mortality cause string
        """
        causes = cls.MORTALITY_CAUSES['seawater' if is_seawater else 'freshwater']
        cumulative = 0
        
        for cause, probability in causes.items():
            cumulative += probability
            if random_value <= cumulative:
                return cause
        
        return 'Unknown'
    
    @classmethod
    def get_season(cls, month: int) -> str:
        """Get season from month number."""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'

