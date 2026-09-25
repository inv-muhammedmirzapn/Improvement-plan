from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("products/values/", views.product_values, name="product_values"),
    path("products/names/", views.product_names, name="product_names"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/analytics/", views.product_analytics, name="product_analytics"),
    path("categories/stats/", views.category_stats, name="category_stats"),
]
