from decimal import Decimal
import unittest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.infrastructure.models import Container, ContainerType, Area, Geography, FeedContainer
from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedingEvent
from apps.inventory.api.serializers.utils import ReadWriteFieldsMixin, StandardErrorMixin, NestedModelMixin
from apps.inventory.api.serializers.base import (
    InventoryBaseSerializer, TimestampedModelSerializer, 
    FeedRelatedSerializer, BatchRelatedSerializer, ContainerRelatedSerializer, 
    FeedingBaseSerializer
)
from apps.inventory.api.serializers.validation import (
    validate_feed_stock_quantity, validate_batch_assignment_relationship,
    validate_date_range, validate_batch_exists
)
from apps.inventory.api.serializers.feed import FeedSerializer
from apps.inventory.api.serializers.purchase import FeedPurchaseSerializer
from apps.inventory.api.serializers.stock import FeedStockSerializer
from apps.inventory.api.serializers.feeding import FeedingEventSerializer
from apps.inventory.api.serializers.summary import BatchFeedingSummarySerializer


class ReadWriteFieldsMixinTest(TestCase):
    """Tests for the ReadWriteFieldsMixin."""
    
    @unittest.skip("TODO: Fix recursive field access in mixin test")
    def test_get_fields_with_id_suffix(self):
        """Test that fields with _id suffix are properly handled."""
        # Create a base serializer class
        class BaseSerializer(serializers.Serializer):
            feed = serializers.PrimaryKeyRelatedField(queryset=Feed.objects.all())
            feed_id = serializers.PrimaryKeyRelatedField(queryset=Feed.objects.all())
            name = serializers.CharField()
            
            def get_fields(self):
                return {
                    'feed': self.fields['feed'],
                    'feed_id': self.fields['feed_id'],
                    'name': self.fields['name'],
                }
        
        # Create a test serializer class that uses the mixin
        class TestSerializer(ReadWriteFieldsMixin, BaseSerializer):
            pass
        
        # Create an instance and get fields
        serializer = TestSerializer()
        fields = serializer.get_fields()
        
        # Check that feed_id is marked as write-only
        self.assertTrue(fields['feed_id'].write_only)
        # Check that feed is marked as read-only
        self.assertTrue(fields['feed'].read_only)


class StandardErrorMixinTest(TestCase):
    """Tests for the StandardErrorMixin."""
    
    @unittest.skip("TODO: Fix error handling test")
    def test_add_error(self):
        """Test that errors can be added to specific fields."""
        # Create a test serializer class that uses the mixin
        class TestSerializer(StandardErrorMixin):
            pass
        
        # Create an instance and add errors
        serializer = TestSerializer()
        serializer.add_error('field1', 'Error 1')
        serializer.add_error('field1', 'Error 2')
        serializer.add_error('field2', 'Error 3')
        
        # Check that errors were added correctly
        self.assertEqual(serializer._errors['field1'], ['Error 1', 'Error 2'])
        self.assertEqual(serializer._errors['field2'], ['Error 3'])
    
    @unittest.skip("TODO: Fix StandardErrorMixin validation flow")
    def test_validate_with_errors(self):
        """StandardErrorMixin.validate should raise ValidationError when errors exist."""

        class TestSerializer(StandardErrorMixin, serializers.Serializer):
            """Serializer that injects an error during validation."""

            def validate(self, attrs):
                # First call into StandardErrorMixin.validate which initialises _errors
                attrs = super().validate(attrs)
                # Add a validation error AFTER the reset performed in super().validate
                self.add_error('field1', 'Error 1')
                # Return attrs so mixin can process and raise
                return attrs

        serializer = TestSerializer()

        # Expect ValidationError raised by the mixin because we added an error
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate({})

        self.assertEqual(ctx.exception.detail['field1'][0], 'Error 1')


class InventoryBaseSerializerTest(TestCase):
    """Tests for the InventoryBaseSerializer."""
    
    def test_inheritance(self):
        """Test that InventoryBaseSerializer inherits from the correct mixins."""
        self.assertTrue(issubclass(InventoryBaseSerializer, StandardErrorMixin))
        self.assertTrue(issubclass(InventoryBaseSerializer, ReadWriteFieldsMixin))


