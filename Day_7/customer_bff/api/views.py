"""
Customer BFF views.

The BFF aggregates data from Restaurant Service and Order Service.
It never owns business state. All writes go to the appropriate microservice.
Identity/authorization: customer_id is extracted from the JWT (simulated via header).
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import gateway
from .gateway import (
    ServiceConflict,
    ServiceNotFound,
    ServiceUnavailable,
    ServiceValidationError,
)
from .serializers import (
    CreateOrderRequestSerializer,
)

log = logging.getLogger(__name__)


def _get_customer_id(request):
    """
    In production this reads from the decoded JWT.
    The customer NEVER supplies their own customer_id in the body.
    """
    return request.headers.get('X-Customer-ID') or request.query_params.get('customer_id') or 1


def _unavailable():
    return Response(
        {'detail': 'Service temporarily unavailable. Please try again.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={'Retry-After': '2'},
    )


# ── GET /api/customer/restaurants/ ────────────────────────────────────────────

class RestaurantListView(APIView):
    def get(self, request):
        try:
            restaurants = gateway.get_restaurants()
        except ServiceUnavailable:
            return _unavailable()
        return Response(restaurants)


# ── GET /api/customer/restaurants/<restaurant_id>/menu/ ───────────────────────

class RestaurantMenuView(APIView):
    def get(self, request, restaurant_id):
        try:
            # Fetch restaurant info and menu in parallel (or sequentially for simplicity)
            restaurant = gateway.get_restaurant(restaurant_id)
            menu = gateway.get_menu(restaurant_id)
        except ServiceNotFound:
            return Response({'detail': 'Restaurant not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceUnavailable:
            return _unavailable()
        return Response({'restaurant': restaurant, 'menu': menu})


# ── POST /api/customer/restaurants/<restaurant_id>/orders/ ────────────────────

class PlaceOrderView(APIView):
    """
    Customer places an order. Workflow:
    1. Validate restaurant + menu items synchronously (Restaurant Service).
    2. Reserve capacity slot (Restaurant Service).
    3. Create order with price snapshot (Order Service).
    4. If Order Service fails, release the capacity slot.

    Idempotency: the client must supply a unique idempotency_key.
    Concurrent submissions with the same key return the same order.
    """
    def post(self, request, restaurant_id):
        customer_id = _get_customer_id(request)
        ser = CreateOrderRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        idempotency_key = ser.validated_data['idempotency_key']
        raw_items = ser.validated_data['items']
        item_ids = [str(i['menu_item_id']) for i in raw_items]

        # Step 1: Validate restaurant + menu items
        try:
            validated_items = gateway.validate_order_items(restaurant_id, item_ids)
        except ServiceNotFound as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()

        # Build price-snapshot items (merge quantity from request with price from restaurant service)
        qty_map = {str(i['menu_item_id']): i['quantity'] for i in raw_items}
        snapshot_items = [
            {
                'menu_item_id': str(item['id']),
                'item_name': item['name'],
                'unit_price': str(item['price']),
                'quantity': qty_map.get(str(item['id']), 1),
            }
            for item in validated_items
        ]

        # Step 2: Reserve capacity slot
        try:
            gateway.reserve_capacity(restaurant_id)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()

        # Step 3: Create order
        try:
            restaurant = gateway.get_restaurant(restaurant_id)
            order, created = gateway.create_order(
                customer_id=customer_id,
                restaurant_id=restaurant_id,
                restaurant_name=restaurant.get('name', ''),
                idempotency_key=idempotency_key,
                items=snapshot_items,
            )
        except ServiceValidationError as exc:
            # Idempotency conflict — release the capacity slot we just reserved
            gateway.release_capacity(restaurant_id)
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ServiceUnavailable:
            # Order Service down — release the capacity slot
            gateway.release_capacity(restaurant_id)
            return _unavailable()

        return Response(order, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ── GET /api/customer/orders/<order_id>/ ──────────────────────────────────────

class OrderDetailView(APIView):
    """
    Aggregated order view combining order data + restaurant/menu snapshot.
    Defines partial-failure behavior: if Restaurant Service is down, return
    order data with a degraded restaurant section.
    """
    def get(self, request, order_id):
        customer_id = _get_customer_id(request)

        # Fetch order from Order Service
        try:
            order = gateway.get_order(order_id, customer_id)
        except ServiceNotFound:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceUnavailable:
            return _unavailable()

        # Fetch restaurant info (graceful degradation on failure)
        restaurant = None
        try:
            restaurant = gateway.get_restaurant(order['restaurant_id'])
        except (ServiceNotFound, ServiceUnavailable):
            log.warning('OrderDetailView: could not fetch restaurant %s — degraded response',
                        order.get('restaurant_id'))

        # Build aggregated response (Frontend Friendly)
        aggregated = {
            'order': {
                'id': order['id'],
                'status': order['status'],
                'total_amount': order['total_amount'],
                'created_at': order['created_at'],
                'updated_at': order['updated_at'],
            },
            'restaurant': restaurant or {
                'id': order.get('restaurant_id'),
                'name': order.get('restaurant_name', 'Unknown'),
                'status': 'UNKNOWN',
            },
            'items': order.get('items', []),
            'status': order['status'],
        }
        return Response(aggregated)


# ── POST /api/customer/orders/<order_id>/cancel/ ──────────────────────────────

class CancelOrderView(APIView):
    def post(self, request, order_id):
        customer_id = _get_customer_id(request)
        try:
            order = gateway.cancel_order(order_id, customer_id)
        except ServiceNotFound:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ServiceUnavailable:
            return _unavailable()
        return Response(order)
