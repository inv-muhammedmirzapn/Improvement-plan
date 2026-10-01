"""
Restaurant business logic service.

Concurrency strategy:
- Capacity slot reservation: SELECT FOR UPDATE on the Restaurant row.
  Application logic + DB-level row lock ensures only one worker can
  claim the final slot even with multiple Django instances / Celery workers.
- MenuItem availability: optimistic version check prevents stale updates.
- All business-state changes commit atomically with their outbox event.
"""
import logging

from django.db import transaction
from django.db.models import F

from ..db_retry import retry_on_db_error
from ..exceptions import (
    CapacityExceeded,
    InvalidStateTransition,
    MenuItemNotFound,
    RestaurantClosed,
    RestaurantNotFound,
)
from ..models import MenuItem, Restaurant
from . import outbox as outbox_service

log = logging.getLogger(__name__)


@retry_on_db_error()
def create_restaurant(name, description='', address='', max_active_orders=20):
    """Create a new restaurant and emit RestaurantCreated event."""
    with transaction.atomic():
        restaurant = Restaurant.objects.create(
            name=name,
            description=description,
            address=address,
            max_active_orders=max_active_orders,
        )
        outbox_service.append(
            aggregate_type='restaurant',
            aggregate_id=restaurant.id,
            event_type='RestaurantCreated',
            payload={
                'restaurant_id': str(restaurant.id),
                'name': restaurant.name,
                'status': restaurant.status,
                'max_active_orders': restaurant.max_active_orders,
            },
        )
    return restaurant


@retry_on_db_error()
def close_restaurant(restaurant_id):
    """
    Close a restaurant. Idempotent: if already CLOSED, return without error.
    Emits RestaurantClosed event to trigger Order Service reconciliation.
    """
    with transaction.atomic():
        restaurant = (
            Restaurant.objects.select_for_update()
            .filter(pk=restaurant_id)
            .first()
        )
        if restaurant is None:
            raise RestaurantNotFound(f'Restaurant {restaurant_id} not found.')
        if restaurant.status == Restaurant.Status.CLOSED:
            return restaurant  # idempotent
        restaurant.status = Restaurant.Status.CLOSED
        restaurant.version = F('version') + 1
        restaurant.save(update_fields=['status', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='restaurant',
            aggregate_id=restaurant.id,
            event_type='RestaurantClosed',
            payload={
                'restaurant_id': str(restaurant.id),
                'name': restaurant.name,
            },
        )
    return restaurant


@retry_on_db_error()
def reserve_capacity_slot(restaurant_id):
    """
    Reserve one active-order slot for the restaurant.

    Uses SELECT FOR UPDATE to serialize concurrent calls. Two workers racing
    for the final slot will queue up; the second will see active_order_count
    already at max and raise CapacityExceeded.

    This is the critical section that prevents the 'two workers accept
    concurrently with one slot remaining' race condition.
    """
    with transaction.atomic():
        restaurant = (
            Restaurant.objects.select_for_update()
            .filter(pk=restaurant_id)
            .first()
        )
        if restaurant is None:
            raise RestaurantNotFound(f'Restaurant {restaurant_id} not found.')
        if restaurant.status != Restaurant.Status.OPEN:
            raise RestaurantClosed(f'Restaurant {restaurant.name} is closed.')
        if restaurant.active_order_count >= restaurant.max_active_orders:
            raise CapacityExceeded(
                f'Restaurant {restaurant.name} has no remaining order slots '
                f'({restaurant.active_order_count}/{restaurant.max_active_orders}).'
            )
        Restaurant.objects.filter(pk=restaurant_id).update(
            active_order_count=F('active_order_count') + 1
        )
    return True


@retry_on_db_error()
def release_capacity_slot(restaurant_id):
    """
    Release one active-order slot. Idempotent: floor at 0.
    Called when an order is CANCELLED, REJECTED, COMPLETED, or READY.
    """
    with transaction.atomic():
        Restaurant.objects.filter(pk=restaurant_id, active_order_count__gt=0).update(
            active_order_count=F('active_order_count') - 1
        )


@retry_on_db_error()
def add_menu_item(restaurant_id, name, description='', price=None):
    """Add a menu item. Also syncs a MenuItemCreated event."""
    with transaction.atomic():
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
        if not restaurant:
            raise RestaurantNotFound(f'Restaurant {restaurant_id} not found.')
        item = MenuItem.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            price=price,
        )
        outbox_service.append(
            aggregate_type='menu_item',
            aggregate_id=item.id,
            event_type='MenuItemCreated',
            payload={
                'item_id': str(item.id),
                'restaurant_id': str(restaurant_id),
                'name': item.name,
                'price': str(item.price),
                'is_available': item.is_available,
            },
        )
    return item


