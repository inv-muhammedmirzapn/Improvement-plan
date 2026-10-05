from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.FloatField()
    rating = serializers.FloatField()

    class Meta:
        model = Product
        fields = ['id', 'title', 'price', 'category', 'rating', 'stock', 'thumbnail']
