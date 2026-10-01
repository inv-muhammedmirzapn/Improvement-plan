from django.urls import path
from . import views

urlpatterns = [
    path('restaurants/', views.RestaurantListView.as_view(), name='customer-restaurants'),
    path('restaurants/<uuid:restaurant_id>/menu/', views.RestaurantMenuView.as_view(), name='customer-menu'),
    path('restaurants/<uuid:restaurant_id>/orders/', views.PlaceOrderView.as_view(), name='customer-place-order'),
    path('orders/<uuid:order_id>/', views.OrderDetailView.as_view(), name='customer-order-detail'),
    path('orders/<uuid:order_id>/cancel/', views.CancelOrderView.as_view(), name='customer-order-cancel'),
]
