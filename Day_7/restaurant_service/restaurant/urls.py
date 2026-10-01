from django.urls import path
from . import views

urlpatterns = [
    # Public read
    path('restaurants/', views.RestaurantListView.as_view(), name='restaurant-list'),
    path('restaurants/<uuid:restaurant_id>/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('restaurants/<uuid:restaurant_id>/menu/', views.MenuItemListView.as_view(), name='menu-list'),

    # Restaurant management
    path('restaurants/create/', views.CreateRestaurantView.as_view(), name='restaurant-create'),
    path('restaurants/<uuid:restaurant_id>/menu/add/', views.CreateMenuItemView.as_view(), name='menu-item-create'),
    path('restaurants/<uuid:restaurant_id>/menu/<uuid:item_id>/', views.UpdateMenuItemView.as_view(), name='menu-item-update'),
    path('restaurants/<uuid:restaurant_id>/menu/<uuid:item_id>/availability/', views.MenuItemAvailabilityView.as_view(), name='menu-item-availability'),
    path('restaurants/<uuid:restaurant_id>/close/', views.CloseRestaurantView.as_view(), name='restaurant-close'),

    # Internal endpoints used by BFFs / Order Service
    path('internal/restaurants/<uuid:restaurant_id>/validate-items/', views.ValidateOrderItemsView.as_view(), name='validate-items'),
    path('internal/restaurants/<uuid:restaurant_id>/reserve-capacity/', views.ReserveCapacityView.as_view(), name='reserve-capacity'),
    path('internal/restaurants/<uuid:restaurant_id>/release-capacity/', views.ReleaseCapacityView.as_view(), name='release-capacity'),
    path('internal/restaurants/<uuid:restaurant_id>/active-count/', views.InternalActiveOrderCountView.as_view(), name='active-count'),
]
