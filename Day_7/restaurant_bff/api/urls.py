from django.urls import path
from . import views

urlpatterns = [
    path('menu-items/', views.CreateMenuItemView.as_view(), name='restaurant-create-menu-item'),
    path('menu-items/<uuid:item_id>/', views.UpdateMenuItemView.as_view(), name='restaurant-update-menu-item'),
    path('menu-items/<uuid:item_id>/availability/', views.MenuItemAvailabilityView.as_view(), name='restaurant-item-availability'),
    path('orders/', views.RestaurantOrderListView.as_view(), name='restaurant-order-list'),
    path('orders/<uuid:order_id>/accept/', views.AcceptOrderView.as_view(), name='restaurant-accept-order'),
    path('orders/<uuid:order_id>/reject/', views.RejectOrderView.as_view(), name='restaurant-reject-order'),
    path('orders/<uuid:order_id>/preparing/', views.PreparingOrderView.as_view(), name='restaurant-preparing-order'),
    path('orders/<uuid:order_id>/ready/', views.ReadyOrderView.as_view(), name='restaurant-ready-order'),
    path('close/', views.CloseRestaurantView.as_view(), name='restaurant-close'),
]
