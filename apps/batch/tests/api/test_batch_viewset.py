"""
Tests for the BatchViewSet.
"""
from rest_framework import status
from tests.base import BaseAPITestCase
from decimal import Decimal
from datetime import date, timedelta
import datetime # Import the full module for aliasing
from unittest.mock import patch
from django.utils import timezone

OriginalDate = datetime.date  # Alias for the original datetime.date

from apps.batch.models import (
    Batch,
    BatchComposition,
    BatchMixEvent,
    BatchMixEventComponent,
)
from apps.batch.tests.api.test_utils import (
    create_test_user,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchViewSetTest(BaseAPITestCase):
    """Test the Batch viewset."""

    def setUp(self):
        """Set up test data."""
        # Create a test user and authenticate
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        
        # Create species and lifecycle stage
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )
        
        # Create a batch
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001"
        )
        
        # Create a container and assignment for the batch
        self.container = create_test_container(name="Tank 1")
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        
        # Valid data for API tests
        self.valid_batch_data = {
            'batch_number': 'BATCH002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': date.today().isoformat(),
            'expected_end_date': (date.today() + timedelta(days=365)).isoformat(),
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'notes': 'Test batch'
        }

    def test_list_batches(self):
        """Test listing batches."""
        url = self.get_api_url('batch', 'batches')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
        
        # Check calculated fields
        self.assertEqual(response.data['results'][0]['calculated_population_count'], 1000)
        self.assertEqual(Decimal(response.data['results'][0]['calculated_biomass_kg']), Decimal('10.00'))
        self.assertEqual(Decimal(response.data['results'][0]['calculated_avg_weight_g']), Decimal('10.00'))

    def test_create_batch(self):
        """
        Test creating a new batch via the API.
        """
        url = self.get_api_url('batch', 'batches')
        
        # Print request data for debugging
        print("Create Batch Request Data:", self.valid_batch_data)
        
        response = self.client.post(url, self.valid_batch_data, format='json')
        
        # Print response for debugging
        print("Create Batch Response Status:", response.status_code)
        if response.status_code != status.HTTP_201_CREATED:
            print("Response Data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Batch.objects.count(), 2)
        
        # Verify the created batch
        new_batch = Batch.objects.get(batch_number='BATCH002')
        self.assertEqual(new_batch.species, self.species)
        self.assertEqual(new_batch.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(new_batch.status, 'ACTIVE')
        self.assertEqual(new_batch.batch_type, 'STANDARD')
        self.assertEqual(new_batch.notes, 'Test batch')

    def test_retrieve_batch(self):
        """Test retrieving a batch."""
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch_number'], 'BATCH001')
        self.assertEqual(response.data['species'], self.species.id)
        self.assertEqual(response.data['lifecycle_stage'], self.lifecycle_stage.id)
        self.assertEqual(response.data['calculated_population_count'], 1000)
        self.assertEqual(Decimal(response.data['calculated_biomass_kg']), Decimal('10.00'))
        self.assertEqual(Decimal(response.data['calculated_avg_weight_g']), Decimal('10.00'))

    def test_update_batch(self):
        """Test updating a batch (direct fields like status, notes)."""
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
        update_data = {
            'batch_number': 'BATCH001-UPDATED',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': self.batch.start_date.isoformat(),
            'expected_end_date': self.batch.expected_end_date.isoformat(),
            'status': 'COMPLETED',
            'batch_type': 'STANDARD',
            'notes': 'Updated test batch'
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the batch from the database
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.batch_number, 'BATCH001-UPDATED')
        self.assertEqual(self.batch.status, 'COMPLETED')
        self.assertEqual(self.batch.notes, 'Updated test batch')

    def test_partial_update_batch(self):
        """Test partially updating a batch (direct fields like status, notes)."""
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
        update_data = {
            'status': 'COMPLETED',
            'notes': 'Partially updated batch'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the batch from the database
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'COMPLETED')
        self.assertEqual(self.batch.notes, 'Partially updated batch')

    def test_delete_batch(self):
        """Test deleting a batch."""
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Batch.objects.count(), 0)

    def test_filter_batches(self):
        """Test filtering batches."""
        # Create another batch with different species
        other_species = create_test_species(name="Rainbow Trout")
        other_stage = create_test_lifecycle_stage(
            species=other_species,
            name="Smolt",
            order=3
        )
        other_batch = create_test_batch(
            species=other_species,
            lifecycle_stage=other_stage,
            batch_number="BATCH002"
        )
        
        # Create assignment for other_batch (required for RBAC filtering)
        create_test_batch_container_assignment(
            batch=other_batch,
            container=self.container,
            lifecycle_stage=other_stage,
            population_count=500,
            avg_weight_g=Decimal("15.0")
        )
        
        # Define a fixed "today" for mocking to make date-based filters deterministic
        simulated_today = OriginalDate(2025, 1, 1) # Use OriginalDate to create the instance for clarity

        # Patch the 'date' name in the current module's namespace.
        # autospec=OriginalDate ensures the mock behaves like datetime.date for isinstance checks etc.
        with patch('apps.batch.tests.api.test_batch_viewset.date', autospec=OriginalDate) as MockDateType:
            MockDateType.today.return_value = simulated_today
            # When date(Y, M, D) is called (which is now MockDateType(Y,M,D)), 
            # it should return a real datetime.date instance.
            MockDateType.side_effect = lambda *args, **kwargs: OriginalDate(*args, **kwargs)
            
            # Filter by species
            url = f"{self.get_api_url('batch', 'batches')}?species={self.species.id}"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')

            # Filter by status
            url = f"{self.get_api_url('batch', 'batches')}?status=ACTIVE"
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)  # Both batches are active

            # Filter by date range
            # The batches were created with start_date = real_today - 30 days
            # So we need to filter for dates that include that range
            thirty_days_ago = OriginalDate.today() - timedelta(days=30)
            sixty_days_ago = OriginalDate.today() - timedelta(days=60)
            ten_days_ago = OriginalDate.today() - timedelta(days=10)

            # Filter for batches created between 60 days ago and 10 days ago
            start_date_query_val = sixty_days_ago.isoformat()
            end_date_query_val = ten_days_ago.isoformat()
            url = f"{self.get_api_url('batch', 'batches')}?start_date_after={start_date_query_val}&start_date_before={end_date_query_val}"
            response = self.client.get(url)

            # Print response for debugging
            print("Filter by Date Range Response:", response.data)

            # Both test batches should be included as they were created ~30 days ago
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)

            # Filter by batch number
            url = f"{self.get_api_url('batch', 'batches')}?batch_number=BATCH001"
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')

    def test_mixed_lineage_standard_batch_returns_self_as_root(self):
        """Standard batches should resolve to themselves with 100% root share."""
        url = self.get_action_url(
            'batch',
            'batches',
            pk=self.batch.id,
            action='mixed-lineage',
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['id'], self.batch.id)
        self.assertEqual(response.data['root_sources'], [
            {
                'batch_id': self.batch.id,
                'batch_number': self.batch.batch_number,
                'percentage': '100.00',
            }
        ])
        self.assertEqual(response.data['max_depth'], 0)

    def test_mixed_lineage_returns_compounded_root_shares(self):
        """
        Mixed lineage should recursively flatten compounded percentages.

        Example:
        - M1 = A(60%) + B(40%)
        - M2 = M1(50%) + C(50%)
        => roots for M2: A=30%, B=20%, C=50%
        """
        batch_a = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH-A",
        )
        batch_b = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH-B",
        )
        batch_c = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH-C",
        )

        mixed_1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIX-1",
        )
        mixed_1.batch_type = 'MIXED'
        mixed_1.save(update_fields=['batch_type'])

        mixed_2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIX-2",
        )
        mixed_2.batch_type = 'MIXED'
        mixed_2.save(update_fields=['batch_type'])

        container_2 = create_test_container(name="Tank 2")
        container_3 = create_test_container(name="Tank 3")
        container_4 = create_test_container(name="Tank 4")
        container_5 = create_test_container(name="Tank 5")

        assignment_a = create_test_batch_container_assignment(
            batch=batch_a,
            container=container_2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=600,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_b = create_test_batch_container_assignment(
            batch=batch_b,
            container=container_3,
            lifecycle_stage=self.lifecycle_stage,
            population_count=400,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_m1 = create_test_batch_container_assignment(
            batch=mixed_1,
            container=container_4,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_c = create_test_batch_container_assignment(
            batch=batch_c,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
        )
        create_test_batch_container_assignment(
            batch=mixed_2,
            container=container_5,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0"),
        )

        mix_1 = BatchMixEvent.objects.create(
            mixed_batch=mixed_1,
            container=container_4,
            mixed_at=timezone.now() - timedelta(days=2),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_1,
            source_assignment=assignment_a,
            source_batch=batch_a,
            population_count=600,
            biomass_kg=Decimal("6.0"),
            percentage=Decimal("60.0"),
            is_transferred_in=True,
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_1,
            source_assignment=assignment_b,
            source_batch=batch_b,
            population_count=400,
            biomass_kg=Decimal("4.0"),
            percentage=Decimal("40.0"),
            is_transferred_in=False,
        )

        mix_2 = BatchMixEvent.objects.create(
            mixed_batch=mixed_2,
            container=container_5,
            mixed_at=timezone.now() - timedelta(days=1),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_2,
            source_assignment=assignment_m1,
            source_batch=mixed_1,
            population_count=500,
            biomass_kg=Decimal("5.0"),
            percentage=Decimal("50.0"),
            is_transferred_in=True,
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_2,
            source_assignment=assignment_c,
            source_batch=batch_c,
            population_count=500,
            biomass_kg=Decimal("5.0"),
            percentage=Decimal("50.0"),
            is_transferred_in=False,
        )

        url = self.get_action_url(
            'batch',
            'batches',
            pk=mixed_2.id,
            action='mixed-lineage',
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        root_shares = {
            item['batch_number']: Decimal(item['percentage'])
            for item in response.data['root_sources']
        }
        self.assertEqual(root_shares["BATCH-A"], Decimal("30.00"))
        self.assertEqual(root_shares["BATCH-B"], Decimal("20.00"))
        self.assertEqual(root_shares["BATCH-C"], Decimal("50.00"))

        self.assertEqual(response.data['max_depth'], 2)
        self.assertEqual(len(response.data['graph']['mix_nodes']), 2)
        self.assertIn(
            "Resolved from latest BatchMixEvent.",
            response.data['boundaries']['resolution_notes'],
        )

    def test_mixed_lineage_falls_back_to_batch_composition(self):
        """When no mix event exists, lineage should use BatchComposition fallback."""
        source_1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SRC-1",
        )
        source_2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SRC-2",
        )
        mixed = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIX-FALLBACK",
        )
        mixed.batch_type = 'MIXED'
        mixed.save(update_fields=['batch_type'])
        create_test_batch_container_assignment(
            batch=mixed,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0"),
        )

        BatchComposition.objects.create(
            mixed_batch=mixed,
            source_batch=source_1,
            percentage=Decimal("70.0"),
            population_count=700,
            biomass_kg=Decimal("7.0"),
        )
        BatchComposition.objects.create(
            mixed_batch=mixed,
            source_batch=source_2,
            percentage=Decimal("30.0"),
            population_count=300,
            biomass_kg=Decimal("3.0"),
        )

        url = self.get_action_url(
            'batch',
            'batches',
            pk=mixed.id,
            action='mixed-lineage',
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['root_sources'], [
            {'batch_id': source_1.id, 'batch_number': 'SRC-1', 'percentage': '70.00'},
            {'batch_id': source_2.id, 'batch_number': 'SRC-2', 'percentage': '30.00'},
        ])
        self.assertIn(
            "Resolved from BatchComposition fallback (no qualifying BatchMixEvent).",
            response.data['boundaries']['resolution_notes'],
        )
