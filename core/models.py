from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('farmer', 'Farmer'),
        ('buyer', 'Buyer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Grains', 'Grains'),
        ('Vegetables', 'Vegetables'),
        ('Fruits', 'Fruits'),
        ('Dairy', 'Dairy'),
    ]

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price_per_kg = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField()
    harvest_date = models.DateField()
    location = models.CharField(max_length=200, verbose_name="Farm Location", null=True)  # Add null
    is_organic = models.BooleanField(default=False)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.farmer.username}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Processing')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}kg of {self.product.name} by {self.buyer.username}"

class Farm(models.Model):
    SOIL_TYPES = [
        ('Loamy', 'Loamy'),
        ('Clay', 'Clay'),
        ('Sandy', 'Sandy'),
    ]

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    established_year = models.PositiveIntegerField()
    address = models.TextField()
    total_area = models.DecimalField(max_digits=10, decimal_places=2)
    primary_crop = models.CharField(max_length=100, blank=True)
    soil_type = models.CharField(max_length=20, choices=SOIL_TYPES, blank=True)
    description = models.TextField()
    is_organic_certified = models.BooleanField(default=False)
    is_fair_trade_certified = models.BooleanField(default=False)
    gallery_images = models.ImageField(upload_to='farm_gallery/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name