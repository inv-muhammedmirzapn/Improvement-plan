import hashlib
import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import (
    EventNotFound,
    EventNotOpen,
    IdempotencyConflict,
    PaymentNotFound,
    SeatsUnavailable,
    TemporaryDatabaseError,
)
from .models import Booking, Payment
from .serializers import BookingSerializer, BookSeatsRequestSerializer, PaymentSerializer, WebhookSerializer
from .services import booking as booking_service
from .services import payments as payment_service


def _busy():
    return Response(
        {"detail": "Temporarily unavailable, retry."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": "1"},
    )


class BookSeatsView(APIView):
    def post(self, request, event_id):
        ser = BookSeatsRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = (
            request.user.id
            if (request.user and request.user.is_authenticated)
            else (request.data.get("user_id") or 1)
        )
        try:
            booking, created = booking_service.create_booking(
                user_id=user_id,
                event_id=event_id,
                seat_ids=ser.validated_data["seat_ids"],
                idempotency_key=ser.validated_data["idempotency_key"],
            )
        except EventNotFound:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        except EventNotOpen:
            return Response({"detail": "Event is not open for booking."}, status=status.HTTP_409_CONFLICT)
        except SeatsUnavailable as exc:
            return Response({"detail": str(exc), "seat_ids": exc.seat_ids}, status=status.HTTP_409_CONFLICT)
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except TemporaryDatabaseError:
            return _busy()

        booking = Booking.objects.select_related("payment").get(pk=booking.pk)
        # Same body for the original and every replay; only the status code differs.
        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BookingDetailView(APIView):
    def get(self, request, booking_id):
        user_id = (
            request.user.id
            if (request.user and request.user.is_authenticated)
            else (request.query_params.get("user_id") or 1)
        )
        booking = (
            Booking.objects.select_related("payment")
            .filter(pk=booking_id, user_id=user_id)
            .first()
        )
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookingSerializer(booking).data)


class PaymentDetailView(APIView):
    def get(self, request, reference):
        payment = Payment.objects.filter(gateway_reference=reference).first()
        if payment is None and len(reference) == 36:
            payment = Payment.objects.filter(pk=reference).first()
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)


def verify_signature(body: bytes, signature: str) -> bool:
    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "test-webhook-secret")
    if not secret:
        return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


class PaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]  # authenticated by HMAC signature instead

    def post(self, request):
        raw = request.body  # read raw bytes before DRF parses the stream
        signature = request.headers.get("X-Signature", "")
        # If running in DEBUG mode and no signature provided, allow for easier local testing
        if not getattr(settings, "DEBUG", False) or signature:
            if not verify_signature(raw, signature):
                return Response({"detail": "Bad signature."}, status=status.HTTP_401_UNAUTHORIZED)

        ser = WebhookSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            outcome = payment_service.process_payment_webhook(
                gateway_reference=ser.validated_data["gateway_reference"],
                status=ser.validated_data["status"],
            )
        except PaymentNotFound:
            return Response({"detail": "Unknown reference."}, status=status.HTTP_404_NOT_FOUND)
        except TemporaryDatabaseError:
            return _busy()  # 5xx => gateway retries the webhook
        return Response({"result": outcome}, status=status.HTTP_200_OK)  # 200 for first delivery and duplicates