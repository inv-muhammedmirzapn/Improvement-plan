from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Product(models.Model):
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    rating = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        default=4.0
    )
    stock = models.PositiveIntegerField(default=0)
    thumbnail = models.URLField(max_length=1000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.title} (₹{self.price})"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "price": float(self.price),
            "category": self.category,
            "rating": float(self.rating),
            "stock": self.stock,
            "thumbnail": self.thumbnail,
        }
