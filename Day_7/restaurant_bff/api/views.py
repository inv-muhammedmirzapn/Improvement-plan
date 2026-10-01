"""
Restaurant BFF views.

All state transitions are authorized by verifying the X-Restaurant-ID header
(set by the BFF after JWT validation) matches the restaurant being operated on.
Core business logic lives in the microservices, not here.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import gateway
from .gateway import ServiceConflict, ServiceForbidden, ServiceNotFound, ServiceUnavailable
from .serializers import (
    AvailabilitySerializer,
    CreateMenuItemSerializer,
    UpdateMenuItemSerializer,
)

log = logging.getLogger(__name__)


def _get_restaurant_id(request):
    """Extract authenticated restaurant_id from JWT (via header in real deployment)."""
    return request.headers.get('X-Restaurant-ID') or request.query_params.get('restaurant_id')


def _unavailable():
    return Response(
        {'detail': 'Service temporarily unavailable.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={'Retry-After': '2'},
    )


# ── POST /api/restaurant/menu-items/ ──────────────────────────────────────────

class CreateMenuItemView(APIView):
    def post(self, request):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        ser = CreateMenuItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = gateway.create_menu_item(
                restaurant_id=restaurant_id,
                **ser.validated_data,
            )
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceUnavailable:
            return _unavailable()
        return Response(item, status=status.HTTP_201_CREATED)


# ── PATCH /api/restaurant/menu-items/<item_id>/ ───────────────────────────────

class UpdateMenuItemView(APIView):
    def patch(self, request, item_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        ser = UpdateMenuItemSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            item = gateway.update_menu_item(
                restaurant_id=restaurant_id,
                item_id=item_id,
                **ser.validated_data,
            )
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceForbidden as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ServiceUnavailable:
            return _unavailable()
        return Response(item)


# ── POST /api/restaurant/menu-items/<item_id>/availability/ ───────────────────

class MenuItemAvailabilityView(APIView):
    def post(self, request, item_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        ser = AvailabilitySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = gateway.set_item_availability(
                restaurant_id=restaurant_id,
                item_id=item_id,
                is_available=ser.validated_data['is_available'],
            )
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceUnavailable:
            return _unavailable()
        return Response(item)


# ── GET /api/restaurant/orders/ ───────────────────────────────────────────────

class RestaurantOrderListView(APIView):
    def get(self, request):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        status_filter = request.query_params.get('status')
        try:
            orders = gateway.get_restaurant_orders(restaurant_id, status_filter=status_filter)
        except ServiceUnavailable:
            return _unavailable()
        return Response(orders)


# ── POST /api/restaurant/orders/<order_id>/accept/ ────────────────────────────

class AcceptOrderView(APIView):
    def post(self, request, order_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = gateway.accept_order(restaurant_id, order_id)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()
        return Response(order)


# ── POST /api/restaurant/orders/<order_id>/reject/ ────────────────────────────

class RejectOrderView(APIView):
    def post(self, request, order_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = gateway.reject_order(restaurant_id, order_id)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()
        return Response(order)


# ── POST /api/restaurant/orders/<order_id>/preparing/ ─────────────────────────

class PreparingOrderView(APIView):
    def post(self, request, order_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = gateway.start_preparing(restaurant_id, order_id)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()
        return Response(order)


# ── POST /api/restaurant/orders/<order_id>/ready/ ─────────────────────────────

class ReadyOrderView(APIView):
    def post(self, request, order_id):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = gateway.mark_ready(restaurant_id, order_id)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()
        return Response(order)


# ── POST /api/restaurant/close/ ───────────────────────────────────────────────

class CloseRestaurantView(APIView):
    def post(self, request):
        restaurant_id = _get_restaurant_id(request)
        if not restaurant_id:
            return Response({'detail': 'Restaurant authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            restaurant = gateway.close_restaurant(restaurant_id)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceUnavailable:
            return _unavailable()
        return Response(restaurant)
