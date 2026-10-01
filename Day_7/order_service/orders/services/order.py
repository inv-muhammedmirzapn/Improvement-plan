"""
Order business logic service.

Concurrency & idempotency strategy:
-  Order creation: idempotency_key is a unique DB constraint.
   Concurrent submissions with the same key race to INSERT; the loser gets
   IntegrityError and we return the already-created order.
   Same key + different body → IdempotencyConflict.

-  State transitions: SELECT FOR UPDATE on the Order row serializes all
   concurrent state changes. The state machine check prevents invalid
   transitions even under concurrent load.

-  Cancel vs Accept race: both paths SELECT FOR UPDATE on the same row.
   Whichever arrives first wins; the second sees the already-transitioned
   state and either no-ops or raises InvalidStateTransition.

-  Out-of-order events: every handler checks the current status before
   applying a transition. Stale events are silently ignored.
"""
import hashlib
import json
import logging

from django.db import IntegrityError, transaction
from django.db.models import F

from ..db_retry import retry_on_db_error
from ..exceptions import (
    IdempotencyConflict,
    InvalidStateTransition,
    OrderNotCancellable,
    OrderNotFound,
    TemporaryDatabaseError,
)
from ..models import Order, OrderItem
from . import outbox as outbox_service

log = logging.getLogger(__name__)


