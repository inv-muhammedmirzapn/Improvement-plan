"""
Restaurant Service Models.

Owns:
  - Restaurant (status, capacity config)
  - MenuItem (price, availability)
  - OutboxEvent (transactional outbox)
  - ProcessedMessage (consumer-side inbox for idempotency)
"""
import uuid

from django.db import models


class Restaurant(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN'
        CLOSED = 'CLOSED'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    # How many simultaneous active orders this restaurant can handle
    max_active_orders = models.PositiveIntegerField(default=20)
    # Current count of active orders (PENDING + CONFIRMED + PREPARING)
    # Updated atomically with SELECT FOR UPDATE to prevent overshooting
    active_order_count = models.PositiveIntegerField(default=0)
    # Optimistic-lock version for stale-update protection
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.name} ({self.status})'


class MenuItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    # Optimistic-lock version
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
        ]

    def __str__(self):
        return f'{self.name} - ₹{self.price} ({"available" if self.is_available else "unavailable"})'


class OutboxEvent(models.Model):
    """
    Transactional outbox for Restaurant Service.
    Business state change + outbox write must be committed atomically.
    Relay picks unpublished events and pushes them to the broker.
    The same OutboxEvent.id is used as the broker message_id so consumers
    can de-duplicate using ProcessedMessage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_type = models.CharField(max_length=50)   # 'restaurant' | 'menu_item'
    aggregate_id = models.UUIDField()
    event_type = models.CharField(max_length=100)      # e.g. 'RestaurantCreated'
    payload = models.JSONField()
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Relay bookkeeping
    locked_until = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['published_at', 'locked_until', 'created_at']),
        ]

    def __str__(self):
        return f'{self.event_type} [{self.aggregate_id}] published={self.published_at is not None}'


class ProcessedMessage(models.Model):
    """
    Consumer-side inbox: makes at-least-once event delivery idempotent.
    Keyed on (message_id, consumer) so multiple consumers sharing the same
    broker don't interfere with each other.
    """
    message_id = models.UUIDField()
    consumer = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['message_id', 'consumer'],
                name='restaurant_unique_processed_message',
            ),
        ]
