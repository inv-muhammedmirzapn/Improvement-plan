from rest_framework import serializers


class ReserveSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    order_reference = serializers.CharField(max_length=50)