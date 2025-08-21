"""
Disease Profiles for AquaMind Data Generation

Comprehensive disease modeling based on common salmon diseases
with realistic outbreak patterns, duration, and impact.
"""

from typing import Dict, Any, List, Optional, Tuple


# Disease profiles with detailed characteristics
DISEASE_PROFILES: Dict[str, Dict[str, Any]] = {
    'PD': {  # Pancreas Disease
        'name': 'Pancreas Disease',
        'probability': 0.15,  # 15% annual probability per site
        'mortality_multiplier': 2.5,
        'duration_days': (45, 90),
        'affected_stages': ['post_smolt', 'grow_out'],
        'seasonal_bias': 'summer',  # Higher probability in warmer months
        'peak_months': [6, 7, 8],
        'symptoms': [
            'Reduced appetite',
            'Lethargy',
            'Abnormal swimming',
            'Pale gills'
        ],
        'treatment_options': [
            'medicated_feed',
            'supportive_care'
        ],
        'min_temperature': 10,  # Minimum temperature for outbreak (°C)
        'recovery_rate': 0.7  # 70% recovery rate with treatment
    },
    
    'SRS': {  # Salmonid Rickettsial Septicaemia
        'name': 'Salmonid Rickettsial Septicaemia',
        'probability': 0.08,
        'mortality_multiplier': 3.2,
        'duration_days': (30, 60),
        'affected_stages': ['smolt', 'post_smolt'],
        'seasonal_bias': 'spring',
        'peak_months': [3, 4, 5],
        'symptoms': [
            'Dark coloration',
            'Swollen abdomen',
            'Hemorrhaging',
            'Organ lesions'
        ],
        'treatment_options': [
            'antibiotic_bath',
            'medicated_feed'
        ],
        'min_temperature': 8,
        'recovery_rate': 0.6
    },
    
    'IPN': {  # Infectious Pancreatic Necrosis
        'name': 'Infectious Pancreatic Necrosis',
        'probability': 0.12,
        'mortality_multiplier': 4.0,
        'duration_days': (21, 45),
        'affected_stages': ['fry', 'parr', 'smolt'],
        'seasonal_bias': None,  # Can occur year-round
        'peak_months': [],
        'symptoms': [
            'Spiral swimming',
            'Dark coloration',
            'Distended abdomen',
            'White fecal casts'
        ],
        'treatment_options': [
            'supportive_care',
            'water_quality_management'
        ],
        'min_temperature': 4,
        'recovery_rate': 0.5
    },
    
    'HSMI': {  # Heart and Skeletal Muscle Inflammation
        'name': 'Heart and Skeletal Muscle Inflammation',
        'probability': 0.10,
        'mortality_multiplier': 1.8,
        'duration_days': (60, 120),
        'affected_stages': ['post_smolt', 'grow_out'],
        'seasonal_bias': 'winter',
        'peak_months': [11, 12, 1, 2],
        'symptoms': [
            'Reduced swimming capacity',
            'Pale heart',
            'Muscle inflammation',
            'Sudden mortality'
        ],
        'treatment_options': [
            'supportive_care',
            'reduced_handling'
        ],
        'min_temperature': 6,
        'recovery_rate': 0.75
    },
    
    'AGD': {  # Amoebic Gill Disease
        'name': 'Amoebic Gill Disease',
        'probability': 0.25,  # More common in sea phase
        'mortality_multiplier': 1.5,
        'duration_days': (30, 90),
        'affected_stages': ['post_smolt', 'grow_out'],
        'seasonal_bias': 'summer',
        'peak_months': [5, 6, 7, 8, 9],
        'symptoms': [
            'Increased gill mucus',
            'Respiratory distress',
            'Reduced appetite',
            'Gill lesions'
        ],
        'treatment_options': [
            'freshwater_bath',
            'hydrogen_peroxide_treatment'
        ],
        'min_temperature': 12,
        'recovery_rate': 0.85
    },
    
    'Furunculosis': {
        'name': 'Furunculosis',
        'probability': 0.06,
        'mortality_multiplier': 2.8,
        'duration_days': (14, 30),
        'affected_stages': ['parr', 'smolt', 'post_smolt'],
        'seasonal_bias': 'summer',
        'peak_months': [6, 7, 8],
        'symptoms': [
            'Skin lesions',
            'Hemorrhaging',
            'Loss of appetite',
            'Lethargy'
        ],
        'treatment_options': [
            'antibiotic_bath',
            'vaccination'
        ],
        'min_temperature': 10,
        'recovery_rate': 0.8
    },
    
    'ISA': {  # Infectious Salmon Anemia
        'name': 'Infectious Salmon Anemia',
        'probability': 0.02,  # Rare but serious
        'mortality_multiplier': 5.0,
        'duration_days': (30, 90),
        'affected_stages': ['post_smolt', 'grow_out'],
        'seasonal_bias': None,
        'peak_months': [],
        'symptoms': [
            'Severe anemia',
            'Pale gills',
            'Ascites',
            'High mortality'
        ],
        'treatment_options': [
            'depopulation',  # Often requires culling
            'biosecurity_measures'
        ],
        'min_temperature': 4,
        'recovery_rate': 0.3  # Low recovery rate
    },
    
    'CMS': {  # Cardiomyopathy Syndrome
        'name': 'Cardiomyopathy Syndrome',
        'probability': 0.07,
        'mortality_multiplier': 2.0,
        'duration_days': (45, 90),
        'affected_stages': ['grow_out'],
        'seasonal_bias': 'autumn',
        'peak_months': [9, 10, 11],
        'symptoms': [
            'Heart lesions',
            'Sudden mortality',
            'Reduced performance',
            'Ascites'
        ],
        'treatment_options': [
            'supportive_care',
            'stress_reduction'
        ],
        'min_temperature': 8,
        'recovery_rate': 0.65
    },
    
    'Winter_Ulcer': {
        'name': 'Winter Ulcer Disease',
        'probability': 0.09,
        'mortality_multiplier': 1.6,
        'duration_days': (30, 60),
        'affected_stages': ['post_smolt', 'grow_out'],
        'seasonal_bias': 'winter',
        'peak_months': [12, 1, 2, 3],
        'symptoms': [
            'Skin ulcers',
            'Scale loss',
            'Secondary infections',
            'Reduced appetite'
        ],
        'treatment_options': [
            'antibiotic_treatment',
            'improved_husbandry'
        ],
        'min_temperature': 2,
        'recovery_rate': 0.8
    },
    
    'Costia': {  # Costia (Ichthyobodo)
        'name': 'Costia Infection',
        'probability': 0.15,
        'mortality_multiplier': 1.4,
        'duration_days': (14, 30),
        'affected_stages': ['fry', 'parr'],
        'seasonal_bias': None,
        'peak_months': [],
        'symptoms': [
            'Blue-gray skin film',
            'Flashing behavior',
            'Respiratory distress',
            'Skin irritation'
        ],
        'treatment_options': [
            'formalin_bath',
            'salt_treatment'
        ],
        'min_temperature': 4,
        'recovery_rate': 0.9
    }
}


