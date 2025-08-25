"""
Feed Manager for AquaMind Data Generation

Implements comprehensive feed management system with FIFO inventory,
procurement optimization, seasonal pricing, and supplier management.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Sum

from apps.inventory.models import (
    Feed, FeedStock, FeedPurchase
)
from apps.infrastructure.models import FeedContainer
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class FeedManager:
    """
    Manages comprehensive feed operations including:
    - FIFO inventory management
    - Procurement optimization with seasonal pricing
    - Supplier relationships and lead times
    - Feed quality tracking and wastage
    - Multi-site distribution logistics
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize the feed manager.

        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run

        # Get or create system user
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='feed_manager',
                defaults={
                    'email': 'feed@aquamind.com',
                    'first_name': 'Feed',
                    'last_name': 'Manager',
                    'is_staff': False,
                    'is_active': True
                }
            )

            # Initialize suppliers
            self._initialize_suppliers()

        # Track inventory levels
        self.inventory_levels = {}  # feed_type -> current_stock_kg
        self.reorder_thresholds = GP.REORDER_THRESHOLDS

    def _initialize_suppliers(self):
        """Initialize supplier data (for now, just log availability)."""
        # Note: FeedSupplier model doesn't exist, so we'll simulate supplier logic
        self.suppliers = [
            {
                'name': 'BioMar Norway',
                'country': 'Norway',
                'lead_time_days': 7,
                'price_multiplier': 1.0,
                'reliability': 0.95,
                'specialties': ['salmon_starter', 'salmon_grower']
            },
            {
                'name': 'Skretting Scotland',
                'country': 'Scotland',
                'lead_time_days': 5,
                'price_multiplier': 1.02,
                'reliability': 0.98,
                'specialties': ['salmon_finisher', 'trout_feeds']
            },
            {
                'name': 'Aller Aqua Denmark',
                'country': 'Denmark',
                'lead_time_days': 10,
                'price_multiplier': 0.98,
                'reliability': 0.92,
                'specialties': ['salmon_starter', 'organic_feeds']
            },
            {
                'name': 'Ewos Canada',
                'country': 'Canada',
                'lead_time_days': 14,
                'price_multiplier': 1.05,
                'reliability': 0.90,
                'specialties': ['salmon_grower', 'specialty_feeds']
            }
        ]
        logger.info(f"Initialized {len(self.suppliers)} feed suppliers")

    def process_daily_feed_operations(self, current_date: date) -> Dict[str, int]:
        """
        Process daily feed operations including procurement, inventory, and distribution.

        Args:
            current_date: Current date for processing

        Returns:
            Dictionary with counts of operations performed
        """
        if self.dry_run:
            logger.info("Would process daily feed operations")
            return {'orders_placed': 0, 'deliveries_received': 0, 'inventory_adjusted': 0}

        operations_count = {
            'orders_placed': 0,
            'deliveries_received': 0,
            'inventory_adjusted': 0,
            'transfers_processed': 0
        }

        with transaction.atomic():
            # Check inventory levels and place orders
            orders_placed = self._check_inventory_and_order(current_date)
            operations_count['orders_placed'] = orders_placed

            # Process incoming deliveries
            deliveries = self._process_deliveries(current_date)
            operations_count['deliveries_received'] = deliveries

            # Update inventory levels
            self._update_inventory_levels()
            operations_count['inventory_adjusted'] = 1

            # Process feed transfers between facilities
            transfers = self._process_feed_transfers(current_date)
            operations_count['transfers_processed'] = transfers

            logger.info(f"Daily feed operations completed: {operations_count}")
            return operations_count

    def _check_inventory_and_order(self, current_date: date) -> int:
        """Check inventory levels and place orders when below thresholds."""
        orders_placed = 0

        # Direct mapping from feed_type to feed name
        feed_type_mapping = {
            'starter_0.5mm': 'Starter 0.5MM',
            'starter_1.0mm': 'Starter 1.0MM',
            'grower_2.0mm': 'Grower 2.0MM',
            'grower_3.0mm': 'Grower 3.0MM',
            'finisher_4.5mm': 'Finisher 4.5MM',
            'finisher_6.0mm': 'Finisher 7.0MM'
        }

        for feed_type, threshold in self.reorder_thresholds.items():
            try:
                feed_name = feed_type_mapping.get(feed_type)
                if not feed_name:
                    logger.warning(f"No mapping found for feed type {feed_type}")
                    continue

                feed = Feed.objects.get(name=feed_name)
                current_stock = self._get_current_stock(feed)

                if current_stock < threshold:
                    order_quantity = self._calculate_order_quantity(feed, current_stock, threshold)
                    supplier = self._select_supplier(feed, current_date)

                    if supplier:
                        self._place_purchase_order(feed, supplier, order_quantity, current_date)
                        orders_placed += 1

            except Feed.DoesNotExist:
                logger.warning(f"Feed {feed_name} not found for type {feed_type}")
            except Exception as e:
                logger.error(f"Error checking inventory for {feed_type}: {e}")

        return orders_placed

    def _get_current_stock(self, feed: Feed) -> float:
        """Get current stock level for a feed type."""
        try:
            # Try to get FeedStock records first
            stock_entries = FeedStock.objects.filter(feed=feed)
            if stock_entries.exists():
                total_stock = sum(float(entry.current_quantity_kg) for entry in stock_entries)
                return total_stock
            else:
                # If no FeedStock records exist, return a default stock level
                logger.warning(f"No FeedStock records found for {feed.name}, using default stock level")
                return 10000.0  # Default 10,000 kg stock
        except Exception as e:
            logger.error(f"Error getting stock for {feed.name}: {e}, using default stock level")
            return 10000.0  # Default 10,000 kg stock

    def _calculate_order_quantity(self, feed: Feed, current_stock: float, threshold: float) -> int:
        """Calculate optimal order quantity based on consumption patterns."""
        # Order enough to last 30 days plus buffer
        daily_consumption = self._estimate_daily_consumption(feed)
        safety_buffer = daily_consumption * 7  # 7-day buffer
        order_quantity = int((threshold * 2 - current_stock) + safety_buffer)

        # Round to nearest 1000 kg
        order_quantity = ((order_quantity + 999) // 1000) * 1000

        # Apply minimum order constraints
        minimum_order = 5000  # 5 tons minimum
        order_quantity = max(order_quantity, minimum_order)

        return order_quantity

    def _estimate_daily_consumption(self, feed: Feed) -> float:
        """Estimate daily consumption for a feed type based on current batches."""
        # Simple estimation based on active batches in relevant stages
        stage_map = {
            'Starter 0.5MM': 'fry',
            'Starter 1.0MM': 'parr',
            'Grower 2.0MM': 'smolt',
            'Grower 3.0MM': 'post_smolt',
            'Finisher 4.5MM': 'grow_out'
        }

        stage = stage_map.get(feed.name)
        if not stage:
            return 1000.0  # Default

        # Estimate based on typical feeding rates and batch sizes
        daily_rate_per_kg_biomass = GP.FEED_RATES.get(stage, 2.0) / 100
        estimated_total_biomass = 100000  # kg - rough estimate for all batches in stage
        daily_consumption = estimated_total_biomass * daily_rate_per_kg_biomass

        return daily_consumption

    def _select_supplier(self, feed: Feed, order_date: date) -> Optional[dict]:
        """Select optimal supplier based on price, reliability, and lead time."""
        if not self.suppliers:
            return None

        # Score suppliers based on multiple factors
        scored_suppliers = []
        for supplier in self.suppliers:
            score = 0

            # Price factor (lower is better)
            price_multiplier = supplier['price_multiplier']
            score += (1.0 / price_multiplier) * 100

            # Reliability factor
            score += supplier['reliability'] * 50

            # Lead time factor (lower is better)
            lead_time_penalty = supplier['lead_time_days'] / 20.0  # Normalize
            score += (1.0 - lead_time_penalty) * 30

            # Seasonal availability factor
            seasonal_factor = self._calculate_seasonal_availability(supplier, order_date)
            score += seasonal_factor * 20

            scored_suppliers.append((score, supplier))

        # Select highest scoring supplier
        scored_suppliers.sort(reverse=True)
        return scored_suppliers[0][1]

    def _calculate_seasonal_availability(self, supplier: dict, order_date: date) -> float:
        """Calculate seasonal availability factor for a supplier."""
        month = order_date.month

        # Some suppliers may have seasonal constraints
        if supplier['name'] == 'BioMar Norway':
            # Better availability in northern hemisphere summer
            if month in [6, 7, 8]:
                return 1.0
            elif month in [12, 1, 2]:
                return 0.8
            else:
                return 0.9
        elif supplier['name'] == 'Ewos Canada':
            # Better availability in northern hemisphere winter
            if month in [12, 1, 2]:
                return 1.0
            elif month in [6, 7, 8]:
                return 0.8
            else:
                return 0.9

        return 0.9  # Default good availability

    def _place_purchase_order(self, feed: Feed, supplier: dict, quantity_kg: int, order_date: date):
        """Place a purchase order for feed."""
        try:
            # Calculate pricing
            base_price = GP.FEED_TYPES.get(feed.name.lower().replace(' ', '_'), {}).get('price_base_eur', 2.0)
            supplier_multiplier = supplier.get('price_multiplier', 1.0)
            seasonal_multiplier = self._get_seasonal_price_multiplier(feed.name, order_date)

            unit_price = base_price * supplier_multiplier * seasonal_multiplier
            total_cost = unit_price * quantity_kg

            # Calculate delivery date
            delivery_date = order_date + timedelta(days=supplier['lead_time_days'])

            # Create purchase order (using FeedPurchase model)
            FeedPurchase.objects.create(
                feed=feed,
                purchase_date=order_date,
                quantity_kg=Decimal(str(quantity_kg)),
                cost_per_kg=Decimal(str(unit_price)),
                supplier=supplier['name'],
                batch_number=f"PO-{order_date.strftime('%Y%m%d')}-{feed.name[:3].upper()}-{random.randint(100, 999)}",
                expiry_date=delivery_date + timedelta(days=180),  # 6 months shelf life
                notes=f"Auto-generated order based on inventory threshold from {supplier['name']}"
            )

            logger.info(f"Placed order for {quantity_kg:,}kg of {feed.name} from {supplier['name']}")

        except Exception as e:
            logger.error(f"Error placing purchase order: {e}")

    def _get_seasonal_price_multiplier(self, feed_name: str, order_date: date) -> float:
        """Get seasonal price multiplier for feed."""
        quarter = (order_date.month - 1) // 3 + 1
        base_multiplier = GP.FEED_PRICE_SEASONAL.get(f'Q{quarter}', 1.0)

        # Add market volatility
        volatility = random.uniform(-0.08, 0.12)  # ±12%
        return base_multiplier * (1.0 + volatility)

    def _process_deliveries(self, current_date: date) -> int:
        """Process incoming feed deliveries."""
        deliveries_processed = 0

        try:
            # Find recent purchases that would be delivered now
            recent_purchases = FeedPurchase.objects.filter(
                purchase_date__gte=current_date - timedelta(days=14),
                purchase_date__lte=current_date
            )

            for purchase in recent_purchases:
                # Simulate delivery (assume it arrives within 3-7 days)
                days_since_order = (current_date - purchase.purchase_date).days
                supplier = next((s for s in self.suppliers if s['name'] == purchase.supplier), None)

                if supplier and days_since_order >= 3:  # Minimum 3 days for delivery
                    # Simulate delivery reliability
                    if random.random() < supplier['reliability']:
                        # Successful delivery
                        self._process_successful_delivery(purchase)
                        deliveries_processed += 1
                        logger.info(f"Processed delivery of {purchase.quantity_kg}kg {purchase.feed.name}")
                    else:
                        logger.info(f"Delivery delayed for {purchase.quantity_kg}kg {purchase.feed.name}")

        except Exception as e:
            logger.error(f"Error processing deliveries: {e}")

        return deliveries_processed

    def _process_successful_delivery(self, purchase: FeedPurchase):
        """Process a successful feed delivery."""
        try:
            # Find an appropriate feed container (prefer silos over barges for deliveries)
            feed_container = FeedContainer.objects.filter(
                container_type='SILO',
                active=True
            ).first()

            if not feed_container:
                # Fallback to any active container
                feed_container = FeedContainer.objects.filter(active=True).first()

            if feed_container:
                # Check if stock already exists for this feed-container combination
                existing_stock = FeedStock.objects.filter(
                    feed=purchase.feed,
                    feed_container=feed_container
                ).first()

                if existing_stock:
                    # Update existing stock
                    existing_stock.current_quantity_kg += purchase.quantity_kg
                    existing_stock.notes += f" | Received {purchase.quantity_kg}kg from {purchase.supplier} - Batch {purchase.batch_number}"
                    existing_stock.save()
                    logger.info(f"Updated existing stock: +{purchase.quantity_kg}kg {purchase.feed.name} in {feed_container.name}")
                else:
                    # Create new stock entry
                    FeedStock.objects.create(
                        feed=purchase.feed,
                        feed_container=feed_container,
                        current_quantity_kg=purchase.quantity_kg,
                        reorder_threshold_kg=Decimal('5000'),  # Default threshold
                        notes=f"Received from {purchase.supplier} - Batch {purchase.batch_number}"
                    )
                    logger.info(f"Created new stock: {purchase.quantity_kg}kg {purchase.feed.name} in {feed_container.name}")
            else:
                logger.warning(f"No active feed containers available for {purchase.feed.name} delivery")

        except Exception as e:
            logger.error(f"Error processing successful delivery: {e}")

    def _update_inventory_levels(self):
        """Update cached inventory levels."""
        try:
            for feed in Feed.objects.filter(is_active=True):
                self.inventory_levels[feed.name] = self._get_current_stock(feed)
        except Exception as e:
            logger.error(f"Error updating inventory levels: {e}")

    def _process_feed_transfers(self, current_date: date) -> int:
        """Process feed transfers between facilities."""
        transfers_processed = 0

        try:
            # Simple transfer logic - could be enhanced with actual facility requirements
            # For now, just log the capability
            logger.debug("Feed transfer processing available for future implementation")
            return 0

        except Exception as e:
            logger.error(f"Error processing feed transfers: {e}")

        return transfers_processed

    def get_inventory_status(self) -> Dict[str, Any]:
        """Get comprehensive inventory status report."""
        status = {
            'total_value_eur': 0.0,
            'low_stock_items': [],
            'expiring_soon': [],
            'feed_types': {}
        }

        try:
            for feed in Feed.objects.filter(is_active=True):
                stock_level = self._get_current_stock(feed)
                status['feed_types'][feed.name] = {
                    'current_stock_kg': stock_level,
                    'reorder_threshold_kg': self.reorder_thresholds.get(feed.name, 0),
                    'status': 'OK'
                }

                # Check low stock
                if stock_level < self.reorder_thresholds.get(feed.name, float('inf')):
                    status['low_stock_items'].append(feed.name)
                    status['feed_types'][feed.name]['status'] = 'LOW_STOCK'

                # Calculate inventory value (simplified)
                avg_cost = float(feed.protein_percentage or 0) * 0.1  # Rough cost calculation
                status['total_value_eur'] += stock_level * avg_cost

                # Note: FeedStock doesn't have expiry_date field in this model
                # Expiring stock tracking would need to be added to the model

        except Exception as e:
            logger.error(f"Error generating inventory status: {e}")

        return status

    def _get_average_cost(self, feed: Feed) -> float:
        """Get estimated cost per kg for a feed type."""
        try:
            # Use protein percentage as a rough cost indicator
            protein_pct = float(feed.protein_percentage or 0)
            return protein_pct * 0.1  # Rough cost calculation
        except Exception as e:
            logger.error(f"Error calculating average cost for {feed.name}: {e}")

        return 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the feed manager."""
        return {
            'suppliers_count': len(self.suppliers),
            'total_purchases': FeedPurchase.objects.count(),
            'total_inventory_value': self.get_inventory_status()['total_value_eur'],
            'low_stock_items': len(self.get_inventory_status()['low_stock_items'])
        }
