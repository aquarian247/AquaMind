"""
Disease Generator for AquaMind Data Generation

Implements comprehensive disease outbreak simulation with 10 major salmon diseases,
seasonal patterns, treatment protocols, and realistic health management.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage
from apps.health.models import (
    JournalEntry, HealthSamplingEvent,
    Treatment, HealthLabSample, SampleType
)
from apps.infrastructure.models import Container
from scripts.data_generation.config.disease_profiles import (
    DISEASE_PROFILES, DiseaseSimulator, TREATMENT_PROTOCOLS, HEALTH_THRESHOLDS
)

logger = logging.getLogger(__name__)
User = get_user_model()


class DiseaseGenerator:
    """
    Generates comprehensive disease outbreak scenarios including:
    - Disease outbreak simulation with seasonal patterns
    - Treatment application and effectiveness tracking
    - Health monitoring and veterinary journal entries
    - Lab sampling and health observations
    - Mortality spike events during outbreaks
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize the disease generator.

        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run
        self.disease_simulator = DiseaseSimulator()

        # Get or create system user
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='health_monitor',
                defaults={
                    'email': 'health@aquamind.com',
                    'first_name': 'Health',
                    'last_name': 'Monitor',
                    'is_staff': False,
                    'is_active': True
                }
            )

        # Treatment withholding tracker
        self.active_treatments = {}  # batch_id -> treatment end dates
        self.vaccination_records = {}  # batch_id -> vaccination info

    def simulate_daily_health_operations(self, current_date: date) -> Dict[str, int]:
        """
        Simulate daily health operations for all active batches.

        Args:
            current_date: Current simulation date

        Returns:
            Dictionary with counts of operations performed
        """
        if self.dry_run:
            logger.info("Would simulate daily health operations")
            return {'outbreaks_checked': 0, 'treatments_applied': 0, 'observations_made': 0}

        with transaction.atomic():
            operations_count = {
                'outbreaks_checked': 0,
                'new_outbreaks': 0,
                'treatments_applied': 0,
                'journal_entries': 0,
                'observations_made': 0,
                'lab_samples': 0
            }

            # Get all active batches
            active_batches = Batch.objects.filter(status='ACTIVE')

            for batch in active_batches:
                operations_count['outbreaks_checked'] += 1

                # Check for disease outbreaks
                disease_name = self.disease_simulator.check_disease_outbreak(batch, current_date)
                if disease_name:
                    self._start_disease_outbreak(batch, disease_name, current_date)
                    operations_count['new_outbreaks'] += 1

                # Check for active outbreaks and apply treatments
                active_outbreak = self.disease_simulator.get_active_outbreak(batch.id)
                if active_outbreak:
                    # Apply treatment if needed
                    if not active_outbreak.get('treatment_applied'):
                        treatment_applied = self._apply_disease_treatment(batch, active_outbreak, current_date)
                        if treatment_applied:
                            operations_count['treatments_applied'] += 1

                    # Create health observation for outbreak
                    self._create_health_observation(batch, active_outbreak, current_date)
                    operations_count['observations_made'] += 1

                    # Create journal entry for serious outbreaks
                    if active_outbreak['mortality_multiplier'] > 2.0:
                        self._create_journal_entry(batch, active_outbreak, current_date)
                        operations_count['journal_entries'] += 1

                # Regular health monitoring (bi-weekly for sea batches)
                if self._should_perform_health_sampling(batch, current_date):
                    self._perform_health_sampling(batch, current_date)
                    operations_count['observations_made'] += 1

                # Lab sampling (quarterly)
                if self._should_perform_lab_sampling(current_date):
                    self._perform_lab_sampling(batch, current_date)
                    operations_count['lab_samples'] += 1

                # Check for treatment withholding period expiration
                self._check_treatment_withholding_expiration(batch.id, current_date)

            # End expired outbreaks
            self._end_expired_outbreaks(current_date)

            logger.info(f"Daily health operations completed: {operations_count}")
            return operations_count

    def _start_disease_outbreak(self, batch: Batch, disease_name: str, start_date: date):
        """Start a disease outbreak for a batch."""
        try:
            outbreak_info = self.disease_simulator.start_disease_outbreak(batch, disease_name, start_date)

            # Create detailed journal entry for outbreak start
            journal_entry = JournalEntry.objects.create(
                batch=batch,
                entry_date=start_date,
                category='issue',
                severity='high' if outbreak_info['mortality_multiplier'] > 3.0 else 'medium',
                description=f"Disease outbreak detected: {disease_name}. "
                           f"Expected duration: {outbreak_info['duration_days']} days. "
                           f"Mortality impact: {outbreak_info['mortality_multiplier']}x normal rate. "
                           f"Symptoms: {', '.join(outbreak_info['primary_symptoms'])}",
                user=self.system_user
            )

            logger.info(f"Started {disease_name} outbreak for batch {batch.batch_number}")

        except Exception as e:
            logger.error(f"Error starting disease outbreak: {e}")

    def _apply_disease_treatment(self, batch: Batch, outbreak: Dict, current_date: date) -> bool:
        """Apply appropriate treatment for an active disease outbreak."""
        try:
            disease_name = outbreak['disease_name']
            profile = DISEASE_PROFILES[disease_name]

            # Find best treatment option
            best_treatment = None
            best_effectiveness = 0.0

            for treatment_type, treatment_info in profile.treatment_options.items():
                if treatment_info['mortality_reduction'] > best_effectiveness:
                    best_treatment = treatment_type
                    best_effectiveness = treatment_info['mortality_reduction']

            if not best_treatment:
                return False

            # Check if treatment is already active for this batch
            if batch.id in self.active_treatments:
                active_end_date = self.active_treatments[batch.id]
                if current_date <= active_end_date:
                    return False  # Treatment still active

            # Apply treatment
            success = self.disease_simulator.apply_treatment(batch.id, best_treatment)
            if not success:
                return False

            treatment_info = profile.treatment_options[best_treatment]
            treatment_end_date = current_date + timedelta(days=treatment_info['duration_days'])
            withholding_end_date = current_date + timedelta(days=treatment_info['withholding_period'])

            # Create treatment record
            Treatment.objects.create(
                batch=batch,
                treatment_type=best_treatment.upper().replace('_', ' '),
                start_date=current_date,
                end_date=treatment_end_date,
                withholding_period_end_date=withholding_end_date,
                reason=f"Treatment for {disease_name} outbreak",
                effectiveness=best_effectiveness,
                cost_per_kg_biomass=Decimal(str(treatment_info['cost_per_kg_biomass'])),
                notes=f"Applied {best_treatment} for {disease_name}. "
                      f"Expected effectiveness: {best_effectiveness:.1%}",
                administered_by=self.system_user
            )

            # Track active treatment
            self.active_treatments[batch.id] = withholding_end_date

            # Update outbreak info
            outbreak['treatment_applied'] = True
            outbreak['treatment_type'] = best_treatment
            outbreak['treatment_effectiveness'] = best_effectiveness

            logger.info(f"Applied {best_treatment} treatment to batch {batch.batch_number} for {disease_name}")

            return True

        except Exception as e:
            logger.error(f"Error applying disease treatment: {e}")
            return False

    def _create_health_observation(self, batch: Batch, outbreak: Dict, observation_date: date):
        """Create a health observation record for disease monitoring."""
        try:
            disease_name = outbreak['disease_name']
            profile = DISEASE_PROFILES[disease_name]

            # Generate realistic observation data
            observation_data = {
                'weight_g': random.uniform(50, 5000),  # Depends on stage
                'length_cm': random.uniform(10, 120),   # Depends on stage
                'k_factor': round(random.uniform(1.0, 2.5), 2),
                'condition_score': random.randint(1, 5),
                'appetite_score': random.randint(1, 5) if random.random() < 0.3 else None,
                'ventilation_rate': random.randint(30, 120) if random.random() < 0.2 else None,
                'skin_condition': random.choice(['normal', 'pale', 'hemorrhagic', 'ulcerated']),
                'gill_condition': random.choice(['normal', 'pale', 'hyperplastic', 'mucus_production']),
                'fin_condition': random.choice(['normal', 'eroded', 'split', 'missing'])
            }

            # Add disease-specific observations
            if disease_name in ['PD', 'ISA']:
                observation_data['heart_condition'] = 'enlarged' if random.random() < 0.7 else 'normal'
            if disease_name == 'AGD':
                observation_data['mucus_production'] = 'excessive' if random.random() < 0.8 else 'normal'

            # Create a health sampling event for disease monitoring
            HealthSamplingEvent.objects.create(
                assignment=batch.batchcontainerassignment_set.first(),  # Get first assignment
                sampling_date=observation_date,
                number_of_fish_sampled=10,  # Sample size for monitoring
                avg_weight_g=Decimal(str(observation_data['weight_g'])),
                avg_length_cm=Decimal(str(observation_data['length_cm'])),
                avg_k_factor=Decimal(str(observation_data['k_factor'])),
                notes=f"Monitoring {disease_name} outbreak. Symptoms: {', '.join(profile.primary_symptoms)}",
                sampled_by=self.system_user
            )

        except Exception as e:
            logger.error(f"Error creating health observation: {e}")

    def _create_journal_entry(self, batch: Batch, outbreak: Dict, entry_date: date):
        """Create a veterinary journal entry for significant health events."""
        try:
            disease_name = outbreak['disease_name']
            profile = DISEASE_PROFILES[disease_name]

            severity = 'high' if profile.mortality_multiplier > 3.0 else 'medium'

            JournalEntry.objects.create(
                batch=batch,
                entry_date=entry_date,
                category='diagnosis',
                severity=severity,
                description=f"Veterinary examination for {disease_name} outbreak. "
                           f"Disease: {profile.full_name}. "
                           f"Symptoms observed: {', '.join(profile.primary_symptoms)}. "
                           f"Mortality impact: {profile.mortality_multiplier}x normal rate. "
                           f"Recommended actions: Monitor closely and apply appropriate treatment protocols.",
                user=self.system_user
            )

        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")

    def _should_perform_health_sampling(self, batch: Batch, current_date: date) -> bool:
        """Determine if health sampling should be performed for this batch on this date."""
        # Bi-weekly sampling for sea batches
        if hasattr(batch, 'lifecycle_stage') and batch.lifecycle_stage:
            stage_name = batch.lifecycle_stage.name.lower()
            if 'grow' in stage_name or 'post' in stage_name:
                # Every 14 days
                days_since_start = (current_date - batch.start_date).days
                return days_since_start % 14 == 0
        return False

    def _perform_health_sampling(self, batch: Batch, sampling_date: date):
        """Perform routine health sampling for a batch."""
        try:
            # Generate lice count for sea batches
            lice_count = None
            if hasattr(batch, 'lifecycle_stage') and batch.lifecycle_stage:
                stage_name = batch.lifecycle_stage.name.lower()
                if 'grow' in stage_name or 'post' in stage_name:
                    # Seasonal lice pressure
                    month = sampling_date.month
                    if month in [5, 6, 7, 8, 9, 10]:  # Summer months
                        lice_count = round(random.uniform(0.1, 2.0), 2)  # Higher pressure
                    else:
                        lice_count = round(random.uniform(0.0, 0.8), 2)  # Lower pressure

            # Create health sampling event
            HealthSamplingEvent.objects.create(
                assignment=batch.batchcontainerassignment_set.first(),  # Get first assignment
                sampling_date=sampling_date,
                number_of_fish_sampled=random.randint(10, 30),
                avg_weight_g=Decimal(str(random.uniform(100, 4000))),
                notes=f"Routine health sampling. Sample size: {random.randint(10, 30)} fish. "
                      f"Lice count: {lice_count} adult females per fish." if lice_count else
                      f"Routine health sampling. Sample size: {random.randint(10, 30)} fish.",
                sampled_by=self.system_user
            )

            # Check if treatment threshold exceeded
            if lice_count and lice_count > HEALTH_THRESHOLDS['lice_count_threshold']:
                self._trigger_lice_treatment(batch, sampling_date, lice_count)

        except Exception as e:
            logger.error(f"Error performing health sampling: {e}")

    def _trigger_lice_treatment(self, batch: Batch, detection_date: date, lice_count: float):
        """Trigger lice treatment when threshold is exceeded."""
        try:
            # Choose treatment method based on season and batch stage
            treatment_type = self._select_lice_treatment_method(batch, detection_date)

            treatment_info = TREATMENT_PROTOCOLS[treatment_type]
            treatment_end_date = detection_date + timedelta(days=treatment_info['duration_days'])
            withholding_end_date = detection_date + timedelta(days=treatment_info['withholding_period_days'])

            Treatment.objects.create(
                batch=batch,
                treatment_type=treatment_type.upper().replace('_', ' '),
                start_date=detection_date,
                end_date=treatment_end_date,
                withholding_period_end_date=withholding_end_date,
                reason=f"Lice treatment triggered by count of {lice_count} adult females per fish",
                effectiveness=0.7,  # Typical effectiveness
                cost_per_kg_biomass=Decimal(str(treatment_info['cost_per_kg'])),
                notes=f"Automatic lice treatment due to high lice count. Method: {treatment_type}",
                administered_by=self.system_user
            )

            # Track active treatment
            self.active_treatments[batch.id] = withholding_end_date

            logger.info(f"Triggered {treatment_type} treatment for batch {batch.batch_number} due to high lice count")

        except Exception as e:
            logger.error(f"Error triggering lice treatment: {e}")

    def _select_lice_treatment_method(self, batch: Batch, treatment_date: date) -> str:
        """Select appropriate lice treatment method."""
        month = treatment_date.month

        # Prefer mechanical treatments in summer when possible
        if month in [6, 7, 8]:  # Summer months
            return 'freshwater_bath' if random.random() < 0.6 else 'mechanical_delicing'

        # Use chemical treatments in other seasons
        return 'antibiotic_bath' if random.random() < 0.5 else 'thermal_treatment'

    def _should_perform_lab_sampling(self, current_date: date) -> bool:
        """Determine if lab sampling should be performed on this date."""
        # Quarterly sampling (every 90 days)
        day_of_year = current_date.timetuple().tm_yday
        return day_of_year % 90 == 0

    def _perform_lab_sampling(self, batch: Batch, sampling_date: date):
        """Perform lab sampling for a batch."""
        try:
            sample_types = ['blood', 'gill', 'tissue', 'fecal', 'water']
            sample_type = random.choice(sample_types)

            # Generate realistic lab results
            results = {
                'blood': {
                    'hematocrit': f"{random.randint(25, 45)}%",
                    'hemoglobin': f"{random.uniform(8.0, 15.0):.1f} g/dL",
                    'wbc_count': f"{random.randint(20, 80)} × 10³/μL"
                },
                'gill': {
                    'pathology': random.choice(['normal', 'hyperplasia', 'mucus', 'parasites']),
                    'bacterial_load': f"{random.randint(1000, 100000)} CFU/g"
                },
                'tissue': {
                    'histopathology': random.choice(['normal', 'inflammation', 'necrosis', 'fibrosis']),
                    'viral_pcr': random.choice(['negative', 'positive', 'inconclusive'])
                },
                'fecal': {
                    'parasite_eggs': random.choice(['none', 'low', 'moderate', 'high']),
                    'digestibility': f"{random.randint(70, 95)}%"
                },
                'water': {
                    'bacterial_count': f"{random.randint(100, 10000)} CFU/mL",
                    'ph_level': f"{random.uniform(6.5, 8.5):.1f}"
                }
            }

            # Determine if abnormal findings
            is_abnormal = random.random() < 0.15  # 15% chance of abnormal results

            HealthLabSample.objects.create(
                batch_container_assignment=batch.batchcontainerassignment_set.first(),  # Get first assignment
                sample_type=SampleType.objects.get_or_create(name=sample_type.upper())[0],
                sample_date=sampling_date,
                findings_summary=str(results[sample_type]),
                quantitative_results=results[sample_type],
                notes=f"Quarterly {sample_type} sampling. "
                      f"Results: {results[sample_type]}",
                recorded_by=self.system_user
            )

        except Exception as e:
            logger.error(f"Error performing lab sampling: {e}")

    def _check_treatment_withholding_expiration(self, batch_id: int, current_date: date):
        """Check if any treatment withholding periods have expired."""
        if batch_id in self.active_treatments:
            if current_date > self.active_treatments[batch_id]:
                del self.active_treatments[batch_id]
                logger.debug(f"Treatment withholding period expired for batch {batch_id}")

    def _end_expired_outbreaks(self, current_date: date):
        """End disease outbreaks that have reached their natural conclusion."""
        for batch_id, outbreak in list(self.disease_simulator.active_outbreaks.items()):
            if current_date >= outbreak['end_date']:
                self.disease_simulator.end_disease_outbreak(batch_id, current_date)

                # Create closure journal entry
                try:
                    batch = Batch.objects.get(id=batch_id)
                    JournalEntry.objects.create(
                        batch=batch,
                        entry_date=current_date,
                        category='observation',
                        severity='low',
                        description=f"Disease outbreak resolved: {outbreak['disease_name']}. "
                                   f"Duration: {outbreak['duration_days']} days. "
                                   f"Treatment applied: {outbreak.get('treatment_type', 'None')}. "
                                   f"Outcome: {'Successful' if outbreak.get('treatment_effectiveness', 0) > 0.3 else 'Requires monitoring'}",
                        user=self.system_user
                    )
                except Exception as e:
                    logger.error(f"Error creating disease resolution entry: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the disease generator."""
        return {
            'active_outbreaks': len(self.disease_simulator.active_outbreaks),
            'total_outbreaks_simulated': len(self.disease_simulator.outbreak_history),
            'active_treatments': len(self.active_treatments),
            'diseases_simulated': list(DISEASE_PROFILES.keys()),
            'journal_entries_created': JournalEntry.objects.filter(category__in=['issue', 'diagnosis']).count(),
            'health_samplings_created': HealthSamplingEvent.objects.count(),
            'lab_samples_created': HealthLabSample.objects.count()
        }
