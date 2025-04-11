import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.batch.models import Batch, LifeCycleStage, Species, BatchContainerAssignment
from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.infrastructure.models import Container, ContainerType, Area, Geography
from apps.inventory.models import Feed, FeedRecommendation
from apps.inventory.services.feed_recommendation_service import FeedRecommendationService


class FeedRecommendationServiceTest(TestCase):
    def setUp(self):
        """Set up data for each test method."""
        # Basic Infrastructure
        self.geography = Geography.objects.create(name="Testland")
        self.area = Area.objects.create(
            name="Test Area",
            latitude=60.0,
            longitude=5.0,
            geography=self.geography,
            max_biomass=10000.00
        )
        self.container_type = ContainerType.objects.create(
            name="Test Tank Type",
            description="Test Type Desc",
            category='TANK',
            max_volume_m3=100.00
        )
        self.container = Container.objects.create(
            name="Test Tank 01",
            container_type=self.container_type,
            area=self.area,
            volume_m3=80.00,
            max_biomass_kg=5000.00,
            active=True,
            feed_recommendations_enabled=True # Explicitly enable recommendations
        )

        # Species and Lifecycle Stages
        self.species = Species.objects.create(name="Test Salmon", scientific_name="Salmo testar")
        self.stage_egg = LifeCycleStage.objects.create(name="Egg & Alevin", order=0, species=self.species)
        self.stage_fry = LifeCycleStage.objects.create(name="Fry", order=1, species=self.species)
        self.stage_parr = LifeCycleStage.objects.create(name="Parr", order=2, species=self.species)
        self.stage_smolt = LifeCycleStage.objects.create(name="Smolt", order=3, species=self.species)
        self.stage_post_smolt = LifeCycleStage.objects.create(name="Post-Smolt", order=4, species=self.species)
        self.stage_adult = LifeCycleStage.objects.create(name="Adult", order=5, species=self.species)

        # Feeds (using correct field names and corrected size categories)
        self.feed_fry = Feed.objects.create(
            name="Fry Feed Alpha",
            brand="TestFeed Inc.",
            size_category="MICRO",          # Corrected: Fry -> MICRO
            protein_percentage=Decimal("55.0"), 
            fat_percentage=Decimal("15.0"),
            is_active=True  # Explicitly set active
        )
        self.feed_parr = Feed.objects.create(
            name="Parr Pellets Beta",
            brand="AquaGrow Feeds",
            size_category="SMALL",         # Corrected: Parr -> SMALL
            protein_percentage=Decimal("45.0"), 
            fat_percentage=Decimal("20.0"),
            is_active=True  # Explicitly set active
        )
        self.feed_smolt = Feed.objects.create(
            name="Smolt Chow Gamma",
            brand="TestFeed Inc.",
            size_category="MEDIUM",          # Corrected: Smolt/Post-Smolt -> MEDIUM
            protein_percentage=Decimal("40.0"), 
            fat_percentage=Decimal("25.0"),
            is_active=True  # Explicitly set active
        )
        # Add an Adult feed
        self.feed_adult = Feed.objects.create(
            name="Adult Grower Delta",
            brand="AquaGrow Feeds",
            size_category="LARGE",         # Corrected: Adult -> LARGE
            protein_percentage=Decimal("38.0"), 
            fat_percentage=Decimal("28.0"),
            is_active=True  # Explicitly set active
        )

        # Batch and Assignment (using correct field names)
        today = timezone.now().date()
        self.batch = Batch.objects.create(
            batch_number="Test Batch 001",    # Renamed from name
            species=self.species,
            lifecycle_stage=self.stage_smolt,  # Renamed from current_lifecycle_stage
            start_date=today - datetime.timedelta(days=100),
            population_count=1000,            # Renamed from initial_population
            avg_weight_g=Decimal("1000.0")    # Added avg_weight_g
        )
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_smolt,
            assignment_date=today - datetime.timedelta(days=5),
            population_count=1000,
            biomass_kg=Decimal("1000.00"),
            is_active=True # Make sure it's active
        )
        
        # Environmental Parameters and Reading
        self.param_temp = EnvironmentalParameter.objects.create(name="Water Temperature", unit="C")
        self.param_do = EnvironmentalParameter.objects.create(name="Dissolved Oxygen", unit="mg/L")
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=timezone.now() - datetime.timedelta(hours=2), value=Decimal("14.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_do, reading_time=timezone.now() - datetime.timedelta(hours=2), value=Decimal("8.0"))

    def test_get_temperature_efficiency(self):
        """Test temperature efficiency calculation for different ranges."""
        service = FeedRecommendationService
        # Cold
        self.assertEqual(service.get_temperature_efficiency(Decimal("5.0")), Decimal("0.5"))
        # Cool
        self.assertEqual(service.get_temperature_efficiency(Decimal("10.0")), Decimal("0.7"))
        # Optimal
        self.assertEqual(service.get_temperature_efficiency(Decimal("15.0")), Decimal("1.0"))
        # Warm
        self.assertEqual(service.get_temperature_efficiency(Decimal("20.0")), Decimal("0.8"))
        # Hot
        self.assertEqual(service.get_temperature_efficiency(Decimal("25.0")), Decimal("0.6"))
        # Boundary Checks
        self.assertEqual(service.get_temperature_efficiency(Decimal("8.0")), Decimal("0.7")) # Upper boundary of cold, should be cool
        self.assertEqual(service.get_temperature_efficiency(Decimal("12.0")), Decimal("1.0")) # Upper boundary of cool, should be optimal
        self.assertEqual(service.get_temperature_efficiency(Decimal("18.0")), Decimal("0.8")) # Upper boundary of optimal, should be warm
        self.assertEqual(service.get_temperature_efficiency(Decimal("22.0")), Decimal("0.6")) # Upper boundary of warm, should be hot
        # Null check
        self.assertEqual(service.get_temperature_efficiency(None), Decimal("0.8")) # Default

    def test_get_oxygen_efficiency(self):
        """Test dissolved oxygen efficiency calculation for different ranges."""
        service = FeedRecommendationService
        # Critical
        self.assertEqual(service.get_oxygen_efficiency(Decimal("3.0")), Decimal("0.3"))
        # Poor
        self.assertEqual(service.get_oxygen_efficiency(Decimal("5.0")), Decimal("0.6"))
        # Adequate
        self.assertEqual(service.get_oxygen_efficiency(Decimal("7.0")), Decimal("0.9"))
        # Optimal
        self.assertEqual(service.get_oxygen_efficiency(Decimal("10.0")), Decimal("1.0"))
        # Super Saturated
        self.assertEqual(service.get_oxygen_efficiency(Decimal("15.0")), Decimal("0.8"))
        # Boundary Checks
        self.assertEqual(service.get_oxygen_efficiency(Decimal("4.0")), Decimal("0.6")) # Upper boundary of critical, should be poor
        self.assertEqual(service.get_oxygen_efficiency(Decimal("6.0")), Decimal("0.9")) # Upper boundary of poor, should be adequate
        self.assertEqual(service.get_oxygen_efficiency(Decimal("8.0")), Decimal("1.0")) # Upper boundary of adequate, should be optimal
        self.assertEqual(service.get_oxygen_efficiency(Decimal("12.0")), Decimal("0.8")) # Upper boundary of optimal, should be super_saturated
        # Null check
        self.assertEqual(service.get_oxygen_efficiency(None), Decimal("0.8")) # Default

    def test_get_recommended_feed_type(self):
        """Test that the correct feed type is recommended based on lifecycle stage."""
        service = FeedRecommendationService

        # Test Fry stage -> MICRO
        recommended_feed_fry = service.get_recommended_feed_type(self.stage_fry)
        self.assertEqual(recommended_feed_fry, self.feed_fry)

        # Test Parr stage -> SMALL
        recommended_feed_parr = service.get_recommended_feed_type(self.stage_parr)
        self.assertEqual(recommended_feed_parr, self.feed_parr)

        # Test Smolt stage -> MEDIUM
        recommended_feed_smolt = service.get_recommended_feed_type(self.stage_smolt)
        self.assertEqual(recommended_feed_smolt, self.feed_smolt)

        # Test Post-Smolt stage -> MEDIUM
        recommended_feed_post_smolt = service.get_recommended_feed_type(self.stage_post_smolt)
        self.assertEqual(recommended_feed_post_smolt, self.feed_smolt, "Post-Smolt should use MEDIUM feed") # Corrected assertion

        # Test Adult stage -> LARGE
        recommended_feed_adult = service.get_recommended_feed_type(self.stage_adult)
        self.assertEqual(recommended_feed_adult, self.feed_adult, "Adult should use LARGE feed") # Corrected assertion

        # Test with a stage that has no mapping in the service (e.g., Egg & Alevin)
        recommended_feed_egg = service.get_recommended_feed_type(self.stage_egg)
        self.assertIsNone(recommended_feed_egg, "Should return None for stages with no feed size mapping")

        # Test with a stage that has no suitable feed (dummy stage with no mapping)
        dummy_stage = LifeCycleStage.objects.create(name="Dummy Stage", order=99, species=self.species)
        recommended_feed_dummy = service.get_recommended_feed_type(dummy_stage)
        self.assertIsNone(recommended_feed_dummy, "Should return None if stage name is not in the service map")

    def test_get_recent_environmental_readings(self):
        """Test retrieval of recent average environmental readings."""
        service = FeedRecommendationService
        now = timezone.now()
        hours_lookback = 24
        cutoff_time = now - datetime.timedelta(hours=hours_lookback)

        # Readings within lookback period for the test container
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=now - datetime.timedelta(hours=1), value=Decimal("14.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=now - datetime.timedelta(hours=5), value=Decimal("16.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_do, reading_time=now - datetime.timedelta(hours=2), value=Decimal("9.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_do, reading_time=now - datetime.timedelta(hours=10), value=Decimal("10.0"))

        # Reading outside lookback period
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=now - datetime.timedelta(hours=hours_lookback + 1), value=Decimal("10.0"))

        # Reading for a different container (should be ignored)
        other_container = Container.objects.create(name="Other Tank", container_type=self.container_type, area=self.area, volume_m3=50, max_biomass_kg=2000, active=True)
        EnvironmentalReading.objects.create(container=other_container, parameter=self.param_temp, reading_time=now - datetime.timedelta(hours=1), value=Decimal("20.0"))

        # Call the service method
        recent_readings = service.get_recent_environmental_readings(self.assignment, hours_lookback=hours_lookback)

        # Assertions
        self.assertIsNotNone(recent_readings)
        # Average temp = (14 from setUp + 16 + 14) / 3 = 14.666...
        self.assertAlmostEqual(recent_readings["water_temperature_c"], Decimal("14.6666666666666667"), places=2)
        # Average DO = (8 from setUp + 9 + 10) / 3 = 9.0
        self.assertAlmostEqual(recent_readings["dissolved_oxygen_mg_l"], Decimal("9.0"), places=2)

        # Test default lookback (currently 24h in service, matches above)
        recent_readings_default = service.get_recent_environmental_readings(self.assignment)
        self.assertAlmostEqual(recent_readings_default["water_temperature_c"], Decimal("14.6666666666666667"), places=2)

        # Test case with no recent readings
        EnvironmentalReading.objects.filter(container=self.container, reading_time__gte=cutoff_time).delete()
        no_recent_readings = service.get_recent_environmental_readings(self.assignment, hours_lookback=hours_lookback)
        self.assertEqual(no_recent_readings, {'water_temperature_c': None, 'dissolved_oxygen_mg_l': None}, "Should return dict with None values if no recent readings found")

    def test_calculate_feed_recommendation_normal(self):
        """Test feed recommendation calculation under normal conditions."""
        service = FeedRecommendationService
        now = timezone.now()

        # Setup specific environmental conditions for predictable results
        # Optimal Temp (15C -> 1.0 eff), Adequate DO (7 mg/L -> 0.9 eff)
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=now - datetime.timedelta(hours=1), value=Decimal("15.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_do, reading_time=now - datetime.timedelta(hours=1), value=Decimal("7.0"))

        # Expected base percentage for Smolt: 2.0%
        expected_base_percent = service.BASE_FEEDING_PERCENTAGES.get(self.stage_smolt.name)
        self.assertEqual(expected_base_percent, Decimal('2.0'))

        # Calculate recommendation
        result = service.calculate_feed_recommendation(self.assignment)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['feed'], self.feed_smolt) # Smolt feed
        # Check environmental data used: Avg(14 from setUp, 15 from test) = 14.5
        self.assertAlmostEqual(result['water_temperature_c'], Decimal('14.5'), places=2)
        # Check environmental data used: Avg(8 from setUp, 7 from test) = 7.5
        self.assertAlmostEqual(result['dissolved_oxygen_mg_l'], Decimal('7.5'), places=2)
        # These efficiency values are internal to the service, but we check them indirectly via the adjusted percentage
        # self.assertEqual(result['temperature_efficiency'], Decimal('1.0')) # Optimal temp
        # self.assertEqual(result['oxygen_efficiency'], Decimal('0.9'))     # Adequate DO

        # Adjusted% = Base% * CombinedEfficiency = 2.0% * min(1.0, 0.9) = 2.0% * 0.9 = 1.8%
        expected_adjusted_percent = expected_base_percent * min(Decimal('1.0'), Decimal('0.9'))
        # Assert the calculated adjusted percentage matches expected
        self.assertAlmostEqual(result['feeding_percentage'], expected_adjusted_percent, places=4)

        # Total Feed = Biomass * Adjusted% = 1000kg * 1.8% = 18 kg
        expected_total_feed = self.assignment.biomass_kg * (expected_adjusted_percent / Decimal('100'))
        expected_total_feed_quantized = expected_total_feed.quantize(Decimal('0.001'))
        self.assertAlmostEqual(result['recommended_feed_kg'], expected_total_feed_quantized, places=3)

        # Feedings per day for Smolt = 4
        expected_feedings = service.FEEDINGS_PER_DAY.get(self.stage_smolt.name)
        self.assertEqual(result['feedings_per_day'], expected_feedings)

    def test_calculate_feed_recommendation_egg_stage(self):
        """Test calculation for Egg & Alevin stage (should be zero)."""
        service = FeedRecommendationService
        egg_stage = self.stage_egg
        # Update assignment to egg stage
        self.assignment.lifecycle_stage = egg_stage
        self.assignment.save()

        result = service.calculate_feed_recommendation(self.assignment)

        # Assertions - should use default efficiencies (0.8 for both Temp and DO)
        self.assertIsNotNone(result)
        self.assertIsNone(result['feed'], "No feed type should be recommended for Egg stage")
        self.assertEqual(result['feeding_percentage'], Decimal('0'))
        self.assertEqual(result['recommended_feed_kg'], Decimal('0.00'))
        self.assertEqual(result['feedings_per_day'], 0)

    def test_calculate_feed_recommendation_no_environmental(self):
        """Test calculation when no recent environmental readings are found."""
        service = FeedRecommendationService
        # Delete existing readings for the test setup's container
        EnvironmentalReading.objects.filter(container=self.container).delete()

        # Calculate recommendation
        result = service.calculate_feed_recommendation(self.assignment)

        # Assertions - should use default efficiencies (assume 0.8 for temp, 0.8 for DO from service logic if None)
        self.assertIsNotNone(result)
        self.assertEqual(result['feed'], self.feed_smolt)
        self.assertIsNone(result['water_temperature_c'])
        self.assertIsNone(result['dissolved_oxygen_mg_l'])

        # Calculate expected based on defaults
        expected_base_percent = service.BASE_FEEDING_PERCENTAGES.get(self.stage_smolt.name)
        # Assume default efficiencies are 0.8 (based on get_temperature_efficiency/get_oxygen_efficiency handling None)
        default_temp_eff = Decimal('0.8')
        default_oxygen_eff = Decimal('0.8')
        expected_combined_efficiency = min(default_temp_eff, default_oxygen_eff)
        expected_adjusted_percent = expected_base_percent * expected_combined_efficiency

        # Check adjusted percentage
        self.assertAlmostEqual(result['feeding_percentage'], expected_adjusted_percent, places=4)

        # Total Feed = Biomass * Adjusted% = 1000kg * 1.6% = 16 kg
        expected_total_feed = self.assignment.biomass_kg * (expected_adjusted_percent / Decimal('100'))
        expected_total_feed_quantized = expected_total_feed.quantize(Decimal('0.001'))
        self.assertAlmostEqual(result['recommended_feed_kg'], expected_total_feed_quantized, places=3)

        # Feedings per day for Smolt = 4
        expected_feedings = service.FEEDINGS_PER_DAY.get(self.stage_smolt.name)
        self.assertEqual(result['feedings_per_day'], expected_feedings)

    def test_calculate_feed_recommendation_zero_biomass(self):
        """Test calculation when the assignment has zero biomass."""
        service = FeedRecommendationService
        # Deactivate the existing assignment to avoid IntegrityError
        self.assignment.is_active = False
        self.assignment.save()

        # Create a new assignment with zero biomass
        zero_biomass_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_smolt,
            assignment_date=timezone.now().date() - datetime.timedelta(days=1),
            population_count=0,
            biomass_kg=Decimal("0.00"), # Zero biomass
            is_active=True
        )

        result = service.calculate_feed_recommendation(zero_biomass_assignment)

        # Assertions - Feed amount should be zero, but feed type is still determined
        self.assertIsNotNone(result)
        self.assertEqual(result['feed'], self.feed_smolt)
        self.assertEqual(result['recommended_feed_kg'], Decimal('0.00'))
        # The adjusted feeding percentage itself might be non-zero, calculated based on stage/env before biomass.
        # self.assertEqual(result['feeding_percentage'], Decimal('0')) 
        self.assertEqual(result['feedings_per_day'], service.FEEDINGS_PER_DAY.get(self.stage_smolt.name))

    def test_create_recommendation_for_assignment(self):
        """Test creating a single FeedRecommendation object for an assignment."""
        service = FeedRecommendationService
        today = timezone.now().date()

        # Ensure no pre-existing recommendation for this assignment and date
        FeedRecommendation.objects.filter(
            batch_container_assignment=self.assignment, # Revert to object filter
            recommended_date=today # Correct field name
        ).delete()

        # Use the correct method name 'create_recommendation'
        recommendation, created = service.create_recommendation(self.assignment, target_date=today)

        # Check the return values
        self.assertTrue(created, "Recommendation should have been created")
        self.assertIsInstance(recommendation, FeedRecommendation, "Should return a FeedRecommendation object")

        # Verify the object properties
        self.assertEqual(recommendation.batch_container_assignment, self.assignment)
        self.assertEqual(recommendation.recommended_date, today)
        self.assertEqual(recommendation.feed, self.feed_smolt)
        self.assertGreater(recommendation.recommended_feed_kg, 0)
        self.assertIsNotNone(recommendation.recommendation_reason)

        # Test idempotency: calling again should not create a new one
        recommendation_again, created_again = service.create_recommendation(self.assignment, target_date=today)
        self.assertFalse(created_again, "Recommendation should not be created again")
        self.assertEqual(recommendation_again, recommendation, "Should return the existing recommendation")

    def test_create_recommendations_for_container(self):
        """Test creating recommendations for all active assignments in a container."""
        service = FeedRecommendationService
        today = timezone.now().date()

        # Set up predictable env conditions
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=timezone.now() - datetime.timedelta(hours=1), value=Decimal("14.0"))
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_do, reading_time=timezone.now() - datetime.timedelta(hours=1), value=Decimal("7.0"))

        # Create another active assignment in the same container
        batch2 = Batch.objects.create(
            batch_number="Test Batch 002", 
            species=self.species, 
            lifecycle_stage=self.stage_parr, # Corrected field
            start_date=today - datetime.timedelta(days=50), 
            population_count=500,           # Corrected field
            avg_weight_g=Decimal("50.0")    # Corrected field
        )
        assignment2 = BatchContainerAssignment.objects.create(
            batch=batch2,
            container=self.container,
            lifecycle_stage=self.stage_parr,
            assignment_date=today - datetime.timedelta(days=2),
            population_count=3000,
            biomass_kg=Decimal("300.00"),
            is_active=True
        )

        # Create an inactive assignment in the same container
        batch3 = Batch.objects.create(
            batch_number="Test Batch 003", 
            species=self.species, 
            lifecycle_stage=self.stage_smolt, # Corrected field name
            start_date=today - datetime.timedelta(days=110),
            population_count=100,           # Added population_count
            avg_weight_g=Decimal("150.0")   # Added avg_weight_g
        )
        assignment_inactive = BatchContainerAssignment.objects.create(
            batch=batch3,
            container=self.container, # Can be any container
            lifecycle_stage=self.stage_smolt,
            assignment_date=today - datetime.timedelta(days=3),
            population_count=1000,
            biomass_kg=Decimal("150.00"),
            is_active=False # Inactive
        )

        # Create an active assignment in a different container
        other_container = Container.objects.create(name="Other Tank", container_type=self.container_type, area=self.area, volume_m3=50, max_biomass_kg=2000, active=True)
        batch4 = Batch.objects.create(
            batch_number="Test Batch 004", # Corrected field
            species=self.species, 
            lifecycle_stage=self.stage_smolt, # Corrected field name
            start_date=today - datetime.timedelta(days=120),
            population_count=200,           # Added population_count
            avg_weight_g=Decimal("90.0")    # Added avg_weight_g
        )
        assignment_other_container = BatchContainerAssignment.objects.create(
            batch=batch4,
            container=other_container,
            lifecycle_stage=self.stage_smolt,
            assignment_date=today - datetime.timedelta(days=4),
            population_count=4000,
            biomass_kg=Decimal("800.00"),
            is_active=True
        )

        # Initial call - should create 2 recommendations (for self.assignment and assignment2)
        created_recommendations = service.create_recommendations_for_container(self.container.id, target_date=today)
        self.assertEqual(len(created_recommendations), 2, "Should create recommendations only for active assignments in the target container")

        # Verify the recommendations exist in DB
        recs = FeedRecommendation.objects.filter(recommended_date=today)
        self.assertEqual(recs.count(), 2)
        assignment_pks = {rec.batch_container_assignment.pk for rec in recs}
        self.assertIn(self.assignment.pk, assignment_pks)
        self.assertIn(assignment2.pk, assignment_pks)
        self.assertNotIn(assignment_inactive.pk, assignment_pks)
        self.assertNotIn(assignment_other_container.pk, assignment_pks)

        # Verify specific values for the second assignment (Parr stage)
        rec2 = recs.get(batch_container_assignment=assignment2)
        self.assertEqual(rec2.feed, self.feed_parr) # Parr feed
        base_percent_parr = service.BASE_FEEDING_PERCENTAGES.get(self.stage_parr.name)
        adjusted_percent_parr = base_percent_parr * Decimal('1.0') * Decimal('0.9') # Same env eff
        total_feed_parr = assignment2.biomass_kg * (adjusted_percent_parr / Decimal('100'))
        feedings_parr = service.FEEDINGS_PER_DAY.get(self.stage_parr.name)
        feed_per_feeding_parr = rec2.recommended_feed_kg / rec2.feedings_per_day
        self.assertAlmostEqual(rec2.recommended_feed_kg, total_feed_parr, places=4)
        self.assertAlmostEqual(feed_per_feeding_parr, total_feed_parr / Decimal(feedings_parr), places=4)
        self.assertEqual(rec2.feedings_per_day, feedings_parr)

        # Call again for the same date - should create 0 new recommendations
        created_recommendations_duplicate = service.create_recommendations_for_container(self.container.id, target_date=today)
        self.assertEqual(len(created_recommendations_duplicate), 0, "Should not create duplicate recommendations")
        self.assertEqual(FeedRecommendation.objects.filter(recommended_date=today).count(), 2)

        # Test with no target date (should default to today)
        # Delete existing recs for today to test creation
        recs.delete()
        created_recommendations_today = service.create_recommendations_for_container(self.container.id)
        self.assertEqual(len(created_recommendations_today), 2)
        self.assertEqual(FeedRecommendation.objects.filter(recommended_date=today).count(), 2)

    def test_generate_all_recommendations(self):
        """Test generating recommendations for ALL active assignments system-wide."""
        service = FeedRecommendationService
        today = timezone.now().date()

        # Env conditions (can be minimal as calculation is tested elsewhere)
        EnvironmentalReading.objects.create(container=self.container, parameter=self.param_temp, reading_time=timezone.now() - datetime.timedelta(hours=1), value=Decimal("15.0"))

        # Get the active assignments expected to be processed
        active_assignments = BatchContainerAssignment.objects.filter(
            is_active=True, 
            container__feed_recommendations_enabled=True
        )
        num_active = active_assignments.count()
        self.assertEqual(num_active, 1, "Test setup should have 1 active assignment in recommendation-enabled containers")

        # Initial call - should create recommendations for the provided active assignments
        created_count = service.generate_all_recommendations(
            target_date=today, 
            assignments=active_assignments # Pass the explicit list
        )
        self.assertEqual(created_count, num_active, f"Should create {num_active} recommendations for all active assignments")

        # Verify DB count
        recs = FeedRecommendation.objects.filter(recommended_date=today)
        self.assertEqual(recs.count(), num_active)
        assignment_pks = {rec.batch_container_assignment.pk for rec in recs}
        self.assertIn(self.assignment.pk, assignment_pks)

        # Call again for the same date - should create 0 new recommendations
        # Re-fetch assignments as their state might not be perfectly reflected otherwise in tests
        active_assignments_again = BatchContainerAssignment.objects.filter(
            is_active=True, 
            container__feed_recommendations_enabled=True
        )
        created_count_duplicate = service.generate_all_recommendations(
            target_date=today, 
            assignments=active_assignments_again
        )
        self.assertEqual(created_count_duplicate, 0, "Should not create duplicate recommendations")
        self.assertEqual(FeedRecommendation.objects.filter(recommended_date=today).count(), num_active)

        # Test with no target date (should default to today)
        # Delete existing recs for today to test creation
        recs.delete()
        # Re-fetch assignments
        active_assignments_today = BatchContainerAssignment.objects.filter(
            is_active=True, 
            container__feed_recommendations_enabled=True
        )
        created_count_today = service.generate_all_recommendations(assignments=active_assignments_today)
        self.assertEqual(created_count_today, num_active)
        self.assertEqual(FeedRecommendation.objects.filter(recommended_date=today).count(), num_active)
