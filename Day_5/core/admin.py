from django.contrib import admin
from .models import ProductStock, StockReservation


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ("sku", "available_quantity", "is_discontinued", "id")
    list_filter = ("is_discontinued",)
    search_fields = ("sku", "id")


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ("order_reference", "stock", "quantity", "is_deleted", "created_at", "id")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("order_reference", "stock__sku")

    def get_queryset(self, request):
        # Allow viewing both active and soft-deleted reservations in admin
        return StockReservation.objects.with_deleted.all()
