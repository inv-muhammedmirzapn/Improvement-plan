from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ReserveSerializer
from . import services

class ReserveStockView(APIView):
    def post(self, request, sku):
        s = ReserveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            r = services.reserve_stock(sku=sku, **s.validated_data)
        except services.StockNotFound:
            return Response({"error":"sku not found"}, status=status.HTTP_404_NOT_FOUND)
        except services.OutOfStock:
            return Response({"error":"out of stock"}, status=status.HTTP_400_BAD_REQUEST)
        except services.StockDiscontinued:
            return Response({"error":"Product Discontinued"}, status=status.HTTP_409_CONFLICT)
        except services.DuplicateOrder:
            return Response({"error":"Order reference already used"}, status=status.HTTP_409_CONFLICT)
        
        return Response(
            {"reservation_id" : str(r.id), "order_reference":r.order_reference, "quantity":r.quantity},
            status=status.HTTP_201_CREATED
        )