@retry_on_db_error()
def update_menu_item(item_id, restaurant_id, **fields):
    """Update allowed menu item fields (name, description, price)."""
    with transaction.atomic():
        item = (
            MenuItem.objects.select_for_update()
            .filter(pk=item_id, restaurant_id=restaurant_id)
            .first()
        )
        if not item:
            raise MenuItemNotFound(f'MenuItem {item_id} not found.')
        allowed = {'name', 'description', 'price'}
        for k, v in fields.items():
            if k in allowed:
                setattr(item, k, v)
        item.version = F('version') + 1
        item.save()
        outbox_service.append(
            aggregate_type='menu_item',
            aggregate_id=item.id,
            event_type='MenuItemUpdated',
            payload={
                'item_id': str(item.id),
                'restaurant_id': str(restaurant_id),
                'name': item.name,
                'price': str(item.price),
                'is_available': item.is_available,
            },
        )
    return item


@retry_on_db_error()
def set_item_availability(item_id, restaurant_id, is_available):
    """
    Toggle menu item availability. Emits MenuItemAvailabilityChanged.

    Menu availability race (item goes unavailable while order is in flight):
    - The Order Service performs a synchronous validation call here BEFORE
      creating the order. If the item is unavailable at validation time the
      order is rejected immediately.
    - If the item becomes unavailable AFTER the synchronous check but BEFORE
      the order is committed, the Order Service will receive a stale
      MenuItemAvailabilityChanged event and must reconcile. The defined
      rule: an order already in PENDING/CONFIRMED is NOT retroactively
      cancelled due to availability changes. The restaurant can reject it.
    """
    with transaction.atomic():
        item = (
            MenuItem.objects.select_for_update()
            .filter(pk=item_id, restaurant_id=restaurant_id)
            .first()
        )
        if not item:
            raise MenuItemNotFound(f'MenuItem {item_id} not found.')
        if item.is_available == is_available:
            return item  # idempotent
        item.is_available = is_available
        item.version = F('version') + 1
        item.save(update_fields=['is_available', 'version', 'updated_at'])
        outbox_service.append(
            aggregate_type='menu_item',
            aggregate_id=item.id,
            event_type='MenuItemAvailabilityChanged',
            payload={
                'item_id': str(item.id),
                'restaurant_id': str(restaurant_id),
                'is_available': is_available,
            },
        )
    return item


def get_restaurant(restaurant_id):
    """Fetch restaurant by id (read-only, no lock)."""
    restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
    if not restaurant:
        raise RestaurantNotFound(f'Restaurant {restaurant_id} not found.')
    return restaurant


def get_menu_items(restaurant_id, available_only=False):
    """Fetch menu items for a restaurant."""
    qs = MenuItem.objects.filter(restaurant_id=restaurant_id)
    if available_only:
        qs = qs.filter(is_available=True)
    return qs.order_by('name')


def validate_order_items(restaurant_id, item_ids):
    """
    Synchronous validation used by Order Service (via BFF) before creating
    an order. Returns a list of {id, name, price} snapshots.
    Raises if restaurant is closed, capacity exceeded, or any item unavailable.
    """
    restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
    if not restaurant:
        raise RestaurantNotFound(f'Restaurant {restaurant_id} not found.')
    if restaurant.status != Restaurant.Status.OPEN:
        raise RestaurantClosed(f'Restaurant {restaurant.name} is closed.')

    items = MenuItem.objects.filter(pk__in=item_ids, restaurant_id=restaurant_id)
    found_ids = {str(i.id) for i in items}
    for iid in item_ids:
        if str(iid) not in found_ids:
            raise MenuItemNotFound(f'MenuItem {iid} not found in restaurant {restaurant_id}.')

    unavailable = [i for i in items if not i.is_available]
    if unavailable:
        from ..exceptions import MenuItemUnavailable
        raise MenuItemUnavailable(
            f'Items unavailable: {[str(i.id) for i in unavailable]}'
        )

    return [
        {'id': str(i.id), 'name': i.name, 'price': str(i.price)}
        for i in items
    ]
