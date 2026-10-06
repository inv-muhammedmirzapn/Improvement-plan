from django.core.management.base import BaseCommand
from products.models import Product

SAMPLE_PRODUCTS = [
    {
        "id": 1,
        "title": "Wireless Noise-Canceling Headphones",
        "price": 2499,
        "category": "Electronics",
        "rating": 4.8,
        "stock": 25,
        "thumbnail": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 2,
        "title": "Ergonomic Mechanical Keyboard",
        "price": 4299,
        "category": "Electronics",
        "rating": 4.6,
        "stock": 14,
        "thumbnail": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 3,
        "title": "Ultra-Wide Gaming Monitor 34\"",
        "price": 32999,
        "category": "Electronics",
        "rating": 4.9,
        "stock": 8,
        "thumbnail": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 4,
        "title": "Precision Wireless Gaming Mouse",
        "price": 1899,
        "category": "Electronics",
        "rating": 4.4,
        "stock": 42,
        "thumbnail": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 5,
        "title": "Pro Runner Air Cushioned Sneakers",
        "price": 5499,
        "category": "Footwear",
        "rating": 4.7,
        "stock": 19,
        "thumbnail": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 6,
        "title": "Classic Leather Oxford Shoes",
        "price": 6899,
        "category": "Footwear",
        "rating": 4.5,
        "stock": 0,
        "thumbnail": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 7,
        "title": "Waterproof Trail Hiking Boots",
        "price": 7999,
        "category": "Footwear",
        "rating": 4.6,
        "stock": 11,
        "thumbnail": "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 8,
        "title": "Smart Fitness Tracker Watch",
        "price": 3499,
        "category": "Fitness",
        "rating": 4.3,
        "stock": 30,
        "thumbnail": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 9,
        "title": "Adjustable Cast Iron Dumbbell Set",
        "price": 8999,
        "category": "Fitness",
        "rating": 4.8,
        "stock": 7,
        "thumbnail": "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 10,
        "title": "Non-Slip Eco Yoga Mat",
        "price": 1299,
        "category": "Fitness",
        "rating": 4.2,
        "stock": 50,
        "thumbnail": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 11,
        "title": "Minimalist Ceramic Coffee Dripper",
        "price": 1499,
        "category": "Home & Kitchen",
        "rating": 4.7,
        "stock": 22,
        "thumbnail": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 12,
        "title": "Stainless Steel Thermal Travel Mug",
        "price": 999,
        "category": "Home & Kitchen",
        "rating": 4.4,
        "stock": 35,
        "thumbnail": "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 13,
        "title": "Cast Iron Dutch Oven 5-Quart",
        "price": 5299,
        "category": "Home & Kitchen",
        "rating": 4.9,
        "stock": 0,
        "thumbnail": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 14,
        "title": "Polarized UV Protection Aviator Sunglasses",
        "price": 2199,
        "category": "Accessories",
        "rating": 4.5,
        "stock": 28,
        "thumbnail": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 15,
        "title": "Genuine Leather Bifold Wallet",
        "price": 1799,
        "category": "Accessories",
        "rating": 4.6,
        "stock": 16,
        "thumbnail": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 16,
        "title": "Water-Resistant Commuter Backpack 25L",
        "price": 3799,
        "category": "Accessories",
        "rating": 4.7,
        "stock": 18,
        "thumbnail": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 17,
        "title": "Portable Bluetooth Waterproof Speaker",
        "price": 3199,
        "category": "Audio",
        "rating": 4.6,
        "stock": 27,
        "thumbnail": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": 18,
        "title": "Studio Condenser USB Microphone",
        "price": 6499,
        "category": "Audio",
        "rating": 4.8,
        "stock": 12,
        "thumbnail": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"
    }
]


class Command(BaseCommand):
    help = "Seed database with initial sample products"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample products...")
        count = 0
        for item in SAMPLE_PRODUCTS:
            obj, created = Product.objects.update_or_create(
                id=item["id"],
                defaults={
                    "title": item["title"],
                    "price": item["price"],
                    "category": item["category"],
                    "rating": item["rating"],
                    "stock": item["stock"],
                    "thumbnail": item["thumbnail"],
                }
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} products!"))
