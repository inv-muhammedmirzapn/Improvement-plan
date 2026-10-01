"""Restaurant BFF serializers."""
from rest_framework import serializers


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
