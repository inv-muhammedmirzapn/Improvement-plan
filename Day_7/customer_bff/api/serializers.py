"""Customer BFF serializers."""
from rest_framework import serializers


class OrderItemRequestSerializer(serializers.Serializer):
    menu_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CreateOrderRequestSerializer(serializers.Serializer):
    """
    Customer-facing order request.
    Price is NOT accepted from the customer; it comes from Restaurant Service.
    idempotency_key must be supplied by the client (e.g., UUID generated on the device).
    """
    idempotency_key = serializers.CharField(max_length=100)
    items = OrderItemRequestSerializer(many=True, min_length=1)
