# store/models.py
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        try:
            return self.image.url if self.image else ""
        except Exception:
            return ""


class SubCategory(models.Model):
    category = models.ForeignKey(Category, related_name="subcategories", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    image = models.ImageField(upload_to="subcategories/", blank=True, null=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    @property
    def image_url(self):
        try:
            return self.image.url if self.image else ""
        except Exception:
            return ""


class Size(models.Model):
    """Reusable unit records like GM, KG, PIECE, BOX, ML, LTR, PACK, etc."""
    name = models.CharField(max_length=30, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.abbreviation


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    sub_category = models.ForeignKey(
        SubCategory, related_name="products", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True)

    regular_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    size_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.PROTECT, null=True, blank=True)

    image = models.ImageField(upload_to="products/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    on_sale = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)

    # keep nullable for smooth migration; slug auto-fills on save
    slug = models.SlugField(max_length=200, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("store:product_detail", kwargs={"pk": self.pk})

    @property
    def image_url(self):
        try:
            return self.image.url if self.image else ""
        except Exception:
            return ""

    @property
    def display_price(self):
        """Use sale price when set, else regular price."""
        return self.sale_price if self.sale_price is not None else self.regular_price

    @property
    def size_display(self):
        if self.size and self.size_value is not None:
            val = int(self.size_value) if self.size_value == int(self.size_value) else self.size_value
            return f"{val} {self.size.abbreviation}"
        return ""

    def save(self, *args, **kwargs):
        # Auto-generate a unique slug if missing
        if not self.slug and self.name:
            base = slugify(self.name) or "product"
            slug = base
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    @property
    def total_price(self):
        # Sum as Decimal (keeps precision)
        return sum(
            (item.product.display_price or Decimal("0.00")) * item.quantity
            for item in self.items.all()
        )

    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_total_price(self):
        return (self.product.display_price or Decimal("0.00")) * self.quantity
