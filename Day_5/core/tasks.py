import requests
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .models import StockReservation


@shared_task(
    autoretry_for=(requests.RequestException,),
    retry_backoff=True, retry_jitter=True, max_retries=5,
)
def notify_wms(reservation_id: str) -> None:
    try:
        r = StockReservation.objects.select_related("stock").get(pk=reservation_id)
    except StockReservation.DoesNotExist:
        return  # deleted in the meantime; nothing to notify
    resp = requests.post(
        settings.WMS_WEBHOOK_URL,
        json={
            "event": "stock.reserved",
            "reservation_id": str(r.id),
            "sku": r.stock.sku,
            "quantity": r.quantity,
            "order_reference": r.order_reference,
        },
        headers={"Idempotency-Key": str(r.id)},  # safe under Celery retries
        timeout=5,
    )
    resp.raise_for_status()


@shared_task(max_retries=3, default_retry_delay=10)
def generate_packing_slip(reservation_id: str) -> str | None:
    from io import BytesIO
    from reportlab.pdfgen import canvas

    try:
        r = StockReservation.objects.select_related("stock").get(pk=reservation_id)
    except StockReservation.DoesNotExist:
        return None

    path = f"packing_slips/{r.order_reference}.pdf"
    if default_storage.exists(path):  # idempotent
        return path

    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 780, f"Packing Slip - Order {r.order_reference}")
    c.drawString(72, 760, f"SKU: {r.stock.sku}   Qty: {r.quantity}")
    reserved_at = timezone.localtime(r.created_at)
    c.drawString(72, 740, f"Reserved at: {reserved_at:%Y-%m-%d %H:%M:%S %Z}")
    c.save()
    return default_storage.save(path, ContentFile(buf.getvalue()))