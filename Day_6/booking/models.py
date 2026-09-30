import uuid
from django.db import models


class Event(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"
        CANCELLED = "CANCELLED"
        CLOSED = "CLOSED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return f"{self.name} ({self.status})"


class Seat(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE"
        RESERVED = "RESERVED"
        SOLD = "SOLD"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=20)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.AVAILABLE)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "seat_number"], name="unique_event_seat_number"),
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"Event {self.event_id} - Seat {self.seat_number} ({self.status})"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT"
        CONFIRMED = "CONFIRMED"
        EXPIRED = "EXPIRED"
        CANCELLED = "CANCELLED"
        REFUND_REQUIRED = "REFUND_REQUIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING_PAYMENT)
    idempotency_key = models.CharField(max_length=100, unique=True)
    request_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"Booking {self.id} (User {self.user_id}, {self.status})"


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booking_seats")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="seat_bookings")
    active_seat = models.OneToOneField(
        Seat, null=True, blank=True, on_delete=models.PROTECT, related_name="active_hold"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["booking", "seat"], name="unique_booking_seat"),
        ]


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED"   # row created in booking tx, gateway not yet called
        PENDING = "PENDING"       # gateway accepted, waiting for webhook
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"
        EXPIRED = "EXPIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    gateway_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.INITIATED)
    currency = models.CharField(max_length=3, default="INR")
    gateway_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Payment {self.gateway_reference} - {self.amount} {self.currency} ({self.status})"


class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # also consumer-side message_id
    aggregate_id = models.UUIDField()
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # relay bookkeeping
    locked_until = models.DateTimeField(null=True, blank=True)  # lease / retry back-off
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["aggregate_id", "event_type"], name="unique_outbox_aggregate_event"),
        ]
        indexes = [
            models.Index(fields=["published_at", "locked_until", "created_at"]),
        ]


class ProcessedMessage(models.Model):
    """Consumer-side inbox: makes handling of at-least-once deliveries idempotent."""
    message_id = models.UUIDField()
    consumer = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["message_id", "consumer"], name="unique_processed_message"),
        ]
