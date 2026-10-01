"""
Order Service Models.

Owns:
  - Order (lifecycle, customer identity, restaurant reference)
  - OrderItem (price snapshot — copied from Restaurant Service at order time)
  - IdempotencyKey (deduplication of concurrent submissions)
  - OutboxEvent (transactional outbox)
  - ProcessedMessage (consumer-side inbox)

Key design decisions:
  - restaurant_id and item prices are denormalized into Order/OrderItem so
    Order Service never needs to read Restaurant Service's database.
  - version field on Order enables optimistic locking for concurrent transitions.
  - SELECT FOR UPDATE is used for safety-critical transitions (cancel, accept, reject).
"""
import uuid

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING'          # created, waiting for restaurant acceptance
        CONFIRMED = 'CONFIRMED'      # restaurant accepted
        PREPARING = 'PREPARING'      # restaurant started preparing
        READY = 'READY'              # ready for pickup/delivery
        COMPLETED = 'COMPLETED'      # terminal
        CANCELLED = 'CANCELLED'      # terminal
        REJECTED = 'REJECTED'        # terminal

    # Valid transitions: (from_status, to_status)
    ALLOWED_TRANSITIONS = {
        (Status.PENDING, Status.CONFIRMED),
        (Status.PENDING, Status.REJECTED),
        (Status.PENDING, Status.CANCELLED),
        (Status.CONFIRMED, Status.PREPARING),
        (Status.CONFIRMED, Status.CANCELLED),   # only if business rules permit
        (Status.PREPARING, Status.READY),
        (Status.READY, Status.COMPLETED),
        # Note: CANCELLED -> anything and COMPLETED -> anything are FORBIDDEN
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.IntegerField(db_index=True)
    restaurant_id = models.UUIDField(db_index=True)   # reference only, no FK
    restaurant_name = models.CharField(max_length=255, default='')  # snapshot
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Optimistic lock version
    version = models.PositiveIntegerField(default=0)
    # Idempotency key used for order creation deduplication
    idempotency_key = models.CharField(max_length=100, unique=True, db_index=True)
    # Hash of the original request body to detect key+different-body conflicts
    request_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer_id', 'status']),
            models.Index(fields=['restaurant_id', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def can_transition_to(self, new_status):
        return (self.status, new_status) in self.ALLOWED_TRANSITIONS

    def __str__(self):
        return f'Order {self.id} [{self.status}] customer={self.customer_id}'


class OrderItem(models.Model):
    """
    Price snapshot of each item at the time of order creation.
    Restaurant Service's current prices are NOT referenced after order creation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item_id = models.UUIDField()           # reference only, no FK cross-service
    item_name = models.CharField(max_length=255)  # snapshot
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'{self.item_name} x{self.quantity} = ₹{self.line_total}'


class OutboxEvent(models.Model):
    """Transactional outbox for Order Service."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_type = models.CharField(max_length=50)
    aggregate_id = models.UUIDField()
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['published_at', 'locked_until', 'created_at']),
        ]


class ProcessedMessage(models.Model):
    """Consumer-side inbox for idempotent event handling."""
    message_id = models.UUIDField()
    consumer = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['message_id', 'consumer'],
                name='order_unique_processed_message',
            ),
        ]
