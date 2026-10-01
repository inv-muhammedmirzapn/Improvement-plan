from django.urls import path
from . import views

urlpatterns = [
    # Order creation (called by BFFs)
    path('orders/', views.CreateOrderView.as_view(), name='order-create'),

    # Customer-facing
    path('orders/<uuid:order_id>/', views.CustomerOrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:order_id>/cancel/', views.CancelOrderView.as_view(), name='order-cancel'),

    # Restaurant-facing
    path('restaurants/<uuid:restaurant_id>/orders/', views.RestaurantOrderListView.as_view(), name='restaurant-orders'),
    path('orders/<uuid:order_id>/accept/', views.AcceptOrderView.as_view(), name='order-accept'),
    path('orders/<uuid:order_id>/reject/', views.RejectOrderView.as_view(), name='order-reject'),
    path('orders/<uuid:order_id>/preparing/', views.PreparingOrderView.as_view(), name='order-preparing'),
    path('orders/<uuid:order_id>/ready/', views.ReadyOrderView.as_view(), name='order-ready'),

    # Internal
    path('internal/restaurants/<uuid:restaurant_id>/active-count/',
         views.InternalActiveOrderCountView.as_view(), name='internal-active-count'),
]
