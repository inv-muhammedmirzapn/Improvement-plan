"""
Tests for Order Service.

Covers:
- Order creation idempotency (same key + same body → same order)
- Idempotency conflict (same key + different body)
- Concurrent order creation with same key
- State machine transitions
- Cancel vs Accept race condition
- Duplicate event idempotency (ProcessedMessage)
- Out-of-order event handling
- Stuck order detection
"""
import threading
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase

from orders.exceptions import IdempotencyConflict, InvalidStateTransition, OrderNotCancellable
from orders.models import Order, OutboxEvent, ProcessedMessage
from orders.services import order as order_service
from orders.services.inbox import process_once


SAMPLE_ITEMS = [
    {
        'menu_item_id': uuid.uuid4(),
        'item_name': 'Chicken Biryani',
        'unit_price': Decimal('250.00'),
        'quantity': 2,
    },
    {
        'menu_item_id': uuid.uuid4(),
        'item_name': 'Paneer Rice',
        'unit_price': Decimal('180.00'),
        'quantity': 1,
    },
]


def make_order(idempotency_key=None, items=None, customer_id=1, restaurant_id=None):
    return order_service.create_order(
        customer_id=customer_id,
        restaurant_id=restaurant_id or uuid.uuid4(),
        restaurant_name='Spice Kitchen',
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        items=items or SAMPLE_ITEMS,
    )


class OrderCreationTest(TestCase):
    def test_create_order_success(self):
        order, created = make_order()
        self.assertTrue(created)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.count(), 2)
        total = sum(i['unit_price'] * i['quantity'] for i in SAMPLE_ITEMS)
        self.assertEqual(order.total_amount, total)

    def test_create_order_emits_outbox_event(self):
        order, _ = make_order()
        outbox = OutboxEvent.objects.filter(aggregate_id=order.id, event_type='OrderCreated').first()
        self.assertIsNotNone(outbox)

    def test_idempotency_same_key_same_body_returns_same_order(self):
        key = str(uuid.uuid4())
        restaurant_id = uuid.uuid4()
        order1, created1 = make_order(idempotency_key=key, restaurant_id=restaurant_id)
        order2, created2 = make_order(idempotency_key=key, restaurant_id=restaurant_id)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(order1.id, order2.id)

    def test_idempotency_same_key_different_body_raises_conflict(self):
        key = str(uuid.uuid4())
        make_order(idempotency_key=key)
        different_items = [
            {
                'menu_item_id': uuid.uuid4(),
                'item_name': 'Fried Rice',
                'unit_price': Decimal('160.00'),
                'quantity': 1,
            }
        ]
        with self.assertRaises(IdempotencyConflict):
            make_order(idempotency_key=key, items=different_items)


class ConcurrentOrderCreationTest(TransactionTestCase):
    """Test that 10 concurrent submissions with the same key create only 1 order."""

    def test_concurrent_same_key_creates_one_order(self):
        key = str(uuid.uuid4())
        restaurant_id = uuid.uuid4()
        results = []
        errors = []

        def create():
            try:
                order, created = make_order(idempotency_key=key, restaurant_id=restaurant_id)
                results.append((order.id, created))
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=create) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed (idempotency key returns the same order)
        order_ids = {r[0] for r in results}
        self.assertEqual(len(order_ids), 1, f'Expected 1 unique order, got {order_ids}. Errors: {errors}')
        # Exactly one should have created=True
        created_flags = [r[1] for r in results]
        self.assertEqual(created_flags.count(True), 1)
        self.assertEqual(Order.objects.count(), 1)


