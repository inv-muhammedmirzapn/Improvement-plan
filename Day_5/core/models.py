import uuid
from django.db import models
from django.db.models import Q


class ProductStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True)
    available_quantity = models.IntegerField(default=0)
    is_discontinued = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(available_quantity__gte=0),
                name="productstock_availability_qty_gte_0",
            )
        ]


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # Bulk soft delete, instead of real DELETE
        return self.update(is_deleted=True)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    @property
    def with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class StockReservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(ProductStock, on_delete=models.CASCADE, related_name="reservations")
    quantity = models.IntegerField()
    order_reference = models.CharField(max_length=50, unique=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = SoftDeleteManager()

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

    def hard_delete(self):
        super().delete()