class DiseaseOutbreakSimulator:
    """Simulates disease outbreaks with realistic patterns."""
    
    @staticmethod
    def get_outbreak_probability(disease: str, month: int, temperature: float) -> float:
        """
        Calculate outbreak probability based on conditions.
        
        Args:
            disease: Disease identifier
            month: Month of year (1-12)
            temperature: Water temperature in Celsius
            
        Returns:
            Adjusted probability of outbreak
        """
        profile = DISEASE_PROFILES.get(disease)
        if not profile:
            return 0.0
        
        base_prob = profile['probability'] / 12  # Monthly probability
        
        # Temperature adjustment
        if temperature < profile.get('min_temperature', 0):
            return 0.0
        
        # Seasonal adjustment
        seasonal_multiplier = 1.0
        if profile.get('peak_months'):
            if month in profile['peak_months']:
                seasonal_multiplier = 1.5
            elif profile.get('seasonal_bias'):
                # Reduce probability outside peak season
                seasonal_multiplier = 0.5
        
        return base_prob * seasonal_multiplier
    
    @staticmethod
    def get_mortality_impact(disease: str, day_of_outbreak: int, 
                            treatment_applied: bool = False) -> float:
        """
        Calculate mortality impact for a given day of outbreak.
        
        Args:
            disease: Disease identifier
            day_of_outbreak: Days since outbreak started
            treatment_applied: Whether treatment has been applied
            
        Returns:
            Mortality multiplier for the day
        """
        profile = DISEASE_PROFILES.get(disease)
        if not profile:
            return 1.0
        
        base_multiplier = profile['mortality_multiplier']
        duration = profile['duration_days'][1]  # Max duration
        
        # Disease progression curve (bell-shaped)
        progress = day_of_outbreak / duration
        if progress < 0.3:
            # Building phase
            impact = base_multiplier * (progress / 0.3)
        elif progress < 0.7:
            # Peak phase
            impact = base_multiplier
        else:
            # Recovery phase
            impact = base_multiplier * (1 - (progress - 0.7) / 0.3)
        
        # Treatment reduces impact
        if treatment_applied:
            recovery_rate = profile.get('recovery_rate', 0.7)
            impact *= (1 - recovery_rate * 0.5)  # 50% reduction with treatment
        
        return max(1.0, impact)
    
    @staticmethod
    def get_treatment_protocol(disease: str, batch_value: float) -> Dict[str, Any]:
        """
        Get recommended treatment protocol for a disease.
        
        Args:
            disease: Disease identifier
            batch_value: Economic value of the batch
            
        Returns:
            Treatment protocol dictionary
        """
        profile = DISEASE_PROFILES.get(disease)
        if not profile:
            return {}
        
        treatment_options = profile.get('treatment_options', [])
        if not treatment_options:
            return {}
        
        # Select treatment based on batch value and disease severity
        if batch_value > 100000 and profile['mortality_multiplier'] > 3:
            # High-value batch with severe disease - use most effective treatment
            selected_treatment = treatment_options[0]
        else:
            # Standard treatment
            selected_treatment = treatment_options[0]
        
        return {
            'treatment': selected_treatment,
            'duration_days': 14,
            'expected_effectiveness': profile.get('recovery_rate', 0.7),
            'cost_per_kg': get_treatment_cost(selected_treatment)
        }
    
    @staticmethod
    def should_report_to_authorities(disease: str) -> bool:
        """
        Check if disease requires regulatory reporting.
        
        Args:
            disease: Disease identifier
            
        Returns:
            True if disease must be reported
        """
        # ISA and IPN typically require reporting
        reportable_diseases = ['ISA', 'IPN']
        return disease in reportable_diseases


