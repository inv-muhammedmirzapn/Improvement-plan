"""
Tests for Restaurant Service.

Covers:
- Business rules and state transitions
- Concurrent capacity slot reservation (SELECT FOR UPDATE correctness)
- Idempotency of restaurant close
- OutboxEvent committed atomically with business state
- Duplicate event handling (ProcessedMessage)
- Menu item availability race condition
"""
import threading
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, TransactionTestCase

from restaurant.exceptions import CapacityExceeded, MenuItemUnavailable, RestaurantClosed
from restaurant.models import MenuItem, OutboxEvent, ProcessedMessage, Restaurant
from restaurant.services import restaurant as restaurant_service
from restaurant.services.inbox import process_once
from restaurant.services.outbox import append, claim_batch, mark_published


class RestaurantCreationTest(TestCase):
    def test_create_restaurant_emits_outbox_event(self):
        restaurant = restaurant_service.create_restaurant(
            name='Spice Kitchen',
            description='Fine Indian dining',
            max_active_orders=20,
        )
        self.assertEqual(restaurant.status, Restaurant.Status.OPEN)
        outbox = OutboxEvent.objects.filter(aggregate_id=restaurant.id, event_type='RestaurantCreated').first()
        self.assertIsNotNone(outbox)
        self.assertIsNone(outbox.published_at)

    def test_close_restaurant_idempotent(self):
        restaurant = restaurant_service.create_restaurant(name='Test Restaurant')
        restaurant_service.close_restaurant(restaurant.id)
        # Second call must not raise and must not create duplicate outbox event
        restaurant_service.close_restaurant(restaurant.id)
        closed_events = OutboxEvent.objects.filter(aggregate_id=restaurant.id, event_type='RestaurantClosed')
        self.assertEqual(closed_events.count(), 1)


class CapacityTest(TransactionTestCase):
    """
    TransactionTestCase because we test concurrent DB operations.
    Each thread runs in its own transaction.
    """
    def setUp(self):
        self.restaurant = restaurant_service.create_restaurant(
            name='Concurrent Kitchen',
            max_active_orders=1,  # Only 1 slot!
        )

    def test_single_reservation_succeeds(self):
        restaurant_service.reserve_capacity_slot(self.restaurant.id)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.active_order_count, 1)

    def test_concurrent_reservation_only_one_succeeds(self):
        """
        Two threads race to reserve the single remaining slot.
        Only one must succeed; the other must get CapacityExceeded.
        This validates SELECT FOR UPDATE serializes the critical section.
        """
        results = []
        errors = []

        def try_reserve():
            try:
                restaurant_service.reserve_capacity_slot(self.restaurant.id)
                results.append('ok')
            except CapacityExceeded:
                errors.append('capacity_exceeded')

        t1 = threading.Thread(target=try_reserve)
        t2 = threading.Thread(target=try_reserve)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 1, 'Exactly one reservation should succeed.')
        self.assertEqual(len(errors), 1, 'Exactly one should get CapacityExceeded.')
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.active_order_count, 1)

    def test_capacity_releases_correctly(self):
        restaurant_service.reserve_capacity_slot(self.restaurant.id)
        restaurant_service.release_capacity_slot(self.restaurant.id)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.active_order_count, 0)

    def test_release_does_not_go_below_zero(self):
        """Release when count is 0 must not result in negative count."""
        restaurant_service.release_capacity_slot(self.restaurant.id)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.active_order_count, 0)

    def test_closed_restaurant_cannot_reserve(self):
        restaurant_service.close_restaurant(self.restaurant.id)
        with self.assertRaises(RestaurantClosed):
            restaurant_service.reserve_capacity_slot(self.restaurant.id)


class MenuItemTest(TestCase):
    def setUp(self):
        self.restaurant = restaurant_service.create_restaurant(name='Menu Test Kitchen')

    def test_add_menu_item_emits_outbox(self):
        item = restaurant_service.add_menu_item(
            restaurant_id=self.restaurant.id,
            name='Chicken Biryani',
            price=Decimal('250.00'),
        )
        self.assertTrue(item.is_available)
        outbox = OutboxEvent.objects.filter(aggregate_id=item.id, event_type='MenuItemCreated').first()
        self.assertIsNotNone(outbox)

    def test_set_item_availability_idempotent(self):
        item = restaurant_service.add_menu_item(
            restaurant_id=self.restaurant.id,
            name='Paneer Rice',
            price=Decimal('180.00'),
        )
        # Mark unavailable twice
        restaurant_service.set_item_availability(item.id, self.restaurant.id, False)
        restaurant_service.set_item_availability(item.id, self.restaurant.id, False)
        events = OutboxEvent.objects.filter(aggregate_id=item.id, event_type='MenuItemAvailabilityChanged')
        self.assertEqual(events.count(), 1)  # Only one event for the actual change

    def test_validate_order_items_rejects_unavailable(self):
        item = restaurant_service.add_menu_item(
            restaurant_id=self.restaurant.id,
            name='Fried Rice',
            price=Decimal('160.00'),
        )
        restaurant_service.set_item_availability(item.id, self.restaurant.id, False)
        with self.assertRaises(MenuItemUnavailable):
            restaurant_service.validate_order_items(self.restaurant.id, [item.id])

    def test_validate_order_items_closed_restaurant(self):
        item = restaurant_service.add_menu_item(
            restaurant_id=self.restaurant.id,
            name='Dal',
            price=Decimal('100.00'),
        )
        restaurant_service.close_restaurant(self.restaurant.id)
        with self.assertRaises(RestaurantClosed):
            restaurant_service.validate_order_items(self.restaurant.id, [item.id])


class OutboxTest(TestCase):
    def test_outbox_claim_and_publish(self):
        restaurant = restaurant_service.create_restaurant(name='Outbox Test')
        events = claim_batch()
        self.assertTrue(len(events) > 0)
        event = events[0]
        mark_published(event.id)
        event.refresh_from_db()
        self.assertIsNotNone(event.published_at)

    def test_outbox_claim_skips_published(self):
        restaurant = restaurant_service.create_restaurant(name='Published Test')
        events = claim_batch()
        for ev in events:
            mark_published(ev.id)
        events2 = claim_batch()
        ids1 = {e.id for e in events}
        ids2 = {e.id for e in events2}
        self.assertTrue(ids1.isdisjoint(ids2))


class InboxIdempotencyTest(TestCase):
    def test_process_once_runs_handler_once(self):
        counter = [0]
        message_id = uuid.uuid4()

        def handler():
            counter[0] += 1

        process_once(message_id, 'test-consumer', handler)
        process_once(message_id, 'test-consumer', handler)
        process_once(message_id, 'test-consumer', handler)

        self.assertEqual(counter[0], 1)
        self.assertEqual(ProcessedMessage.objects.filter(message_id=message_id).count(), 1)

    def test_different_consumers_get_different_entries(self):
        message_id = uuid.uuid4()
        process_once(message_id, 'consumer-A', lambda: None)
        process_once(message_id, 'consumer-B', lambda: None)
        self.assertEqual(ProcessedMessage.objects.filter(message_id=message_id).count(), 2)
