"""
Health Manager Module

This module handles health data generation including journal entries, health sampling events,
lab samples, lice counts, and treatments for the AquaMind test data generation system.
"""
import random
import logging
import traceback
import json
from datetime import datetime, date, timedelta, time
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta

from apps.batch.models import Batch, BatchContainerAssignment
from apps.health.models import (
    JournalEntry, HealthParameter, HealthSamplingEvent, IndividualFishObservation,
    FishParameterScore, HealthLabSample, SampleType, Treatment, VaccinationType,
    MortalityReason, MortalityRecord, LiceCount
)
from apps.users.models import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('health_manager')

class HealthManager:
    """Manages health data generation for batches."""
    
    # Constants for health data generation
    SEVERITY_LEVELS = [1, 2, 3, 4, 5]  # 1 = minor, 5 = severe
    LICE_SPECIES = ["Lepeophtheirus salmonis", "Caligus elongatus"]
    LICE_STAGES = ["Chalimus", "Pre-adult", "Adult female", "Adult male"]
    LAB_SAMPLE_TYPES = ["Blood", "Tissue", "Gill", "Fecal", "Water"]
    
    # Treatment types and methods
    TREATMENT_TYPES = {
        "lice": [
            "Freshwater Bath", 
            "Chemical Bath - Hydrogen Peroxide",
            "Chemical Bath - Azamethiphos",
            "Chemical Bath - Deltamethrin",
            "Thermal Treatment",
            "Mechanical Removal",
            "In-Feed - Emamectin Benzoate"
        ],
        "vaccination": [
            "IPN Vaccination",
            "BKD Vaccination",
            "Furunculosis Vaccination",
            "ISA Vaccination"
        ],
        "antibiotic": [
            "Florfenicol",
            "Oxytetracycline",
            "Sulfadiazine-trimethoprim"
        ],
        "antifungal": [
            "Formalin Bath",
            "Salt Bath"
        ]
    }
    
    def __init__(self):
        """Initialize the health manager."""
        logger.info("Initializing HealthManager")
        try:
            # Get or create required parameters
            self.health_parameters = self._get_or_create_health_parameters()
            self.sample_types = self._get_or_create_sample_types()
            self.vaccination_types = self._get_or_create_vaccination_types()
            self.mortality_reasons = self._get_or_create_mortality_reasons()
            
            # Get users for attribution
            self.users = list(User.objects.all())
            if not self.users:
                # Create a default user if none exists
                User.objects.create_user(username="health_system", email="health@example.com", password="password")
                self.users = list(User.objects.all())
            
            logger.info(f"HealthManager initialized with {len(self.health_parameters)} health parameters")
        except Exception as e:
            logger.error(f"Error initializing HealthManager: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _get_or_create_health_parameters(self):
        """Get or create health parameters for assessments."""
        parameters = [
            {
                "name": "Gill Condition",
                "scores": [
                    "Gills bright red, no mucus (Excellent)",
                    "Minor pale areas, minimal mucus (Good)",
                    "Pale areas with some mucus (Fair)",
                    "Widespread pale/white areas, excess mucus (Poor)",
                    "Severe necrosis/hemorrhage (Critical)",
                ],
            },
            {
                "name": "Fin Condition",
                "scores": [
                    "All fins intact (Excellent)",
                    "Minor nicks on fins (Good)",
                    "Noticeable fraying on one fin (Fair)",
                    "Multiple fins frayed/eroded (Poor)",
                    "Severe fin loss/ulcers (Critical)",
                ],
            },
            {
                "name": "Skin Condition",
                "scores": [
                    "Scales intact & bright (Excellent)",
                    "Isolated missing scales (Good)",
                    "Patchy scale loss / mild lesions (Fair)",
                    "Large lesions or hemorrhage (Poor)",
                    "Extensive ulceration / fungal growth (Critical)",
                ],
            },
            {
                "name": "Eye Condition",
                "scores": [
                    "Clear & bright eyes (Excellent)",
                    "Slight cloudiness (Good)",
                    "Moderate cloudiness / mild exophthalmia (Fair)",
                    "Severe cloudiness / marked exophthalmia (Poor)",
                    "Eye rupture / loss (Critical)",
                ],
            },
            {
                "name": "Swimming Behavior",
                "scores": [
                    "Schooling strongly, even distribution (Excellent)",
                    "Minor surface activity (Good)",
                    "Uneven distribution, some slow fish (Fair)",
                    "Lethargic / grouping in corners (Poor)",
                    "Moribund / spiral swimming (Critical)",
                ],
            },
            {
                "name": "Appetite",
                "scores": [
                    "Feed consumed immediately (Excellent)",
                    "Minor feed residue (Good)",
                    "Noticeable feed left after 10 min (Fair)",
                    "Half ration uneaten (Poor)",
                    "No feeding response (Critical)",
                ],
            },
            {
                "name": "Respiration Rate",
                "scores": [
                    "Normal opercular beats (Excellent)",
                    "Slightly elevated beats (Good)",
                    "Moderately elevated beats (Fair)",
                    "Rapid opercular movement (Poor)",
                    "Surface gasping (Critical)",
                ],
            },
            {
                "name": "Parasite Load",
                "scores": [
                    "No visible parasites (Excellent)",
                    "1–5 parasites per fish (Good)",
                    "6–10 parasites per fish (Fair)",
                    "11–20 parasites per fish (Poor)",
                    ">20 parasites per fish (Critical)",
                ],
            },
        ]
        
        result = []
        for param in parameters:
            obj, created = HealthParameter.objects.get_or_create(
                name=param["name"],
                defaults={
                    "description_score_1": param["scores"][0],
                    "description_score_2": param["scores"][1],
                    "description_score_3": param["scores"][2],
                    "description_score_4": param["scores"][3],
                    "description_score_5": param["scores"][4],
                }
            )
            result.append(obj)
            if created:
                logger.info(f"Created health parameter: {obj.name}")
        
        return result
    
    def _get_or_create_sample_types(self):
        """Get or create sample types for lab samples."""
        types = [
            {"name": "Blood", "description": "Blood sample for hematology and biochemistry"},
            {"name": "Gill", "description": "Gill tissue sample for pathogen detection"},
            {"name": "Tissue", "description": "Tissue sample for histopathology"},
            {"name": "Fecal", "description": "Fecal sample for parasite detection"},
            {"name": "Water", "description": "Water sample for environmental analysis"}
        ]
        
        result = []
        for type_info in types:
            obj, created = SampleType.objects.get_or_create(
                name=type_info["name"],
                defaults={"description": type_info["description"]}
            )
            result.append(obj)
            if created:
                logger.info(f"Created sample type: {obj.name}")
        
        return result
    
    def _get_or_create_vaccination_types(self):
        """Get or create vaccination types."""
        types = [
            {"name": "IPN Vaccine", "description": "Infectious Pancreatic Necrosis vaccine"},
            {"name": "BKD Vaccine", "description": "Bacterial Kidney Disease vaccine"},
            {"name": "Furunculosis Vaccine", "description": "Furunculosis (Aeromonas) vaccine"},
            {"name": "ISA Vaccine", "description": "Infectious Salmon Anemia vaccine"},
            {"name": "Vibriosis Vaccine", "description": "Vibriosis vaccine"}
        ]
        
        result = []
        for type_info in types:
            obj, created = VaccinationType.objects.get_or_create(
                name=type_info["name"],
                defaults={"description": type_info["description"]}
            )
            result.append(obj)
            if created:
                logger.info(f"Created vaccination type: {obj.name}")
        
        return result
    
    def _get_or_create_mortality_reasons(self):
        """Get or create mortality reasons."""
        reasons = [
            {"name": "Disease", "description": "Mortality due to disease"},
            {"name": "Predation", "description": "Mortality due to predators"},
            {"name": "Handling", "description": "Mortality due to handling stress"},
            {"name": "Environmental", "description": "Mortality due to environmental conditions"},
            {"name": "Unknown", "description": "Mortality with unknown cause"}
        ]
        
        result = []
        for reason_info in reasons:
            obj, created = MortalityReason.objects.get_or_create(
                name=reason_info["name"],
                defaults={"description": reason_info["description"]}
            )
            result.append(obj)
            if created:
                logger.info(f"Created mortality reason: {obj.name}")
        
        return result
    
    def generate_health_data(self, batch, start_date, end_date, batch_assignments=None):
        """Generate comprehensive health data for a batch over a time period.
        
        Args:
            batch: The batch to generate health data for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating health data for batch {batch.id} from {start_date} to {end_date}")
        
        try:
            # If batch_assignments not provided, fetch them
            if batch_assignments is None:
                batch_assignments = list(BatchContainerAssignment.objects.filter(
                    batch=batch,
                    assignment_date__lte=end_date,
                    departure_date__gte=start_date
                ).order_by('assignment_date'))
            
            if not batch_assignments:
                logger.warning(f"No batch assignments found for batch {batch.id} in the specified period")
                return
            
            # Generate weekly health journal entries
            self._generate_journal_entries(batch, start_date, end_date, batch_assignments)
            
            # Generate monthly health sampling events
            self._generate_health_sampling_events(batch, start_date, end_date, batch_assignments)
            
            # Generate bi-weekly lice counts for sea stages
            self._generate_lice_counts(batch, start_date, end_date, batch_assignments)
            
            # Generate lab samples (less frequent)
            self._generate_lab_samples(batch, start_date, end_date, batch_assignments)
            
            # Generate treatments based on lifecycle stage and health issues
            self._generate_treatments(batch, start_date, end_date, batch_assignments)
            
            logger.info(f"Completed health data generation for batch {batch.id}")
        except Exception as e:
            logger.error(f"Error generating health data for batch {batch.id}: {str(e)}")
            logger.error(traceback.format_exc())
    
    def generate_current_health(self, start_date: date, end_date: date):
        """Generate current health status records for active batches."""
        active_batches = Batch.objects.filter(status='ACTIVE')
        records = 0
        for batch in active_batches:
            assignments = list(BatchContainerAssignment.objects.filter(batch=batch, is_active=True))
            if assignments:
                self.generate_health_data(batch, start_date, end_date, assignments)
                records += 1
        logger.info(f"Generated health data for {records} active batches")
        return records
    
    def _generate_journal_entries(self, batch, start_date, end_date, batch_assignments):
        """Generate weekly journal entries for a batch.
        
        Args:
            batch: The batch to generate entries for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating journal entries for batch {batch.id}")
        
        # Generate weekly entries
        current_date = start_date
        while current_date <= end_date:
            # Find the active assignment for this date
            assignment = next((a for a in batch_assignments if a.assignment_date <= current_date and 
                              (a.departure_date is None or a.departure_date >= current_date)), None)
            
            if assignment:
                # Determine if this is a regular entry or an issue-based entry
                is_issue = random.random() < 0.2  # 20% chance of reporting an issue
                
                severity = None
                if is_issue:
                    severity_level = random.choice([1, 2, 3])  # Minor to moderate issues
                    if random.random() < 0.1:  # 10% chance of severe issue
                        severity_level = random.choice([4, 5])

                    # Map numeric severity to string values expected by model
                    severity_map = {1: 'low', 2: 'medium', 3: 'medium', 4: 'high', 5: 'high'}
                    severity = severity_map.get(severity_level, 'low')
                
                entry_text = self._generate_journal_entry_text(batch, assignment, is_issue, severity)
                
                # Create the journal entry
                category = 'issue' if is_issue else 'observation'
                JournalEntry.objects.create(
                    batch=batch,
                    container=assignment.container,
                    user=random.choice(self.users),
                    entry_date=timezone.make_aware(datetime.combine(current_date, time(random.randint(8,17), random.randint(0,59)))),
                    category=category,
                    description=entry_text,  # Changed from entry_text to description
                    severity=severity,
                )
                
                logger.debug(f"Created journal entry for batch {batch.id} on {current_date}")
            
            # Move to next week (with some randomness in the exact day)
            days_to_add = 7 + random.randint(-1, 1)
            current_date += timedelta(days=days_to_add)
    
    def _generate_entry_tags(self, is_issue, severity):
        """Generate appropriate tags for a journal entry."""
        tags = ["routine"]
        
        if is_issue:
            tags = ["issue"]
            if severity and severity == 'high':
                tags.append("urgent")
            
            # Add specific issue tags
            issue_tags = ["health", "behavior", "environment", "feeding"]
            tags.append(random.choice(issue_tags))
        
        return ",".join(tags)
    
    def _generate_journal_entry_text(self, batch, assignment, is_issue, severity):
        """Generate realistic journal entry text."""
        lifecycle_stage = assignment.lifecycle_stage.name if assignment.lifecycle_stage else "Unknown"
        container_name = assignment.container.name if assignment.container else "Unknown"
        
        if not is_issue:
            templates = [
                f"Routine health check for {batch.batch_number} in {container_name}. Fish appear healthy and active.",
                f"Weekly inspection of {batch.batch_number}. Normal behavior observed. Good appetite.",
                f"Regular monitoring of {lifecycle_stage} stage fish. No health concerns noted.",
                f"Batch {batch.batch_number} showing good coloration and swimming patterns. Feeding well.",
                f"Routine observation of {container_name}. Fish responding well to feeding. No abnormalities."
            ]
            return random.choice(templates)
        
        # Issue-based entries
        if severity and severity in ['high', 'medium']:
            templates = [
                f"URGENT: Abnormal mortality observed in {container_name}. Immediate investigation required.",
                f"ALERT: Multiple fish in {batch.batch_number} showing severe lethargy and loss of appetite.",
                f"CRITICAL: Unusual swimming behavior and surface gasping in {container_name}. Oxygen levels checked.",
                f"HIGH PRIORITY: Significant gill irritation observed across population. Treatment evaluation needed.",
                f"URGENT ACTION: Potential disease outbreak in {batch.batch_number}. Samples collected for testing."
            ]
        else:
            templates = [
                f"Minor fin erosion observed in some individuals in {container_name}. Will monitor closely.",
                f"Slight increase in scale loss noted in {batch.batch_number}. Environmental parameters checked.",
                f"Some fish showing reduced appetite in {container_name}. Feed consumption being monitored.",
                f"Few individuals displaying abnormal swimming patterns. Will continue observation.",
                f"Minor skin discoloration observed in small percentage of population. No other symptoms noted."
            ]
        
        return random.choice(templates)
    
    def _generate_health_sampling_events(self, batch, start_date, end_date, batch_assignments):
        """Generate monthly health sampling events with individual fish observations.
        
        Args:
            batch: The batch to generate sampling events for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating health sampling events for batch {batch.id}")
        
        # Generate monthly sampling events
        current_date = start_date
        while current_date <= end_date:
            # Find the active assignment for this date
            assignment = next((a for a in batch_assignments if a.assignment_date <= current_date and 
                              (a.departure_date is None or a.departure_date >= current_date)), None)
            
            if assignment:
                # Create the sampling event
                with transaction.atomic():
                    # Determine sample size (typically 10-30 fish)
                    sample_size = random.randint(10, 30)
                    
                    # Calculate average metrics based on lifecycle stage
                    avg_weight = assignment.avg_weight_g or 100  # Default if None
                    avg_length = self._estimate_length_from_weight(avg_weight)
                    
                    # Add some variance
                    avg_weight = avg_weight * random.uniform(0.95, 1.05)
                    avg_length = avg_length * random.uniform(0.95, 1.05)
                    
                    # Calculate K factor (condition factor)
                    avg_k_factor = (avg_weight / (avg_length ** 3)) * 100
                    
                    # Create sampling event
                    sampling_event = HealthSamplingEvent.objects.create(
                        assignment=assignment,
                        sampling_date=current_date,
                        sampled_by=random.choice(self.users),
                        number_of_fish_sampled=sample_size,
                        calculated_sample_size=sample_size,
                        avg_weight_g=avg_weight,
                        avg_length_cm=avg_length,
                        avg_k_factor=avg_k_factor,
                        notes=f"Monthly health sampling for {batch.batch_number}"
                    )
                    
                    # Generate individual fish observations
                    self._generate_individual_observations(sampling_event, sample_size)
                    
                    logger.debug(f"Created health sampling event for batch {batch.id} on {current_date}")
            
            # Move to next month (with some randomness in the exact day)
            days_to_add = 30 + random.randint(-3, 3)
            current_date += timedelta(days=days_to_add)
    
    def _estimate_length_from_weight(self, weight_g):
        """Estimate fish length based on weight using a simplified formula."""
        # Simplified formula: length (cm) ≈ cube root of (weight (g) / factor)
        # Factor varies by species and condition, using 0.01 as an approximation
        return round((weight_g / 0.01) ** (1/3), 1)
    
    def _generate_individual_observations(self, sampling_event, sample_size):
        """Generate individual fish observations for a sampling event."""
        for i in range(sample_size):
            # Create individual fish observation
            fish_obs = IndividualFishObservation.objects.create(
                sampling_event=sampling_event,
                fish_identifier=f"FISH_{i + 1:03d}",
                weight_g=sampling_event.avg_weight_g * random.uniform(0.8, 1.2) if sampling_event.avg_weight_g else None,
                length_cm=sampling_event.avg_length_cm * random.uniform(0.9, 1.1) if sampling_event.avg_length_cm else None
            )
            
            # Add parameter scores for this fish
            for param in self.health_parameters:
                # Score from 1-5, with most being good (4-5)
                if random.random() < 0.8:  # 80% chance of good score
                    score = random.randint(4, 5)
                else:
                    score = random.randint(1, 3)

                FishParameterScore.objects.create(
                    individual_fish_observation=fish_obs,
                    parameter=param,
                    score=score
                )
    
    def _generate_individual_fish_notes(self):
        """Generate notes for individual fish observations."""
        templates = [
            "Fish appears healthy with good coloration",
            "Normal swimming behavior observed",
            "No visible external parasites",
            "Good fin condition with minimal erosion",
            "Clear eyes, no cloudiness",
            "Minor scale loss on dorsal area",
            "Slight fin erosion on caudal fin",
            "Small lesion on left side",
            "Slightly pale gills",
            ""  # Empty notes sometimes
        ]
        return random.choice(templates)
    
    def _generate_parameter_score_notes(self, parameter, score):
        """Generate notes for parameter scores based on the parameter and score."""
        if score >= 4:
            good_notes = {
                "Gill Condition": "Gills bright red with good lamellae structure",
                "Fin Condition": "Fins intact with no erosion",
                "Skin Condition": "Skin healthy with good scale coverage",
                "Eye Condition": "Eyes clear and bright",
                "Swimming Behavior": "Normal swimming patterns observed",
                "Appetite": "Good feeding response",
                "Respiration Rate": "Normal respiration rate",
                "Parasite Load": "No visible parasites"
            }
            return good_notes.get(parameter.name, "Good condition")
        else:
            poor_notes = {
                "Gill Condition": "Pale gills with some mucus",
                "Fin Condition": "Some fin erosion present",
                "Skin Condition": "Scale loss and minor lesions",
                "Eye Condition": "Slight cloudiness in eyes",
                "Swimming Behavior": "Erratic swimming observed",
                "Appetite": "Reduced feeding response",
                "Respiration Rate": "Elevated respiration rate",
                "Parasite Load": "Some external parasites visible"
            }
            return poor_notes.get(parameter.name, "Needs attention")
    
    def _generate_lice_counts(self, batch, start_date, end_date, batch_assignments):
        """Generate bi-weekly lice counts for sea stages.
        
        Args:
            batch: The batch to generate lice counts for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating lice counts for batch {batch.id}")
        
        # Only generate lice counts for sea stages (Post-Smolt and Adult)
        sea_assignments = [a for a in batch_assignments if a.lifecycle_stage and 
                          a.lifecycle_stage.name in ["Post-Smolt", "Adult"]]
        
        if not sea_assignments:
            logger.info(f"No sea stage assignments found for batch {batch.id}, skipping lice counts")
            return
        
        # Generate bi-weekly lice counts
        for assignment in sea_assignments:
            current_date = max(start_date, assignment.assignment_date)
            end_assignment = assignment.departure_date or end_date
            end_assignment = min(end_assignment, end_date)
            
            while current_date <= end_assignment:
                # Generate lice count with seasonal variation
                month = current_date.month
                
                # Higher lice counts in summer months (May-September)
                is_summer = 5 <= month <= 9
                
                # Base counts with seasonal adjustment
                base_chalimus = random.uniform(0.5, 2.0) if is_summer else random.uniform(0.1, 0.8)
                base_preadult = random.uniform(0.3, 1.5) if is_summer else random.uniform(0.1, 0.5)
                base_adult_female = random.uniform(0.2, 1.0) if is_summer else random.uniform(0.0, 0.3)
                base_adult_male = random.uniform(0.3, 1.2) if is_summer else random.uniform(0.1, 0.4)
                
                # Add some randomness
                chalimus = max(0, base_chalimus * random.uniform(0.8, 1.2))
                preadult = max(0, base_preadult * random.uniform(0.8, 1.2))
                adult_female = max(0, base_adult_female * random.uniform(0.8, 1.2))
                adult_male = max(0, base_adult_male * random.uniform(0.8, 1.2))
                
                # Create the lice count record
                LiceCount.objects.create(
                    batch=batch,
                    container=assignment.container,
                    count_date=current_date,
                    fish_sampled=random.randint(10, 20),
                    species=random.choice(self.LICE_SPECIES),
                    chalimus_count=chalimus,
                    preadult_count=preadult,
                    adult_female_count=adult_female,
                    adult_male_count=adult_male,
                    notes=self._generate_lice_count_notes(chalimus, preadult, adult_female, adult_male)
                )
                
                logger.debug(f"Created lice count for batch {batch.id} on {current_date}")
                
                # Move to next count (approximately bi-weekly)
                days_to_add = 14 + random.randint(-2, 2)
                current_date += timedelta(days=days_to_add)
    
    def _generate_lice_count_notes(self, chalimus, preadult, adult_female, adult_male):
        """Generate notes for lice counts based on the counts."""
        total = chalimus + preadult + adult_female + adult_male
        
        if adult_female > 0.5:
            return "Adult female lice above threshold. Treatment recommended."
        elif total > 3.0:
            return "High overall lice load. Monitor closely."
        elif total > 1.0:
            return "Moderate lice presence. Continue regular monitoring."
        else:
            return "Low lice counts. No action required."
    
    def _generate_lab_samples(self, batch, start_date, end_date, batch_assignments):
        """Generate occasional lab samples.
        
        Args:
            batch: The batch to generate lab samples for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating lab samples for batch {batch.id}")
        
        # Generate quarterly lab samples
        current_date = start_date
        while current_date <= end_date:
            # Find the active assignment for this date
            assignment = next((a for a in batch_assignments if a.assignment_date <= current_date and 
                              (a.departure_date is None or a.departure_date >= current_date)), None)
            
            if assignment:
                # Determine if this is a routine sample or triggered by an issue
                is_routine = random.random() < 0.7  # 70% routine, 30% issue-based
                
                # Select sample type
                sample_type = random.choice(self.sample_types)
                
                # Generate results based on sample type
                results = self._generate_lab_sample_results(sample_type.name, is_routine)
                
                # Create the lab sample
                HealthLabSample.objects.create(
                    batch_container_assignment=assignment,
                    sample_type=sample_type,
                    sample_date=current_date,
                    lab_reference_id=f"LAB-{batch.batch_number}-{current_date.strftime('%Y%m%d')}",
                    quantitative_results=results,
                    findings_summary=self._generate_lab_sample_notes(sample_type.name, is_routine, results)
                )
                
                logger.debug(f"Created lab sample for batch {batch.id} on {current_date}")
            
            # Move to next quarter (with some randomness)
            days_to_add = 90 + random.randint(-10, 10)
            current_date += timedelta(days=days_to_add)
    
    def _generate_lab_sample_results(self, sample_type, is_routine):
        """Generate realistic lab sample results based on sample type."""
        if sample_type == "Blood":
            return {
                "hematocrit": round(random.uniform(25, 45), 1),
                "hemoglobin": round(random.uniform(7, 12), 1),
                "white_blood_cells": round(random.uniform(1.5, 3.0) * 10000, 0),
                "red_blood_cells": round(random.uniform(0.9, 1.5) * 1000000, 0),
                "glucose": round(random.uniform(3.0, 8.0), 1),
                "total_protein": round(random.uniform(30, 60), 1),
                "abnormal": not is_routine
            }
        elif sample_type == "Gill":
            return {
                "amoebic_gill_disease": random.random() < 0.1,
                "bacterial_gill_disease": random.random() < 0.1,
                "epitheliocystis": random.random() < 0.05,
                "gill_score": random.randint(1, 5),
                "parasite_presence": random.random() < 0.2,
                "abnormal": not is_routine
            }
        elif sample_type == "Tissue":
            return {
                "histopathology": random.choice([
                    "No significant findings",
                    "Mild inflammation",
                    "Moderate inflammation",
                    "Severe inflammation",
                    "Necrosis present",
                    "Granulomas observed"
                ]),
                "pcr_results": random.choice([
                    "Negative for all tested pathogens",
                    "Positive for Aeromonas spp.",
                    "Positive for Flavobacterium spp.",
                    "Positive for Vibrio spp.",
                    "Positive for PRV"
                ]),
                "abnormal": not is_routine
            }
        elif sample_type == "Fecal":
            return {
                "parasites_detected": random.random() < 0.15,
                "parasite_species": random.choice(["None", "Nematodes", "Cestodes", "Trematodes", "Mixed infection"]),
                "bacterial_culture": random.choice(["Normal flora", "Aeromonas spp.", "Vibrio spp.", "Mixed growth"]),
                "abnormal": not is_routine
            }
        else:  # Water
            return {
                "temperature": round(random.uniform(8, 16), 1),
                "dissolved_oxygen": round(random.uniform(7, 12), 1),
                "ph": round(random.uniform(6.8, 8.2), 1),
                "ammonia": round(random.uniform(0, 0.05), 3),
                "nitrite": round(random.uniform(0, 0.1), 3),
                "nitrate": round(random.uniform(0, 25), 1),
                "bacterial_count": round(random.uniform(100, 5000), 0),
                "abnormal": not is_routine
            }
    
    def _generate_lab_sample_notes(self, sample_type, is_routine, results):
        """Generate notes for lab samples based on results."""
        if is_routine:
            return f"Routine {sample_type.lower()} sample. Results within normal parameters."
        
        if results.get("abnormal", False):
            if sample_type == "Blood":
                if results["hematocrit"] < 30:
                    return "Low hematocrit indicates potential anemia. Further investigation recommended."
                else:
                    return "Elevated white blood cell count suggests inflammatory response."
            elif sample_type == "Gill":
                if results.get("amoebic_gill_disease", False):
                    return "Positive for amoebic gill disease. Treatment recommended."
                else:
                    return f"Gill score of {results.get('gill_score', 'N/A')} indicates moderate gill damage."
            elif sample_type == "Tissue":
                if "Positive" in results.get("pcr_results", ""):
                    return f"PCR results: {results.get('pcr_results')}. Treatment protocol to be implemented."
                else:
                    return f"Histopathology: {results.get('histopathology')}. Monitor closely."
            elif sample_type == "Fecal":
                if results.get("parasites_detected", False):
                    return f"Parasites detected: {results.get('parasite_species')}. Deworming treatment recommended."
                else:
                    return "Abnormal bacterial flora detected. Monitor for digestive issues."
            else:  # Water
                if results.get("dissolved_oxygen", 10) < 8:
                    return "Low dissolved oxygen levels. Increase aeration immediately."
                else:
                    return "Water quality parameters outside optimal range. Adjust system accordingly."
        
        return "Sample analysis complete. No significant findings."
    
    def _generate_treatments(self, batch, start_date, end_date, batch_assignments):
        """Generate treatments based on lifecycle stage and health issues.
        
        Args:
            batch: The batch to generate treatments for
            start_date: The start date for data generation
            end_date: The end date for data generation
            batch_assignments: List of batch container assignments
        """
        logger.info(f"Generating treatments for batch {batch.id}")
        
        # Generate vaccinations during freshwater stages
        self._generate_vaccinations(batch, batch_assignments)
        
        # Generate lice treatments based on lice counts
        self._generate_lice_treatments(batch, start_date, end_date, batch_assignments)
        
        # Generate other treatments based on health issues
        self._generate_health_issue_treatments(batch, start_date, end_date, batch_assignments)
    
    def _generate_vaccinations(self, batch, batch_assignments):
        """Generate vaccinations during appropriate lifecycle stages."""
        # Vaccinations typically occur during Parr or Smolt stages
        vaccination_assignments = [a for a in batch_assignments if a.lifecycle_stage and 
                                  a.lifecycle_stage.name in ["Parr", "Smolt"]]
        
        if not vaccination_assignments:
            logger.info(f"No suitable lifecycle stages for vaccination found for batch {batch.id}")
            return
        
        # Select a suitable assignment for vaccination
        assignment = vaccination_assignments[0]  # Use the first suitable assignment
        
        # Calculate vaccination date (typically early in the stage)
        vaccination_date = assignment.assignment_date + timedelta(days=random.randint(7, 21))
        
        # Generate vaccinations for common diseases
        for vacc_type in self.vaccination_types[:4]:  # Limit to 4 vaccination types
            Treatment.objects.create(
                batch=batch,
                container=assignment.container,
                batch_assignment=assignment,
                user=random.choice(self.users),
                treatment_date=vaccination_date,
                treatment_type="vaccination",
                vaccination_type=vacc_type,
                description=f"{vacc_type.name} administered to batch {batch.batch_number}",
                dosage="Standard dose",
                duration_days=0,  # Single administration
                withholding_period_days=0,
                outcome="successful"
            )
            
            logger.debug(f"Created vaccination ({vacc_type.name}) for batch {batch.id} on {vaccination_date}")
            
            # Space out vaccinations by a few days
            vaccination_date += timedelta(days=random.randint(1, 3))
    
    def _generate_lice_treatments(self, batch, start_date, end_date, batch_assignments):
        """Generate lice treatments based on lice counts."""
        # Get all lice counts for this batch
        lice_counts = LiceCount.objects.filter(
            batch=batch,
            count_date__gte=start_date,
            count_date__lte=end_date
        ).order_by('count_date')
        
        if not lice_counts:
            logger.info(f"No lice counts found for batch {batch.id}, skipping lice treatments")
            return
        
        # Track last treatment date to prevent too frequent treatments
        last_treatment_date = None
        
        for lice_count in lice_counts:
            # Check if treatment is needed (adult female count > 0.5 is a common threshold)
            if lice_count.adult_female_count > 0.5:
                # Ensure minimum interval between treatments (at least 14 days)
                if last_treatment_date and (lice_count.count_date - last_treatment_date).days < 14:
                    continue
                
                # Find the active assignment for this date
                assignment = next((a for a in batch_assignments if a.assignment_date <= lice_count.count_date and 
                                  (a.departure_date is None or a.departure_date >= lice_count.count_date)), None)
                
                if not assignment:
                    continue
                
                # Select treatment method based on lice level and random choice
                if lice_count.adult_female_count > 2.0:
                    # High infestation - use more aggressive treatments
                    treatment_options = self.TREATMENT_TYPES["lice"][:4]  # First 4 options are stronger
                else:
                    # Moderate infestation - use any treatment
                    treatment_options = self.TREATMENT_TYPES["lice"]
                
                treatment_method = random.choice(treatment_options)
                
                # Determine treatment duration and withholding period
                if "Bath" in treatment_method:
                    duration_days = 1
                    withholding_period_days = random.randint(3, 7)
                elif "Thermal" in treatment_method or "Mechanical" in treatment_method:
                    duration_days = 1
                    withholding_period_days = 0
                else:  # In-Feed
                    duration_days = 7
                    withholding_period_days = 14
                
                # Create treatment record
                treatment_date = lice_count.count_date + timedelta(days=random.randint(1, 3))
                
                Treatment.objects.create(
                    batch=batch,
                    container=assignment.container,
                    batch_assignment=assignment,
                    user=random.choice(self.users),
                    treatment_date=treatment_date,
                    treatment_type="physical" if "Mechanical" in treatment_method or "Thermal" in treatment_method else "medication",
                    description=f"Lice treatment: {treatment_method}",
                    dosage=self._generate_treatment_dosage(treatment_method),
                    duration_days=duration_days,
                    withholding_period_days=withholding_period_days,
                    outcome=random.choice(["successful", "successful", "partial", "unsuccessful"])
                )
                
                logger.debug(f"Created lice treatment for batch {batch.id} on {treatment_date}")
                
                # Update last treatment date
                last_treatment_date = treatment_date
    
    def _generate_health_issue_treatments(self, batch, start_date, end_date, batch_assignments):
        """Generate treatments based on health issues recorded in journal entries."""
        # Get journal entries with moderate to severe issues (medium/high severity)
        issue_entries = JournalEntry.objects.filter(
            batch=batch,
            entry_date__gte=start_date,
            entry_date__lte=end_date,
            severity__in=['medium', 'high']
        ).order_by('entry_date')
        
        if not issue_entries:
            logger.info(f"No significant health issues found for batch {batch.id}, skipping issue treatments")
            return
        
        # Track last treatment date to prevent too frequent treatments
        last_treatment_date = None
        
        for entry in issue_entries:
            # Ensure minimum interval between treatments (at least 7 days)
            if last_treatment_date and (entry.entry_date - last_treatment_date).days < 7:
                continue
            
            # Determine treatment type based on issue
            if "gill" in entry.description.lower() or "respiratory" in entry.description.lower():
                treatment_type = "medication"
                description = random.choice([
                    "Hydrogen peroxide bath for gill health",
                    "Formalin bath for gill parasites",
                    "Salt bath for gill irritation"
                ])
                duration_days = 1
                withholding_period_days = random.randint(3, 7)
            elif "lesion" in entry.description.lower() or "wound" in entry.description.lower():
                treatment_type = "medication"
                description = random.choice([
                    "Topical antiseptic application",
                    "Salt bath for external parasites",
                    "Potassium permanganate bath"
                ])
                duration_days = 1
                withholding_period_days = random.randint(2, 5)
            elif "appetite" in entry.description.lower() or "feeding" in entry.description.lower():
                treatment_type = "medication"
                description = random.choice([
                    "Medicated feed with appetite stimulant",
                    "Probiotic feed supplement",
                    "Vitamin C supplementation"
                ])
                duration_days = random.randint(3, 7)
                withholding_period_days = 0
            elif "bacteria" in entry.description.lower() or "infection" in entry.description.lower():
                treatment_type = "medication"
                description = random.choice(self.TREATMENT_TYPES["antibiotic"])
                duration_days = random.randint(5, 10)
                withholding_period_days = random.randint(14, 30)
            else:
                treatment_type = "other"
                description = "Supportive care and monitoring"
                duration_days = random.randint(3, 7)
                withholding_period_days = 0
            
            # Create treatment record
            treatment_date = entry.entry_date + timedelta(days=random.randint(0, 2))
            
            Treatment.objects.create(
                batch=batch,
                container=entry.container,
                user=random.choice(self.users),
                treatment_date=treatment_date,
                treatment_type=treatment_type,
                description=description,
                dosage=self._generate_treatment_dosage(description),
                duration_days=duration_days,
                withholding_period_days=withholding_period_days,
                outcome=random.choice(["successful", "successful", "partial", "unsuccessful"])
            )
            
            logger.debug(f"Created health issue treatment for batch {batch.id} on {treatment_date}")
            
            # Update last treatment date
            last_treatment_date = treatment_date
    
    def _generate_treatment_dosage(self, treatment_method):
        """Generate appropriate dosage information based on treatment method."""
        if "Hydrogen Peroxide" in treatment_method:
            return f"{random.randint(1200, 1800)} ppm for {random.randint(15, 25)} minutes"
        elif "Azamethiphos" in treatment_method:
            return f"{random.randint(100, 150)} ppb for {random.randint(30, 60)} minutes"
        elif "Deltamethrin" in treatment_method:
            return f"{random.randint(2, 5)} ppb for {random.randint(30, 40)} minutes"
        elif "Thermal" in treatment_method:
            return f"{random.randint(28, 34)}°C for {random.randint(20, 40)} seconds"
        elif "Mechanical" in treatment_method:
            return "Standard pressure settings"
        elif "Emamectin" in treatment_method:
            return f"{random.randint(50, 100)} μg/kg biomass for {random.randint(7, 10)} days"
        elif "Florfenicol" in treatment_method:
            return f"{random.randint(10, 15)} mg/kg biomass for {random.randint(7, 10)} days"
        elif "Oxytetracycline" in treatment_method:
            return f"{random.randint(75, 100)} mg/kg biomass for {random.randint(7, 14)} days"
        elif "Formalin" in treatment_method:
            return f"{random.randint(150, 250)} ppm for {random.randint(30, 60)} minutes"
        elif "Salt" in treatment_method:
            return f"{random.randint(10, 30)} ppt for {random.randint(30, 60)} minutes"
        else:
            return "Standard dose as per protocol"
