from django.urls import path
from .views import ReserveStockView

urlpatterns = [
    path("api/stock/<str:sku>/reserve/", ReserveStockView.as_view(), name="reserve-stock"),
]