def get_treatment_cost(treatment_type: str) -> float:
    """
    Get treatment cost per kg of biomass.
    
    Args:
        treatment_type: Type of treatment
        
    Returns:
        Cost in EUR per kg
    """
    treatment_costs = {
        'antibiotic_bath': 0.15,
        'freshwater_bath': 0.05,
        'medicated_feed': 0.25,
        'formalin_bath': 0.10,
        'salt_treatment': 0.03,
        'hydrogen_peroxide_treatment': 0.12,
        'supportive_care': 0.08,
        'vaccination': 0.20,
        'reduced_handling': 0.02,
        'water_quality_management': 0.05,
        'stress_reduction': 0.03,
        'improved_husbandry': 0.04,
        'biosecurity_measures': 0.10,
        'depopulation': 1.00  # Full loss
    }
    
    return treatment_costs.get(treatment_type, 0.10)


def get_co_infection_probability(primary_disease: str, 
                                secondary_disease: str) -> float:
    """
    Get probability of co-infection.
    
    Args:
        primary_disease: Primary disease present
        secondary_disease: Potential secondary disease
        
    Returns:
        Probability of co-infection
    """
    # Some diseases make fish more susceptible to others
    co_infection_matrix = {
        ('AGD', 'Costia'): 0.3,
        ('PD', 'CMS'): 0.2,
        ('IPN', 'Furunculosis'): 0.25,
        ('Winter_Ulcer', 'Furunculosis'): 0.35,
        ('HSMI', 'CMS'): 0.15
    }
    
    # Check both orderings
    prob = co_infection_matrix.get((primary_disease, secondary_disease), 0.0)
    if prob == 0.0:
        prob = co_infection_matrix.get((secondary_disease, primary_disease), 0.0)
    
    return prob
