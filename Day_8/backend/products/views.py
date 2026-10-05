from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Product
from .serializers import ProductSerializer


class ProductListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: List all products.
    Optional query params: category, search.
    POST: Create a new product.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.all()
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')

        if category and category.lower() != 'all':
            qs = qs.filter(category__iexact=category)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs


class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE a single product by ID.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'


class CheckProductAvailabilityAPIView(APIView):
    """
    GET: Simulate checking product availability in inventory.
    """
    def get(self, request, id):
        product = get_object_or_404(Product, id=id)
        is_available = product.stock > 0
        return Response({
            "productId": product.id,
            "title": product.title,
            "available": is_available,
            "stock": product.stock,
            "message": f"'{product.title}' is available with {product.stock} units in stock." if is_available else f"'{product.title}' is currently out of stock."
        }, status=status.HTTP_200_OK if is_available else status.HTTP_200_OK)
