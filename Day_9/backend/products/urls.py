from django.urls import path
from .views import (
    ProductListCreateAPIView,
    ProductDetailAPIView,
    CategoryListAPIView,
    CheckProductAvailabilityAPIView,
)

urlpatterns = [
    path('products/', ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('products/<int:id>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('products/<int:id>/availability/', CheckProductAvailabilityAPIView.as_view(), name='product-availability'),
]
