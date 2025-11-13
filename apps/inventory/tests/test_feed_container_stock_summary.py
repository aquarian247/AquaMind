"""Tests for feed container stock summary endpoint with geography filters."""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.infrastructure.models import (
    Area,
    ContainerType,
    FeedContainer,
    Geography,
    Hall,
    FreshwaterStation,
)
from apps.inventory.models import Feed, FeedContainerStock, FeedPurchase
from apps.users.models import User


class FeedContainerStockSummaryTest(APITestCase):
    """Validate geography-aware aggregation for feed container stock summary."""

    def setUp(self):
        self.client = APIClient()
        # Create user - profile with ADMIN/ALL access created automatically via signal
        self.user = User.objects.create_user(
            username="stock_user",
            password="p@ssword123"
        )
        self.client.force_authenticate(user=self.user)

        # Geography structures
        self.geo_area = Geography.objects.create(name="Marine Geo")
        self.geo_station = Geography.objects.create(name="Freshwater Geo")

        # Marine infrastructure
        self.area = Area.objects.create(
            name="Marine Area",
            geography=self.geo_area,
            latitude=0,
            longitude=0,
            max_biomass=Decimal("1000.0"),
        )
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("200.0"),
        )
        self.area_feed_container = FeedContainer.objects.create(
            name="Area Silo",
            container_type="SILO",
            area=self.area,
            capacity_kg=Decimal("500.0"),
        )

        # Freshwater infrastructure
        self.station = FreshwaterStation.objects.create(
            name="Station",
            station_type="FRESHWATER",
            geography=self.geo_station,
            latitude=0,
            longitude=0,
        )
        self.hall = Hall.objects.create(
            name="Hall A",
            freshwater_station=self.station,
            description="",
        )
        self.hall_feed_container = FeedContainer.objects.create(
            name="Hall Silo",
            container_type="SILO",
            hall=self.hall,
            capacity_kg=Decimal("600.0"),
        )

        # Feed + purchases feeding the stock
        self.feed = Feed.objects.create(name="Grower", brand="BrandA", size_category="MEDIUM")
        self.other_feed = Feed.objects.create(name="Starter", brand="BrandB", size_category="SMALL")

        self.area_purchase = FeedPurchase.objects.create(
            feed=self.feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal("120.0"),
            cost_per_kg=Decimal("2.50"),
            supplier="Marine Supplier",
        )
        self.hall_purchase = FeedPurchase.objects.create(
            feed=self.other_feed,
            purchase_date=timezone.now().date(),
            quantity_kg=Decimal("180.0"),
            cost_per_kg=Decimal("3.00"),
            supplier="Freshwater Supplier",
        )

        now = timezone.now()
        FeedContainerStock.objects.create(
            feed_container=self.area_feed_container,
            feed_purchase=self.area_purchase,
            quantity_kg=Decimal("100.0"),
            entry_date=now,
        )
        FeedContainerStock.objects.create(
            feed_container=self.hall_feed_container,
            feed_purchase=self.hall_purchase,
            quantity_kg=Decimal("150.0"),
            entry_date=now,
        )

        self.summary_url = "/api/v1/inventory/feed-container-stock/summary/"

    def test_summary_geography_filters(self):
        """Ensure geography filters isolate marine vs freshwater stock."""
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(response.data["total_quantity_kg"], 250.0)
        self.assertAlmostEqual(response.data["total_value"], 700.0)
        self.assertEqual(response.data["unique_containers"], 2)

        marine_resp = self.client.get(f"{self.summary_url}?geography={self.geo_area.id}")
        self.assertEqual(marine_resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(marine_resp.data["total_quantity_kg"], 100.0)
        self.assertAlmostEqual(marine_resp.data["total_value"], 250.0)
        self.assertEqual(marine_resp.data["unique_containers"], 1)

        freshwater_resp = self.client.get(f"{self.summary_url}?geography={self.geo_station.id}")
        self.assertEqual(freshwater_resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(freshwater_resp.data["total_quantity_kg"], 150.0)
        self.assertAlmostEqual(freshwater_resp.data["total_value"], 450.0)
        self.assertEqual(freshwater_resp.data["unique_containers"], 1)

    def test_area_hall_station_filters(self):
        """Area, hall, and station filters narrow the result set correctly."""
        area_resp = self.client.get(f"{self.summary_url}?area={self.area.id}")
        self.assertEqual(area_resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(area_resp.data["total_quantity_kg"], 100.0)
        self.assertEqual(area_resp.data["unique_containers"], 1)
        self.assertEqual(len(area_resp.data["by_container"]), 1)

        hall_resp = self.client.get(f"{self.summary_url}?hall={self.hall.id}")
        self.assertEqual(hall_resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(hall_resp.data["total_quantity_kg"], 150.0)
        self.assertEqual(hall_resp.data["unique_containers"], 1)

        station_resp = self.client.get(
            f"{self.summary_url}?freshwater_station={self.station.id}"
        )
        self.assertEqual(station_resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(station_resp.data["total_quantity_kg"], 150.0)
        self.assertEqual(station_resp.data["unique_containers"], 1)