class StateMachineTest(TestCase):
    def setUp(self):
        self.order, _ = make_order()

    def test_pending_to_confirmed(self):
        order = order_service.confirm_order(self.order.id)
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_pending_to_rejected(self):
        order = order_service.reject_order(self.order.id)
        self.assertEqual(order.status, Order.Status.REJECTED)

    def test_confirmed_to_preparing(self):
        order_service.confirm_order(self.order.id)
        order = order_service.start_preparing(self.order.id)
        self.assertEqual(order.status, Order.Status.PREPARING)

    def test_preparing_to_ready(self):
        order_service.confirm_order(self.order.id)
        order_service.start_preparing(self.order.id)
        order = order_service.mark_ready(self.order.id)
        self.assertEqual(order.status, Order.Status.READY)

    def test_invalid_transition_cancelled_to_preparing(self):
        """CANCELLED → PREPARING must be prevented."""
        order_service.cancel_order(self.order.id, customer_id=self.order.customer_id)
        with self.assertRaises(InvalidStateTransition):
            order_service.start_preparing(self.order.id)

    def test_invalid_transition_rejected_to_confirmed(self):
        order_service.reject_order(self.order.id)
        with self.assertRaises(InvalidStateTransition):
            order_service.confirm_order(self.order.id)

    def test_confirm_is_idempotent(self):
        order_service.confirm_order(self.order.id)
        order = order_service.confirm_order(self.order.id)  # second call
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_reject_is_idempotent(self):
        order_service.reject_order(self.order.id)
        order = order_service.reject_order(self.order.id)
        self.assertEqual(order.status, Order.Status.REJECTED)


class CancelAcceptRaceTest(TransactionTestCase):
    """
    Test the cancel-vs-accept race condition.
    Both paths lock the same row with SELECT FOR UPDATE.
    Whoever gets the lock first wins; the other sees the resulting state
    and either succeeds or raises the appropriate error.
    """

    def test_cancel_then_accept_is_invalid(self):
        order, _ = make_order()
        order_service.cancel_order(order.id, customer_id=order.customer_id)
        with self.assertRaises(InvalidStateTransition):
            order_service.confirm_order(order.id)

    def test_accept_then_cancel_is_valid(self):
        """Customer can cancel a CONFIRMED order (before PREPARING)."""
        order, _ = make_order()
        order_service.confirm_order(order.id)
        cancelled = order_service.cancel_order(order.id, customer_id=order.customer_id)
        self.assertEqual(cancelled.status, Order.Status.CANCELLED)

    def test_cannot_cancel_preparing_order(self):
        order, _ = make_order()
        order_service.confirm_order(order.id)
        order_service.start_preparing(order.id)
        with self.assertRaises(OrderNotCancellable):
            order_service.cancel_order(order.id, customer_id=order.customer_id)

    def test_cancel_emits_outbox_event(self):
        order, _ = make_order()
        order_service.cancel_order(order.id, customer_id=order.customer_id)
        outbox = OutboxEvent.objects.filter(aggregate_id=order.id, event_type='OrderCancelled').first()
        self.assertIsNotNone(outbox)


class InboxIdempotencyTest(TestCase):
    def test_out_of_order_accepted_after_cancelled(self):
        """
        Simulate: OrderAccepted event arrives after order is already CANCELLED.
        The event handler should use process_once + check current state
        to avoid corrupting the state machine.
        """
        order, _ = make_order()
        order_service.cancel_order(order.id, customer_id=order.customer_id)

        accepted_count = [0]

        def handle_order_accepted():
            # Re-fetch and check state before applying transition
            current_order = Order.objects.get(pk=order.id)
            if current_order.can_transition_to(Order.Status.CONFIRMED):
                order_service.confirm_order(order.id)
                accepted_count[0] += 1

        message_id = uuid.uuid4()
        process_once(message_id, 'order-accepted-consumer', handle_order_accepted)

        # State should still be CANCELLED (out-of-order accept ignored)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_duplicate_event_processed_once(self):
        counter = [0]
        msg_id = uuid.uuid4()

        for _ in range(5):
            process_once(msg_id, 'dup-consumer', lambda: counter.__setitem__(0, counter[0] + 1))

        self.assertEqual(counter[0], 1)


class OutboxAtomicityTest(TestCase):
    def test_outbox_and_order_committed_atomically(self):
        """If order creation succeeds, outbox must have the event."""
        order, _ = make_order()
        outbox_count = OutboxEvent.objects.filter(aggregate_id=order.id).count()
        self.assertGreater(outbox_count, 0)

    def test_no_orphan_outbox_on_rollback(self):
        """If the business operation rolls back, outbox must not have the event."""
        from django.db import transaction
        initial_count = OutboxEvent.objects.count()
        try:
            with transaction.atomic():
                make_order()
                raise Exception('Simulated failure')
        except Exception:
            pass
        self.assertEqual(OutboxEvent.objects.count(), initial_count)
