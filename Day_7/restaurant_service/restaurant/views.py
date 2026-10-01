"""
Restaurant Service views.

Internal-facing APIs consumed by BFFs. No public customer-facing endpoints here.
Authorization: the BFF propagates X-Restaurant-ID and X-Role headers.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import (
    BrokerTemporaryError,
    CapacityExceeded,
    InvalidStateTransition,
    MenuItemNotFound,
    MenuItemUnavailable,
    RestaurantClosed,
    RestaurantNotFound,
    TemporaryDatabaseError,
)
from .models import MenuItem, Restaurant
from .serializers import (
    AvailabilitySerializer,
    CreateMenuItemSerializer,
    CreateRestaurantSerializer,
    MenuItemSerializer,
    RestaurantSerializer,
    UpdateMenuItemSerializer,
    ValidateOrderItemsSerializer,
)
from .services import restaurant as restaurant_service

log = logging.getLogger(__name__)


def _busy():
    return Response(
        {'detail': 'Temporarily unavailable, please retry.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={'Retry-After': '1'},
    )


def _get_restaurant_id_from_header(request):
    """
    Extract the authenticated restaurant ID from the request header.
    The BFF sets this after verifying the JWT. Never trust the body.
    """
    return request.headers.get('X-Restaurant-ID')


# ── Public read endpoints ──────────────────────────────────────────────────────

class RestaurantListView(APIView):
    """List all open restaurants."""
    def get(self, request):
        restaurants = Restaurant.objects.all().order_by('name')
        return Response(RestaurantSerializer(restaurants, many=True).data)


class RestaurantDetailView(APIView):
    """Fetch a single restaurant."""
    def get(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
        if not restaurant:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(RestaurantSerializer(restaurant).data)


class MenuItemListView(APIView):
    """List menu items for a restaurant."""
    def get(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
        if not restaurant:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        available_only = request.query_params.get('available_only', 'false').lower() == 'true'
        items = restaurant_service.get_menu_items(restaurant_id, available_only=available_only)
        return Response(MenuItemSerializer(items, many=True).data)


# ── Restaurant management endpoints (Restaurant BFF only) ─────────────────────

class CreateRestaurantView(APIView):
    """Create a new restaurant."""
    def post(self, request):
        ser = CreateRestaurantSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            restaurant = restaurant_service.create_restaurant(**ser.validated_data)
        except TemporaryDatabaseError:
            return _busy()
        return Response(RestaurantSerializer(restaurant).data, status=status.HTTP_201_CREATED)


class CreateMenuItemView(APIView):
    """Add a menu item to a restaurant."""
    def post(self, request, restaurant_id):
        restaurant_id_header = _get_restaurant_id_from_header(request)
        if restaurant_id_header and str(restaurant_id_header) != str(restaurant_id):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = CreateMenuItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = restaurant_service.add_menu_item(
                restaurant_id=restaurant_id,
                **ser.validated_data,
            )
        except RestaurantNotFound:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        except TemporaryDatabaseError:
            return _busy()
        return Response(MenuItemSerializer(item).data, status=status.HTTP_201_CREATED)


class UpdateMenuItemView(APIView):
    """Update menu item fields (name, description, price)."""
    def patch(self, request, restaurant_id, item_id):
        restaurant_id_header = _get_restaurant_id_from_header(request)
        if restaurant_id_header and str(restaurant_id_header) != str(restaurant_id):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = UpdateMenuItemSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            item = restaurant_service.update_menu_item(
                item_id=item_id,
                restaurant_id=restaurant_id,
                **ser.validated_data,
            )
        except MenuItemNotFound:
            return Response({'detail': 'MenuItem not found.'}, status=status.HTTP_404_NOT_FOUND)
        except TemporaryDatabaseError:
            return _busy()
        return Response(MenuItemSerializer(item).data)


class MenuItemAvailabilityView(APIView):
    """Toggle availability of a menu item."""
    def post(self, request, restaurant_id, item_id):
        restaurant_id_header = _get_restaurant_id_from_header(request)
        if restaurant_id_header and str(restaurant_id_header) != str(restaurant_id):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = AvailabilitySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = restaurant_service.set_item_availability(
                item_id=item_id,
                restaurant_id=restaurant_id,
                is_available=ser.validated_data['is_available'],
            )
        except MenuItemNotFound:
            return Response({'detail': 'MenuItem not found.'}, status=status.HTTP_404_NOT_FOUND)
        except TemporaryDatabaseError:
            return _busy()
        return Response(MenuItemSerializer(item).data)


class CloseRestaurantView(APIView):
    """Close the restaurant. Idempotent."""
    def post(self, request, restaurant_id):
        restaurant_id_header = _get_restaurant_id_from_header(request)
        if restaurant_id_header and str(restaurant_id_header) != str(restaurant_id):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            restaurant = restaurant_service.close_restaurant(restaurant_id)
        except RestaurantNotFound:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        except TemporaryDatabaseError:
            return _busy()
        return Response(RestaurantSerializer(restaurant).data)


# ── Internal endpoints (called by Order Service / BFF) ────────────────────────

class ValidateOrderItemsView(APIView):
    """
    Synchronous validation: BFF calls this before creating an order.
    Returns price snapshot of all requested items.
    """
    def post(self, request, restaurant_id):
        ser = ValidateOrderItemsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            items = restaurant_service.validate_order_items(
                restaurant_id=restaurant_id,
                item_ids=ser.validated_data['item_ids'],
            )
        except RestaurantNotFound:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        except RestaurantClosed as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except MenuItemNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except MenuItemUnavailable as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({'items': items})


class ReserveCapacityView(APIView):
    """
    Reserve one active-order slot.
    Called synchronously by Order Service when it creates a PENDING order.
    """
    def post(self, request, restaurant_id):
        try:
            restaurant_service.reserve_capacity_slot(restaurant_id)
        except RestaurantNotFound:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        except RestaurantClosed as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except CapacityExceeded as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except TemporaryDatabaseError:
            return _busy()
        return Response({'reserved': True})


class ReleaseCapacityView(APIView):
    """
    Release one active-order slot. Idempotent.
    Called when an order reaches a terminal state (CANCELLED, REJECTED, COMPLETED).
    """
    def post(self, request, restaurant_id):
        try:
            restaurant_service.release_capacity_slot(restaurant_id)
        except TemporaryDatabaseError:
            return _busy()
        return Response({'released': True})


class InternalActiveOrderCountView(APIView):
    """
    Return current active_order_count for reconciliation by Order Service.
    """
    def get(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(pk=restaurant_id).values('active_order_count').first()
        if not restaurant:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'count': restaurant['active_order_count']})
