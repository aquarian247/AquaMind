"""
Disease Profiles for AquaMind Data Generation

Comprehensive disease simulation system with 10 major salmon diseases,
seasonal patterns, treatment protocols, and realistic outbreak modeling.
Based on Bakkafrost operational patterns and industry standards.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import date, timedelta


@dataclass
class DiseaseProfile:
    """Complete disease profile including outbreak patterns and treatment options."""

    name: str
    full_name: str
    probability: float  # Annual probability per site (0-1)
    mortality_multiplier: float  # How much it increases mortality (1.0 = no increase)
    duration_days: Tuple[int, int]  # Min/max duration of outbreak
    affected_stages: List[str]  # Lifecycle stages vulnerable to this disease
    seasonal_bias: Optional[str]  # 'spring', 'summer', 'autumn', 'winter', or None
    primary_symptoms: List[str]
    treatment_options: Dict[str, Dict]  # Treatment type -> effectiveness details
    vaccine_available: bool
    vaccine_effectiveness: float  # 0-1
    economic_impact: float  # Cost multiplier (1.0 = normal costs)


DISEASE_PROFILES = {
    'IPN': DiseaseProfile(
        name='IPN',
        full_name='Infectious Pancreatic Necrosis',
        probability=0.12,
        mortality_multiplier=4.0,
        duration_days=(21, 45),
        affected_stages=['fry', 'parr', 'smolt'],
        seasonal_bias=None,
        primary_symptoms=['White feces', 'Spiral swimming', 'Dark coloration', 'Pinched abdomen'],
        treatment_options={
            'antibiotic_bath': {
                'effective_against': ['secondary_bacterial_infections'],
                'mortality_reduction': 0.4,
                'duration_days': 7,
                'cost_per_kg_biomass': 0.15,
                'withholding_period': 30
            },
            'supportive_care': {
                'effective_against': ['symptom_management'],
                'mortality_reduction': 0.2,
                'duration_days': 14,
                'cost_per_kg_biomass': 0.05,
                'withholding_period': 0
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.85,
        economic_impact=1.8
    ),

    'PD': DiseaseProfile(
        name='PD',
        full_name='Pancreas Disease',
        probability=0.15,
        mortality_multiplier=2.5,
        duration_days=(45, 90),
        affected_stages=['post_smolt', 'grow_out'],
        seasonal_bias='summer',
        primary_symptoms=['Exophthalmia', 'Heart lesions', 'Pancreatic necrosis', 'Reduced appetite'],
        treatment_options={
            'medicated_feed': {
                'effective_against': ['primary_infection'],
                'mortality_reduction': 0.3,
                'duration_days': 14,
                'cost_per_kg_biomass': 0.25,
                'withholding_period': 60
            },
            'antibiotic_bath': {
                'effective_against': ['secondary_infections'],
                'mortality_reduction': 0.2,
                'duration_days': 7,
                'cost_per_kg_biomass': 0.12,
                'withholding_period': 30
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.75,
        economic_impact=2.2
    ),

    'SRS': DiseaseProfile(
        name='SRS',
        full_name='Salmonid Rickettsial Septicaemia',
        probability=0.08,
        mortality_multiplier=3.2,
        duration_days=(30, 60),
        affected_stages=['smolt', 'post_smolt'],
        seasonal_bias='spring',
        primary_symptoms=['Anaemia', 'Splenomegaly', 'Renal lesions', 'Pale gills'],
        treatment_options={
            'antibiotic_bath': {
                'effective_against': ['primary_bacterial_infection'],
                'mortality_reduction': 0.6,
                'duration_days': 10,
                'cost_per_kg_biomass': 0.18,
                'withholding_period': 45
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.7,
        economic_impact=2.5
    ),

    'HSMI': DiseaseProfile(
        name='HSMI',
        full_name='Heart and Skeletal Muscle Inflammation',
        probability=0.10,
        mortality_multiplier=1.8,
        duration_days=(60, 120),
        affected_stages=['post_smolt', 'grow_out'],
        seasonal_bias='winter',
        primary_symptoms=['Heart inflammation', 'Skeletal muscle inflammation', 'Reduced growth', 'Poor feed conversion'],
        treatment_options={
            'medicated_feed': {
                'effective_against': ['secondary_infections'],
                'mortality_reduction': 0.25,
                'duration_days': 21,
                'cost_per_kg_biomass': 0.20,
                'withholding_period': 90
            },
            'supportive_care': {
                'effective_against': ['symptom_management'],
                'mortality_reduction': 0.15,
                'duration_days': 30,
                'cost_per_kg_biomass': 0.08,
                'withholding_period': 0
            }
        },
        vaccine_available=False,
        vaccine_effectiveness=0.0,
        economic_impact=1.6
    ),

    'AGD': DiseaseProfile(
        name='AGD',
        full_name='Amoebic Gill Disease',
        probability=0.25,
        mortality_multiplier=1.5,
        duration_days=(30, 90),
        affected_stages=['post_smolt', 'grow_out'],
        seasonal_bias='summer',
        primary_symptoms=['Gill hyperplasia', 'Mucus production', 'Respiratory distress', 'Reduced appetite'],
        treatment_options={
            'freshwater_bath': {
                'effective_against': ['primary_parasitic_infection'],
                'mortality_reduction': 0.5,
                'duration_days': 1,
                'cost_per_kg_biomass': 0.08,
                'withholding_period': 7
            },
            'hydrogen_peroxide_bath': {
                'effective_against': ['amoebic_infection'],
                'mortality_reduction': 0.4,
                'duration_days': 1,
                'cost_per_kg_biomass': 0.12,
                'withholding_period': 14
            }
        },
        vaccine_available=False,
        vaccine_effectiveness=0.0,
        economic_impact=1.4
    ),

    'VHS': DiseaseProfile(
        name='VHS',
        full_name='Viral Haemorrhagic Septicaemia',
        probability=0.06,
        mortality_multiplier=3.5,
        duration_days=(14, 28),
        affected_stages=['fry', 'parr', 'smolt'],
        seasonal_bias='spring',
        primary_symptoms=['Haemorrhages', 'Anaemia', 'Renal necrosis', 'Dark coloration'],
        treatment_options={
            'antibiotic_bath': {
                'effective_against': ['secondary_bacterial_infections'],
                'mortality_reduction': 0.3,
                'duration_days': 7,
                'cost_per_kg_biomass': 0.15,
                'withholding_period': 30
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.9,
        economic_impact=2.8
    ),

    'IHNV': DiseaseProfile(
        name='IHNV',
        full_name='Infectious Haematopoietic Necrosis Virus',
        probability=0.09,
        mortality_multiplier=2.8,
        duration_days=(21, 42),
        affected_stages=['fry', 'parr', 'smolt'],
        seasonal_bias='spring',
        primary_symptoms=['Necrotic lesions', 'Anaemia', 'Dark coloration', 'Erratic swimming'],
        treatment_options={
            'supportive_care': {
                'effective_against': ['symptom_management'],
                'mortality_reduction': 0.2,
                'duration_days': 21,
                'cost_per_kg_biomass': 0.06,
                'withholding_period': 0
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.85,
        economic_impact=2.3
    ),

    'CMS': DiseaseProfile(
        name='CMS',
        full_name='Cardiomyopathy Syndrome',
        probability=0.04,
        mortality_multiplier=1.6,
        duration_days=(90, 180),
        affected_stages=['grow_out'],
        seasonal_bias='winter',
        primary_symptoms=['Heart lesions', 'Reduced cardiac output', 'Poor growth', 'Sudden death'],
        treatment_options={
            'medicated_feed': {
                'effective_against': ['secondary_infections'],
                'mortality_reduction': 0.15,
                'duration_days': 30,
                'cost_per_kg_biomass': 0.18,
                'withholding_period': 120
            }
        },
        vaccine_available=False,
        vaccine_effectiveness=0.0,
        economic_impact=1.5
    ),

    'ISA': DiseaseProfile(
        name='ISA',
        full_name='Infectious Salmon Anaemia',
        probability=0.03,
        mortality_multiplier=4.5,
        duration_days=(60, 120),
        affected_stages=['grow_out'],
        seasonal_bias='autumn',
        primary_symptoms=['Anaemia', 'Haemorrhages', 'Liver necrosis', 'High mortality'],
        treatment_options={
            'antibiotic_bath': {
                'effective_against': ['secondary_infections'],
                'mortality_reduction': 0.2,
                'duration_days': 14,
                'cost_per_kg_biomass': 0.22,
                'withholding_period': 60
            }
        },
        vaccine_available=True,
        vaccine_effectiveness=0.6,
        economic_impact=3.5
    ),

    'YWD': DiseaseProfile(
        name='YWD',
        full_name='Yellowtail Disease',
        probability=0.11,
        mortality_multiplier=2.2,
        duration_days=(30, 60),
        affected_stages=['post_smolt', 'grow_out'],
        seasonal_bias='summer',
        primary_symptoms=['Yellowish coloration', 'Liver lesions', 'Reduced appetite', 'Poor growth'],
        treatment_options={
            'medicated_feed': {
                'effective_against': ['primary_infection'],
                'mortality_reduction': 0.35,
                'duration_days': 14,
                'cost_per_kg_biomass': 0.16,
                'withholding_period': 45
            }
        },
        vaccine_available=False,
        vaccine_effectiveness=0.0,
        economic_impact=1.9
    )
}


class DiseaseSimulator:
    """
    Disease outbreak simulation with seasonal patterns and realistic timing.
    """

    def __init__(self):
        self.active_outbreaks = {}  # batch_id -> disease info
        self.outbreak_history = []  # Historical outbreak tracking

    def check_disease_outbreak(self, batch, current_date: date) -> Optional[str]:
        """
        Check if a disease outbreak should occur for the given batch.

        Args:
            batch: Batch object
            current_date: Current simulation date

        Returns:
            Disease name if outbreak occurs, None otherwise
        """
        import random

        # Get batch lifecycle stage
        stage = batch.lifecycle_stage.name if hasattr(batch.lifecycle_stage, 'name') else str(batch.lifecycle_stage).lower()

        # Calculate monthly probability
        month = current_date.month
        season = self._get_season(month)

        for disease_name, profile in DISEASE_PROFILES.items():
            # Check if stage is affected
            if stage not in profile.affected_stages:
                continue

            # Calculate adjusted probability
            base_prob = profile.probability / 12  # Monthly probability

            # Apply seasonal bias
            seasonal_multiplier = self._get_seasonal_multiplier(profile.seasonal_bias, season)
            adjusted_prob = base_prob * seasonal_multiplier

            # Check for outbreak
            if random.random() < adjusted_prob:
                return disease_name

        return None

    def start_disease_outbreak(self, batch, disease_name: str, start_date: date) -> Dict:
        """
        Start a disease outbreak for a batch.

        Args:
            batch: Batch object
            disease_name: Name of the disease
            start_date: Date when outbreak starts

        Returns:
            Outbreak information dictionary
        """
        import random

        profile = DISEASE_PROFILES[disease_name]

        # Calculate outbreak duration
        duration = random.randint(profile.duration_days[0], profile.duration_days[1])
        end_date = start_date + timedelta(days=duration)

        outbreak_info = {
            'batch_id': batch.id,
            'disease_name': disease_name,
            'start_date': start_date,
            'end_date': end_date,
            'duration_days': duration,
            'mortality_multiplier': profile.mortality_multiplier,
            'primary_symptoms': profile.primary_symptoms,
            'treatment_applied': False,
            'treatment_effectiveness': 0.0,
            'economic_impact': profile.economic_impact
        }

        # Store in active outbreaks
        self.active_outbreaks[batch.id] = outbreak_info

        # Add to history
        self.outbreak_history.append(outbreak_info.copy())

        return outbreak_info

    def get_active_outbreak(self, batch_id: int) -> Optional[Dict]:
        """Get active outbreak for a batch, if any."""
        return self.active_outbreaks.get(batch_id)

    def end_disease_outbreak(self, batch_id: int, end_date: date):
        """End a disease outbreak for a batch."""
        if batch_id in self.active_outbreaks:
            outbreak = self.active_outbreaks[batch_id]
            outbreak['actual_end_date'] = end_date
            del self.active_outbreaks[batch_id]

    def apply_treatment(self, batch_id: int, treatment_type: str) -> bool:
        """
        Apply treatment to an active outbreak.

        Args:
            batch_id: Batch ID
            treatment_type: Type of treatment to apply

        Returns:
            True if treatment was applied successfully
        """
        if batch_id not in self.active_outbreaks:
            return False

        outbreak = self.active_outbreaks[batch_id]
        profile = DISEASE_PROFILES[outbreak['disease_name']]

        # Check if treatment is available for this disease
        if treatment_type not in profile.treatment_options:
            return False

        treatment_info = profile.treatment_options[treatment_type]
        outbreak['treatment_applied'] = True
        outbreak['treatment_type'] = treatment_type
        outbreak['treatment_effectiveness'] = treatment_info['mortality_reduction']

        return True

    def _get_season(self, month: int) -> str:
        """Get season from month number."""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'

    def _get_seasonal_multiplier(self, seasonal_bias: Optional[str], current_season: str) -> float:
        """Calculate seasonal probability multiplier."""
        if seasonal_bias is None:
            return 1.0

        if seasonal_bias == current_season:
            # Higher probability in bias season
            return 2.0
        elif abs(self._season_difference(seasonal_bias, current_season)) == 2:
            # Lower probability in opposite season
            return 0.5
        else:
            # Normal probability in adjacent seasons
            return 1.0

    def _season_difference(self, season1: str, season2: str) -> int:
        """Calculate difference between two seasons."""
        seasons = ['winter', 'spring', 'summer', 'autumn']
        idx1 = seasons.index(season1)
        idx2 = seasons.index(season2)

        diff = abs(idx1 - idx2)
        return min(diff, 4 - diff)


# Treatment system configuration
TREATMENT_PROTOCOLS = {
    'vaccination': {
        'timing': 'pre_transfer',
        'duration_days': 1,
        'cost_per_kg': 0.02,
        'withholding_period_days': 0,
        'effectiveness_period_months': 6
    },
    'antibiotic_bath': {
        'timing': 'as_needed',
        'duration_days': 7,
        'cost_per_kg': 0.15,
        'withholding_period_days': 30,
        'effectiveness_period_days': 14
    },
    'freshwater_bath': {
        'timing': 'as_needed',
        'duration_days': 1,
        'cost_per_kg': 0.05,
        'withholding_period_days': 7,
        'effectiveness_period_days': 30
    },
    'medicated_feed': {
        'timing': 'continuous',
        'duration_days': 14,
        'cost_per_kg': 0.25,
        'withholding_period_days': 60,
        'effectiveness_period_days': 21
    },
    'supportive_care': {
        'timing': 'continuous',
        'duration_days': 30,
        'cost_per_kg': 0.08,
        'withholding_period_days': 0,
        'effectiveness_period_days': 90
    }
}

# Health monitoring thresholds
HEALTH_THRESHOLDS = {
    'mortality_rate_threshold': 0.02,  # 2% daily mortality triggers investigation
    'feed_conversion_threshold': 1.4,  # FCR above 1.4 triggers investigation
    'growth_rate_threshold': 0.8,      # Below 80% of expected growth triggers investigation
    'lice_count_threshold': 0.5        # Adult female lice per fish triggers treatment
}