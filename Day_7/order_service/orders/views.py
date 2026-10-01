"""Order Service views."""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import (
    IdempotencyConflict,
    InvalidStateTransition,
    OrderNotCancellable,
    OrderNotFound,
    TemporaryDatabaseError,
)
from .models import Order
from .serializers import (
    CancelOrderSerializer,
    CreateOrderSerializer,
    OrderSerializer,
)
from .services import order as order_service

log = logging.getLogger(__name__)


def _busy():
    return Response(
        {'detail': 'Temporarily unavailable, please retry.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={'Retry-After': '1'},
    )


def _get_customer_id(request):
    """Extract customer_id from JWT (via BFF header). Never trust request body."""
    return request.headers.get('X-Customer-ID') or request.query_params.get('customer_id') or 1


def _get_restaurant_id(request):
    return request.headers.get('X-Restaurant-ID')


# ── Order creation ─────────────────────────────────────────────────────────────

class CreateOrderView(APIView):
    """Create a new order. Idempotent per idempotency_key."""
    def post(self, request):
        customer_id = _get_customer_id(request)
        ser = CreateOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            order, created = order_service.create_order(
                customer_id=int(customer_id),
                **ser.validated_data,
            )
        except IdempotencyConflict as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except TemporaryDatabaseError:
            return _busy()

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ── Customer-facing order views ────────────────────────────────────────────────

class CustomerOrderDetailView(APIView):
    """Fetch a single order for the authenticated customer."""
    def get(self, request, order_id):
        customer_id = _get_customer_id(request)
        try:
            order = order_service.get_order(order_id, customer_id=int(customer_id))
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


class CancelOrderView(APIView):
    """Customer cancels their order."""
    def post(self, request, order_id):
        customer_id = _get_customer_id(request)
        try:
            order = order_service.cancel_order(order_id, customer_id=int(customer_id))
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OrderNotCancellable as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except TemporaryDatabaseError:
            return _busy()
        return Response(OrderSerializer(order).data)


# ── Restaurant-facing order views ──────────────────────────────────────────────

class RestaurantOrderListView(APIView):
    """List all orders for the authenticated restaurant."""
    def get(self, request, restaurant_id):
        restaurant_id_header = _get_restaurant_id(request)
        if restaurant_id_header and str(restaurant_id_header) != str(restaurant_id):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        status_filter = request.query_params.get('status')
        orders = order_service.get_restaurant_orders(restaurant_id, status_filter=status_filter)
        return Response(OrderSerializer(orders, many=True).data)


class AcceptOrderView(APIView):
    """Restaurant accepts an order: PENDING → CONFIRMED."""
    def post(self, request, order_id):
        try:
            order = order_service.confirm_order(order_id)
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransition as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except TemporaryDatabaseError:
            return _busy()
        return Response(OrderSerializer(order).data)


class RejectOrderView(APIView):
    """Restaurant rejects an order: PENDING → REJECTED."""
    def post(self, request, order_id):
        try:
            order = order_service.reject_order(order_id)
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransition as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except TemporaryDatabaseError:
            return _busy()
        return Response(OrderSerializer(order).data)


class PreparingOrderView(APIView):
    """Restaurant marks order as PREPARING: CONFIRMED → PREPARING."""
    def post(self, request, order_id):
        try:
            order = order_service.start_preparing(order_id)
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransition as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except TemporaryDatabaseError:
            return _busy()
        return Response(OrderSerializer(order).data)


class ReadyOrderView(APIView):
    """Restaurant marks order as READY: PREPARING → READY."""
    def post(self, request, order_id):
        try:
            order = order_service.mark_ready(order_id)
        except OrderNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransition as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except TemporaryDatabaseError:
            return _busy()
        return Response(OrderSerializer(order).data)


# ── Internal endpoints ─────────────────────────────────────────────────────────

class InternalActiveOrderCountView(APIView):
    """Return active order count for a restaurant (for reconciliation)."""
    def get(self, request, restaurant_id):
        count = order_service.get_active_order_count(restaurant_id)
        return Response({'count': count})
