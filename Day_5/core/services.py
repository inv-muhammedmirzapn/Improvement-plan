from django.db import IntegrityError, transaction
from django.db.models import F
from .models import ProductStock, StockReservation
from .tasks import notify_wms, generate_packing_slip


class StockNotFound(Exception): ...
class StockDiscontinued(Exception): ...
class OutOfStock(Exception): ...
class DuplicateOrder(Exception): ...


def reserve_stock(*, sku: str, quantity: int, order_reference: str) -> StockReservation:
    try:
        stock_id = ProductStock.objects.values_list("id", flat=True).get(sku=sku)
    except ProductStock.DoesNotExist:
        raise StockNotFound(sku)

    try:
        with transaction.atomic():
            # Single atomic statement: the availability check and decrement
            # happen together inside the database, under a row lock.
            #   UPDATE product_stock
            #      SET available_quantity = available_quantity - %s
            #    WHERE id = %s AND is_discontinued = 0 AND available_quantity >= %s
            updated = ProductStock.objects.filter(
                pk=stock_id,
                is_discontinued=False,
                available_quantity__gte=quantity,
            ).update(available_quantity=F("available_quantity") - quantity)

            if updated == 0:
                if ProductStock.objects.filter(pk=stock_id, is_discontinued=True).exists():
                    raise StockDiscontinued(sku)
                raise OutOfStock(sku)

            reservation = StockReservation.objects.create(
                stock_id=stock_id,
                quantity=quantity,
                order_reference=order_reference,
            )
            reservation_id = str(reservation.id)

            transaction.on_commit(lambda: notify_wms.delay(reservation_id), robust=True)
            transaction.on_commit(lambda: generate_packing_slip.delay(reservation_id), robust=True)
    except IntegrityError:
        # Duplicate order_reference. The atomic block already rolled back,
        # so the stock decrement is undone and no on_commit hooks fire.
        raise DuplicateOrder(order_reference)

    return reservation