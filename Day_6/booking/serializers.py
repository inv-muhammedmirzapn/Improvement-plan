from django.conf import settings
from rest_framework import serializers

from .models import Booking, BookingSeat, Payment


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