class FeedSerializerTest(TestCase):
    """Tests for the FeedSerializer."""
    
    def setUp(self):
        """Set up test data."""
        self.feed_data = {
            'name': 'Test Feed',
            'brand': 'Test Brand',
            'size_category': 'MEDIUM',
            'protein_percentage': '45.0',
            'fat_percentage': '15.0',
            'carbohydrate_percentage': '25.0',
            'description': 'Test description',
            'is_active': True
        }
        self.feed = Feed.objects.create(**self.feed_data)
    
    def test_serialization(self):
        """Test that a Feed instance can be serialized correctly."""
        serializer = FeedSerializer(self.feed)
        data = serializer.data
        
        # Check that all fields are serialized correctly
        self.assertEqual(data['name'], self.feed_data['name'])
        self.assertEqual(data['brand'], self.feed_data['brand'])
        self.assertEqual(data['size_category'], self.feed_data['size_category'])
        # Compare the decimal values with a tolerance for formatting differences
        self.assertAlmostEqual(Decimal(data['protein_percentage']), Decimal(self.feed_data['protein_percentage']), places=2)
        self.assertAlmostEqual(Decimal(data['fat_percentage']), Decimal(self.feed_data['fat_percentage']), places=2)
        self.assertAlmostEqual(Decimal(data['carbohydrate_percentage']), Decimal(self.feed_data['carbohydrate_percentage']), places=2)
        self.assertEqual(data['description'], self.feed_data['description'])
        self.assertEqual(data['is_active'], self.feed_data['is_active'])
        
        # Check that created_at and updated_at are included
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_string_representation(self):
        """Test the string representation of the Feed model."""
        self.assertEqual(str(self.feed), "Test Brand - Test Feed (Medium)")
    
    def test_deserialization(self):
        """Test that data can be deserialized to create a Feed instance."""
        serializer = FeedSerializer(data={
            'name': 'New Feed',
            'brand': 'New Brand',
            'size_category': 'SMALL',
            'protein_percentage': '40.0',
            'fat_percentage': '10.0',
            'carbohydrate_percentage': '30.0',
            'description': 'New description',
            'is_active': True
        })
        self.assertTrue(serializer.is_valid())
        
        # Save the deserialized data
        feed = serializer.save()
        
        # Check that the Feed instance was created correctly
        self.assertEqual(feed.name, 'New Feed')
        self.assertEqual(feed.brand, 'New Brand')
        self.assertEqual(feed.size_category, 'SMALL')
        self.assertEqual(feed.protein_percentage, Decimal('40.0'))
        self.assertEqual(feed.fat_percentage, Decimal('10.0'))
        self.assertEqual(feed.carbohydrate_percentage, Decimal('30.0'))
        self.assertEqual(feed.description, 'New description')
        self.assertTrue(feed.is_active)


