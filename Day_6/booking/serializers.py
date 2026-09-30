from django.conf import settings
from rest_framework import serializers

from .models import Booking, BookingSeat, Event, Payment, Seat


class BookSeatsRequestSerializer(serializers.Serializer):
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=getattr(settings, "MAX_SEATS_PER_BOOKING", 10),
    )
    idempotency_key = serializers.CharField(min_length=8, max_length=100)

    def validate_seat_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("seat_ids must not contain duplicates.")
        return value


class WebhookSerializer(serializers.Serializer):
    gateway_reference = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED"])


class PaymentSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(source="booking.id", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "booking_id", "gateway_reference", "amount", "status", "currency"]


class BookingSerializer(serializers.ModelSerializer):
    seat_ids = serializers.SerializerMethodField()
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "event", "status", "expires_at", "created_at", "seat_ids", "payment"]

    def get_seat_ids(self, obj):
        return sorted(
            str(s) for s in BookingSeat.objects.filter(booking=obj).values_list("seat_id", flat=True)
        )


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["id", "event", "seat_number", "status", "price"]


class EventSerializer(serializers.ModelSerializer):
    total_seats = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "name", "starts_at", "status", "total_seats", "available_seats"]

    def get_total_seats(self, obj):
        return obj.seats.count()

    def get_available_seats(self, obj):
        return obj.seats.filter(status=Seat.Status.AVAILABLE).count()
