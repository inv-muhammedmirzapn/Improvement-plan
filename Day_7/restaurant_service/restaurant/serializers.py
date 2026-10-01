"""
Restaurant Service serializers.
"""
from rest_framework import serializers

from .models import MenuItem, Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'description', 'address', 'status',
                  'max_active_orders', 'active_order_count', 'version',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at', 'active_order_count']


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'restaurant_id', 'name', 'description', 'price',
                  'is_available', 'version', 'created_at', 'updated_at']
        read_only_fields = ['id', 'restaurant_id', 'version', 'created_at', 'updated_at']


class CreateMenuItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='', allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class UpdateMenuItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class AvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class ValidateOrderItemsSerializer(serializers.Serializer):
    """Used by Customer BFF to validate restaurant+menu before order creation."""
    item_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class ReserveCapacitySerializer(serializers.Serializer):
    """Internal endpoint: reserve one active-order slot."""
    restaurant_id = serializers.UUIDField()


class CreateRestaurantSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='', allow_blank=True)
    address = serializers.CharField(required=False, default='', allow_blank=True)
    max_active_orders = serializers.IntegerField(required=False, default=20, min_value=1)