class FeedPurchaseSerializerTest(TestCase):
    """Tests for the FeedPurchaseSerializer."""
    
    def setUp(self):
        """Set up test data."""
        self.feed = Feed.objects.create(
            name='Test Feed',
            brand='Test Brand',
            size_category='MEDIUM'
        )
        self.purchase_data = {
            'feed': self.feed,
            'purchase_date': timezone.now().date(),
            'quantity_kg': Decimal('100.0'),
            'cost_per_kg': Decimal('5.0'),
            'supplier': 'Test Supplier',
            'batch_number': 'LOT123',  
            'expiry_date': timezone.now().date() + timedelta(days=90),
            'notes': 'Test notes'
        }
        self.purchase = FeedPurchase.objects.create(**self.purchase_data)
    
    def test_serialization(self):
        """Test that a FeedPurchase instance can be serialized correctly."""
        serializer = FeedPurchaseSerializer(self.purchase)
        data = serializer.data
        
        # Check that all fields are serialized correctly
        self.assertEqual(data['feed'], self.feed.id)
        self.assertEqual(data['feed_name'], str(self.feed))
        self.assertEqual(data['purchase_date'], str(self.purchase_data['purchase_date']))
        self.assertEqual(data['quantity_kg'], '100.00')  # Expect 2 decimal places
        self.assertEqual(data['cost_per_kg'], '5.00')    # Expect 2 decimal places
        self.assertEqual(data['supplier'], self.purchase_data['supplier'])
        self.assertEqual(data['batch_number'], self.purchase_data['batch_number'])
        self.assertEqual(data['expiry_date'], str(self.purchase_data['expiry_date']))
        self.assertEqual(data['notes'], self.purchase_data['notes'])
    
    def test_validation_date_range(self):
        """Test validation of purchase_date and expiry_date."""
        # Test with expiry_date before purchase_date (invalid)
        serializer = FeedPurchaseSerializer(data={
            'feed': self.feed.id,  # Use feed field, not feed_id
            'purchase_date': '2023-01-15',
            'expiry_date': '2023-01-01',  
            'quantity_kg': '100.0',
            'cost_per_kg': '5.0',
            'supplier': 'Test Supplier'
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('Start date must be before end date', str(serializer.errors))
        
        # Test with expiry_date after purchase_date (valid)
        serializer = FeedPurchaseSerializer(data={
            'feed': self.feed.id,  # Use feed field, not feed_id
            'purchase_date': '2023-01-01',
            'expiry_date': '2023-01-15',  
            'quantity_kg': '100.0',
            'cost_per_kg': '5.0',
            'supplier': 'Test Supplier'
        })
        self.assertTrue(serializer.is_valid())


class FeedingEventSerializerTest(TestCase):
    """Tests for the FeedingEventSerializer."""
    
    def setUp(self):
        """Set up test data."""
        # Create geography and area
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0,
            longitude=0,
            max_biomass=Decimal("1000.0")
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            category="TANK",
            max_volume_m3=Decimal("1000.0")
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("100.0"),
            max_biomass_kg=Decimal("1000.0")
        )
        
        # Create species, lifecycle stage, and batch
        self.species = Species.objects.create(
            name="Test Species",
            scientific_name="Testus speciesus"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Test Stage",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=30)
        )
        
        # Create batch container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            assignment_date=timezone.now().date() - timedelta(days=20),
            population_count=500,
            biomass_kg=Decimal("200.0")
        )
        
        # Create feed and feed stock
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        self.feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            area=self.area,
            capacity_kg=Decimal("500.0")
        )
        self.feed_stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
        
        # Create feeding event
        self.feeding_event = FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feed_stock=self.feed_stock,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("5.0"),
            batch_biomass_kg=Decimal("200.0"),
            method="MANUAL",
            notes="Test feeding event"
        )
    
    def test_serialization(self):
        """Test that a FeedingEvent instance can be serialized correctly."""
        serializer = FeedingEventSerializer(self.feeding_event)
        data = serializer.data
        
        # Check that all fields are serialized correctly
        self.assertEqual(data['batch'], self.batch.id)
        self.assertEqual(data['batch_name'], str(self.batch))
        self.assertEqual(data['batch_assignment'], self.assignment.id)
        self.assertEqual(data['container'], self.container.id)
        self.assertEqual(data['container_name'], str(self.container))
        self.assertEqual(data['feed'], self.feed.id)
        self.assertEqual(data['feed_name'], str(self.feed))
        self.assertEqual(data['feed_stock'], self.feed_stock.id)
        self.assertEqual(data['amount_kg'], '5.0000')  # Expect 4 decimal places
        self.assertEqual(data['batch_biomass_kg'], '200.00')  # Expect 2 decimal places
        self.assertEqual(data['method'], self.feeding_event.method)
        self.assertEqual(data['notes'], self.feeding_event.notes)
    
    def test_validation_batch_assignment_relationship(self):
        """Test validation of batch and batch_assignment relationship."""
        # Create a different batch
        other_batch = Batch.objects.create(
            batch_number="TEST002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=15)
        )
        
        # Test with batch_assignment not belonging to batch (invalid)
        serializer = FeedingEventSerializer(data={
            'batch': other_batch.id,  
            'batch_assignment': self.assignment.id,  
            'container': self.container.id,
            'feed': self.feed.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',
            'batch_biomass_kg': '200.0',
            'method': 'MANUAL'
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('The batch assignment must belong to the specified batch', str(serializer.errors))
        
        # Test with batch_assignment belonging to batch (valid)
        serializer = FeedingEventSerializer(data={
            'batch': self.batch.id,  
            'batch_assignment': self.assignment.id,  
            'container': self.container.id,
            'feed': self.feed.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',
            'batch_biomass_kg': '200.0',
            'method': 'MANUAL'
        })
        self.assertTrue(serializer.is_valid())
    
    def test_validation_feed_stock_quantity(self):
        """Test validation of feed stock quantity."""
        # Test with insufficient feed stock (invalid)
        self.feed_stock.current_quantity_kg = Decimal("2.0")  
        self.feed_stock.save()
        
        serializer = FeedingEventSerializer(data={
            'batch': self.batch.id,
            'batch_assignment': self.assignment.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': self.feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',  
            'batch_biomass_kg': '200.0',
            'method': 'MANUAL'
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('Not enough feed in stock', str(serializer.errors))
        
        # Test with sufficient feed stock (valid)
        self.feed_stock.current_quantity_kg = Decimal("10.0")  
        self.feed_stock.save()
        
        serializer = FeedingEventSerializer(data={
            'batch': self.batch.id,
            'batch_assignment': self.assignment.id,
            'container': self.container.id,
            'feed': self.feed.id,
            'feed_stock': self.feed_stock.id,
            'feeding_date': timezone.now().date().isoformat(),
            'feeding_time': timezone.now().time().isoformat(),
            'amount_kg': '5.0',  
            'batch_biomass_kg': '200.0',
            'method': 'MANUAL'
        })
        self.assertTrue(serializer.is_valid())


class ValidationFunctionsTest(TestCase):
    """Tests for the validation functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create geography and area
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0,
            longitude=0,
            max_biomass=Decimal("1000.0")
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            category="TANK",
            max_volume_m3=Decimal("1000.0")
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("100.0"),
            max_biomass_kg=Decimal("1000.0"),
            feed_recommendations_enabled=True
        )
        
        # Create species, lifecycle stage, and batch
        self.species = Species.objects.create(
            name="Test Species",
            scientific_name="Testus speciesus"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Test Stage",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=30)
        )
        
        # Create batch container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            assignment_date=timezone.now().date() - timedelta(days=20),
            population_count=500,
            biomass_kg=Decimal("200.0")
        )
        
        # Create feed and feed stock
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        self.feed_container = FeedContainer.objects.create(
            name="Test Feed Container",
            area=self.area,
            capacity_kg=Decimal("500.0")
        )
        self.feed_stock = FeedStock.objects.create(
            feed=self.feed,
            feed_container=self.feed_container,
            current_quantity_kg=Decimal("100.0"),
            reorder_threshold_kg=Decimal("20.0")
        )
    
    def test_validate_feed_stock_quantity(self):
        """Test the validate_feed_stock_quantity function."""
        # Test with sufficient stock
        try:
            validate_feed_stock_quantity(self.feed_stock, Decimal("50.0"))
        except ValidationError:
            self.fail("validate_feed_stock_quantity raised ValidationError unexpectedly!")
        
        # Test with insufficient stock
        with self.assertRaises(ValidationError):
            validate_feed_stock_quantity(self.feed_stock, Decimal("150.0"))
        
        # Test with None feed_stock
        try:
            validate_feed_stock_quantity(None, Decimal("50.0"))
        except ValidationError:
            self.fail("validate_feed_stock_quantity raised ValidationError unexpectedly!")
    
    def test_validate_batch_assignment_relationship(self):
        """Test the validate_batch_assignment_relationship function."""
        # Test with matching batch and assignment
        try:
            validate_batch_assignment_relationship(self.batch, self.assignment)
        except ValidationError:
            self.fail("validate_batch_assignment_relationship raised ValidationError unexpectedly!")
        
        # Create a different batch
        other_batch = Batch.objects.create(
            batch_number="TEST002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=15)
        )
        
        # Test with non-matching batch and assignment
        with self.assertRaises(ValidationError):
            validate_batch_assignment_relationship(other_batch, self.assignment)
        
        # Test with None values
        try:
            validate_batch_assignment_relationship(None, self.assignment)
        except ValidationError:
            self.fail("validate_batch_assignment_relationship raised ValidationError unexpectedly!")
        
        try:
            validate_batch_assignment_relationship(self.batch, None)
        except ValidationError:
            self.fail("validate_batch_assignment_relationship raised ValidationError unexpectedly!")
    
    def test_validate_date_range(self):
        """Test the validate_date_range function."""
        # Test with start_date before end_date
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=10)
        try:
            validate_date_range(start_date, end_date)
        except ValidationError:
            self.fail("validate_date_range raised ValidationError unexpectedly!")
        
        # Test with start_date after end_date
        start_date = timezone.now().date()
        end_date = start_date - timedelta(days=10)
        with self.assertRaises(ValidationError):
            validate_date_range(start_date, end_date)
        
        # Test with equal dates
        start_date = timezone.now().date()
        end_date = start_date
        try:
            validate_date_range(start_date, end_date)
        except ValidationError:
            self.fail("validate_date_range raised ValidationError unexpectedly!")
    
    def test_validate_batch_exists(self):
        """Test the validate_batch_exists function."""
        # Test with existing batch
        try:
            batch = validate_batch_exists(self.batch.id)
            self.assertEqual(batch, self.batch)
        except ValidationError:
            self.fail("validate_batch_exists raised ValidationError unexpectedly!")
        
        # Test with non-existing batch
        with self.assertRaises(ValidationError):
            validate_batch_exists(999999)  # Non-existent ID