def _hash_request(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


@retry_on_db_error()
def create_order(
    customer_id,
    restaurant_id,
    restaurant_name,
    idempotency_key,
    items,          # list of {menu_item_id, item_name, unit_price, quantity}
):
    """
    Create an order atomically with an outbox event.

    Idempotency:
    - Same key + same body → return existing order (created=False).
    - Same key + different body → IdempotencyConflict.
    - Concurrent same key → DB unique constraint ensures only one insert
      succeeds; the loser reads the winner's row.

    items is a price-snapshot list from Restaurant Service; Order Service
    never reads Restaurant Service's DB.
    """
    request_data = {
        'customer_id': customer_id,
        'restaurant_id': str(restaurant_id),
        'items': [
            {
                'menu_item_id': str(i['menu_item_id']),
                'quantity': i['quantity'],
            }
            for i in items
        ],
    }
    request_hash = _hash_request(request_data)

    # Check for existing order with this idempotency key BEFORE trying to insert
    existing = Order.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.request_hash != request_hash:
            raise IdempotencyConflict(
                f'Idempotency key {idempotency_key!r} was already used with a different request body.'
            )
        return existing, False

    # Calculate total
    total_amount = sum(
        item['unit_price'] * item['quantity'] for item in items
    )

    try:
        with transaction.atomic():
            order = Order.objects.create(
                customer_id=customer_id,
                restaurant_id=restaurant_id,
                restaurant_name=restaurant_name,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                total_amount=total_amount,
                status=Order.Status.PENDING,
            )
            for item in items:
                line_total = item['unit_price'] * item['quantity']
                OrderItem.objects.create(
                    order=order,
                    menu_item_id=item['menu_item_id'],
                    item_name=item['item_name'],
                    unit_price=item['unit_price'],
                    quantity=item['quantity'],
                    line_total=line_total,
                )
            outbox_service.append(
                aggregate_type='order',
                aggregate_id=order.id,
                event_type='OrderCreated',
                payload={
                    'order_id': str(order.id),
                    'customer_id': order.customer_id,
                    'restaurant_id': str(order.restaurant_id),
                    'restaurant_name': order.restaurant_name,
                    'total_amount': str(order.total_amount),
                    'items': [
                        {
                            'menu_item_id': str(i.menu_item_id),
                            'item_name': i.item_name,
                            'unit_price': str(i.unit_price),
                            'quantity': i.quantity,
                            'line_total': str(i.line_total),
                        }
                        for i in order.items.all()
                    ],
                },
            )
    except IntegrityError:
        # Concurrent submission with same key: read the winner's row
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict(
                    f'Idempotency key {idempotency_key!r} already used with different body.'
                )
            return existing, False
        raise TemporaryDatabaseError('Unexpected IntegrityError during order creation.')

    return order, True


@retry_on_db_error()
def confirm_order(order_id):
    """
    Transition PENDING → CONFIRMED.
    Called when restaurant accepts. SELECT FOR UPDATE prevents cancel/accept race.
    """
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(pk=order_id)
            .first()
        )
        if not order:
            raise OrderNotFound(f'Order {order_id} not found.')
        if order.status == Order.Status.CONFIRMED:
            return order  # idempotent
        if not order.can_transition_to(Order.Status.CONFIRMED):
            raise InvalidStateTransition(
                f'Cannot transition from {order.status} to CONFIRMED.',
                from_status=order.status,
                to_status=Order.Status.CONFIRMED,
            )
        order.status = Order.Status.CONFIRMED
        order.version = F('version') + 1
        order.save(update_fields=['status', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='order',
            aggregate_id=order.id,
            event_type='OrderAccepted',
            payload={
                'order_id': str(order.id),
                'restaurant_id': str(order.restaurant_id),
                'customer_id': order.customer_id,
            },
        )
    return order


@retry_on_db_error()
def reject_order(order_id):
    """
    Transition PENDING → REJECTED.
    Restaurant rejected the order.
    """
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(pk=order_id)
            .first()
        )
        if not order:
            raise OrderNotFound(f'Order {order_id} not found.')
        if order.status == Order.Status.REJECTED:
            return order  # idempotent
        if not order.can_transition_to(Order.Status.REJECTED):
            raise InvalidStateTransition(
                f'Cannot transition from {order.status} to REJECTED.',
                from_status=order.status,
                to_status=Order.Status.REJECTED,
            )
        order.status = Order.Status.REJECTED
        order.version = F('version') + 1
        order.save(update_fields=['status', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='order',
            aggregate_id=order.id,
            event_type='OrderRejected',
            payload={
                'order_id': str(order.id),
                'restaurant_id': str(order.restaurant_id),
                'customer_id': order.customer_id,
            },
        )
    return order


@retry_on_db_error()
def cancel_order(order_id, customer_id):
    """
    Customer cancels order. Allowed from PENDING or CONFIRMED.

    Cancel vs Accept race:
    - Both paths hold SELECT FOR UPDATE on the same Order row.
    - If cancel arrives first: order becomes CANCELLED; accept then sees
      CANCELLED and raises InvalidStateTransition (CANCELLED → CONFIRMED not allowed).
    - If accept arrives first: order becomes CONFIRMED; cancel then succeeds
      because CONFIRMED → CANCELLED is allowed (if still CONFIRMED, not PREPARING).
    """
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(pk=order_id, customer_id=customer_id)
            .first()
        )
        if not order:
            raise OrderNotFound(f'Order {order_id} not found for customer {customer_id}.')
        if order.status == Order.Status.CANCELLED:
            return order  # idempotent
        if order.status in (Order.Status.PREPARING, Order.Status.READY,
                             Order.Status.COMPLETED, Order.Status.REJECTED):
            raise OrderNotCancellable(
                f'Order {order_id} cannot be cancelled in status {order.status}.'
            )
        order.status = Order.Status.CANCELLED
        order.version = F('version') + 1
        order.save(update_fields=['status', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='order',
            aggregate_id=order.id,
            event_type='OrderCancelled',
            payload={
                'order_id': str(order.id),
                'restaurant_id': str(order.restaurant_id),
                'customer_id': order.customer_id,
                'cancelled_by': 'customer',
            },
        )
    return order


@retry_on_db_error()
def start_preparing(order_id):
    """CONFIRMED → PREPARING."""
    return _simple_transition(order_id, Order.Status.CONFIRMED, Order.Status.PREPARING, 'OrderPreparing')


@retry_on_db_error()
def mark_ready(order_id):
    """PREPARING → READY."""
    return _simple_transition(order_id, Order.Status.PREPARING, Order.Status.READY, 'OrderReady')


@retry_on_db_error()
def mark_completed(order_id):
    """READY → COMPLETED."""
    return _simple_transition(order_id, Order.Status.READY, Order.Status.COMPLETED, 'OrderCompleted')


def _simple_transition(order_id, from_status, to_status, event_type):
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(pk=order_id)
            .first()
        )
        if not order:
            raise OrderNotFound(f'Order {order_id} not found.')
        if order.status == to_status:
            return order  # idempotent
        if not order.can_transition_to(to_status):
            raise InvalidStateTransition(
                f'Cannot transition from {order.status} to {to_status}.',
                from_status=order.status,
                to_status=to_status,
            )
        order.status = to_status
        order.version = F('version') + 1
        order.save(update_fields=['status', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='order',
            aggregate_id=order.id,
            event_type=event_type,
            payload={
                'order_id': str(order.id),
                'restaurant_id': str(order.restaurant_id),
                'customer_id': order.customer_id,
                'status': to_status,
            },
        )
    return order


def get_order(order_id, customer_id=None):
    qs = Order.objects.prefetch_related('items').filter(pk=order_id)
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    order = qs.first()
    if not order:
        raise OrderNotFound(f'Order {order_id} not found.')
    return order


def get_restaurant_orders(restaurant_id, status_filter=None):
    qs = Order.objects.prefetch_related('items').filter(restaurant_id=restaurant_id)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs.order_by('-created_at')


def get_active_order_count(restaurant_id):
    """Return the count of active orders for reconciliation endpoint."""
    active_statuses = [Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PREPARING]
    return Order.objects.filter(restaurant_id=restaurant_id, status__in=active_statuses).count()
