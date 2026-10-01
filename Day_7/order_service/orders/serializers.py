"""Order Service serializers."""
from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item_id', 'item_name', 'unit_price', 'quantity', 'line_total']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_id', 'restaurant_id', 'restaurant_name',
            'status', 'total_amount', 'version',
            'idempotency_key', 'created_at', 'updated_at', 'items',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class CreateOrderItemSerializer(serializers.Serializer):
    menu_item_id = serializers.UUIDField()
    item_name = serializers.CharField(max_length=255)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CreateOrderSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    restaurant_name = serializers.CharField(max_length=255)
    idempotency_key = serializers.CharField(max_length=100)
    items = CreateOrderItemSerializer(many=True, min_length=1)


class OrderStatusTransitionSerializer(serializers.Serializer):
    """Generic serializer for state-transition commands that need no body."""
    pass


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
