"""Tests for transfer action location filters."""

from datetime import date
from decimal import Decimal

from rest_framework import status

from tests.base import BaseAPITestCase

from apps.batch.models import BatchTransferWorkflow, TransferAction
from apps.batch.tests.api.test_utils import (
    create_test_batch,
    create_test_container,
    create_test_container_type,
    create_test_freshwater_station,
    create_test_geography,
    create_test_hall,
    create_test_lifecycle_stage,
    create_test_species,
    create_test_user,
    create_test_batch_container_assignment,
)
from apps.users.models import Geography as UserGeography


class TransferActionFilterTests(BaseAPITestCase):
    """Covers station-based filtering on transfer-actions list endpoint."""

    def setUp(self):
        self.user = create_test_user(geography=UserGeography.ALL)
        self.client.force_authenticate(user=self.user)

        geography = create_test_geography("Filter Geography")
        self.station1 = create_test_freshwater_station(geography=geography, name="Station 1")
        self.station2 = create_test_freshwater_station(geography=geography, name="Station 2")
        hall1 = create_test_hall(station=self.station1, name="Hall 1")
        hall2 = create_test_hall(station=self.station2, name="Hall 2")
        container_type = create_test_container_type("Transfer Tank")

        self.station1_container_a = create_test_container(hall=hall1, container_type=container_type, name="S1-A")
        self.station1_container_b = create_test_container(hall=hall1, container_type=container_type, name="S1-B")
        self.station2_container_a = create_test_container(hall=hall2, container_type=container_type, name="S2-A")
        self.station2_container_b = create_test_container(hall=hall2, container_type=container_type, name="S2-B")

        species = create_test_species("Transfer Salmon")
        lifecycle_stage = create_test_lifecycle_stage(species=species, name="Fry", order=2)

        batch1 = create_test_batch(species=species, lifecycle_stage=lifecycle_stage, batch_number="TRF-BATCH-1")
        batch2 = create_test_batch(species=species, lifecycle_stage=lifecycle_stage, batch_number="TRF-BATCH-2")
        batch3 = create_test_batch(species=species, lifecycle_stage=lifecycle_stage, batch_number="TRF-BATCH-3")

        source_station1 = create_test_batch_container_assignment(
            batch=batch1,
            container=self.station1_container_a,
            lifecycle_stage=lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0"),
        )
        dest_station1 = create_test_batch_container_assignment(
            batch=batch1,
            container=self.station1_container_b,
            lifecycle_stage=lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
        )
        source_station2 = create_test_batch_container_assignment(
            batch=batch2,
            container=self.station2_container_a,
            lifecycle_stage=lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("12.0"),
        )
        dest_station2 = create_test_batch_container_assignment(
            batch=batch2,
            container=self.station2_container_b,
            lifecycle_stage=lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("12.0"),
        )
        source_external = create_test_batch_container_assignment(
            batch=batch3,
            container=self.station2_container_b,
            lifecycle_stage=lifecycle_stage,
            population_count=900,
            avg_weight_g=Decimal("11.0"),
        )
        dest_in_station1 = create_test_batch_container_assignment(
            batch=batch3,
            container=self.station1_container_b,
            lifecycle_stage=lifecycle_stage,
            population_count=300,
            avg_weight_g=Decimal("11.0"),
        )

        workflow1 = BatchTransferWorkflow.objects.create(
            workflow_number="TRF-FILTER-001",
            batch=batch1,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=lifecycle_stage,
            dest_lifecycle_stage=lifecycle_stage,
            planned_start_date=date.today(),
            initiated_by=self.user,
        )
        workflow2 = BatchTransferWorkflow.objects.create(
            workflow_number="TRF-FILTER-002",
            batch=batch2,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=lifecycle_stage,
            dest_lifecycle_stage=lifecycle_stage,
            planned_start_date=date.today(),
            initiated_by=self.user,
        )
        workflow3 = BatchTransferWorkflow.objects.create(
            workflow_number="TRF-FILTER-003",
            batch=batch3,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=lifecycle_stage,
            dest_lifecycle_stage=lifecycle_stage,
            planned_start_date=date.today(),
            initiated_by=self.user,
        )

        self.station1_internal_action = TransferAction.objects.create(
            workflow=workflow1,
            action_number=1,
            source_assignment=source_station1,
            dest_assignment=dest_station1,
            source_population_before=1000,
            transferred_count=400,
            transferred_biomass_kg=Decimal("4.0"),
            status="COMPLETED",
            actual_execution_date=date.today(),
        )
        self.station2_internal_action = TransferAction.objects.create(
            workflow=workflow2,
            action_number=1,
            source_assignment=source_station2,
            dest_assignment=dest_station2,
            source_population_before=1000,
            transferred_count=350,
            transferred_biomass_kg=Decimal("4.2"),
            status="COMPLETED",
            actual_execution_date=date.today(),
        )
        self.station1_incoming_action = TransferAction.objects.create(
            workflow=workflow3,
            action_number=1,
            source_assignment=source_external,
            dest_assignment=dest_in_station1,
            source_population_before=900,
            transferred_count=250,
            transferred_biomass_kg=Decimal("2.75"),
            status="COMPLETED",
            actual_execution_date=date.today(),
        )

    def test_filter_transfer_actions_by_station(self):
        url = self.get_api_url("batch", "transfer-actions") + f"?station={self.station1.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_ids = {row["id"] for row in response.data["results"]}
        self.assertIn(self.station1_internal_action.id, action_ids)
        self.assertIn(self.station1_incoming_action.id, action_ids)
        self.assertNotIn(self.station2_internal_action.id, action_ids)
