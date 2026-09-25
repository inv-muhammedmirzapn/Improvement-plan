from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Avg, Count, Max, Min, Sum
from .models import Category, Product
from .serializers import ProductSerializer


@api_view(["GET", "POST"])
def product_list(request):
    # GET: List products
    if request.method == "GET":
        category = request.query_params.get("category")
        min_price = request.query_params.get("min_price")
        not_category = request.query_params.get("not_category")
        ordering = request.query_params.get("ordering")
        
        products = Product.objects.all()
        if category:
            products = products.filter(category__name__icontains=category)
        if min_price:
            products = products.filter(price__gt=min_price)
        if not_category:
            products = products.exclude(category__name__icontains=not_category)
        if ordering in ["price", "-price", "quantity", "-quantity", "created_date", "-created_date"]:
            products = products.order_by(ordering)

        # Check for first or latest single product request
        fetch = request.query_params.get("fetch") or request.query_params.get("get")
        if fetch == "first":
            product = products.order_by("created_date").first()
            if not product:
                return Response({"error": "No product found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        elif fetch == "latest":
            product = products.order_by("-created_date").first()
            if not product:
                return Response({"error": "No product found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductSerializer(product)
            return Response(serializer.data)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    # POST: Add new product
    elif request.method == "POST":
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Product.MultipleObjectsReturned:
        return Response(
            {"error": "Multiple products returned for this ID"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # GET: View single product
    if request.method == "GET":
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    # PUT: Edit product
    elif request.method == "PUT":
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE: Delete product
    elif request.method == "DELETE":
        product.delete()
        return Response(
            {"message": "Product deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["GET"])
def product_values(request):
    # Returns dictionaries containing only name, price, and quantity
    data = Product.objects.values("name", "price", "quantity")
    return Response(list(data))


@api_view(["GET"])
def product_names(request):
    # Returns a flat list containing only product names
    names = Product.objects.values_list("name", flat=True)
    return Response(list(names))


@api_view(["GET"])
def category_stats(request):
    # Annotate each category with product count and average price
    stats = Category.objects.annotate(
        product_count=Count("products"),
        avg_price=Avg("products__price"),
    ).values("id", "name", "product_count", "avg_price")
    return Response(list(stats))


@api_view(["GET"])
def product_analytics(request):
    # Calculates store-wide product statistics using aggregate()
    stats = Product.objects.aggregate(
        total_quantity=Sum("quantity"),
        avg_price=Avg("price"),
        highest_price=Max("price"),
        lowest_price=Min("price"),
    )
    return Response(stats)
