from django.urls import path
from .views import (
    ProductListCreateAPIView,
    ProductDetailAPIView,
    CheckProductAvailabilityAPIView,
)

urlpatterns = [
    path('products/', ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('products/<int:id>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('products/<int:id>/availability/', CheckProductAvailabilityAPIView.as_view(), name='product-availability'),
]
