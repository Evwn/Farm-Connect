from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import uuid

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

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Escrow', 'In Escrow'),
        ('Released', 'Released'),
        ('Refunded', 'Refunded'),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Processing')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    escrow_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Order #{self.id} - {self.product.name}"

class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Funded', 'Funded'),
        ('Waiting_Confirmation', 'Waiting Confirmation'),
        ('Confirmed', 'Confirmed'),
        ('Awaiting_Release', 'Awaiting Release'),
        ('Released', 'Released'),
        ('Refunded', 'Refunded'),
        ('Disputed', 'Disputed'),
    ]

    DISPUTE_STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Under_Review', 'Under Review'),
        ('Seller_Responded', 'Seller Responded'),
        ('Mediation', 'In Mediation'),
        ('Resolved_Seller', 'Resolved in Favor of Seller'),
        ('Resolved_Buyer', 'Resolved in Favor of Buyer'),
        ('Resolved_Compromise', 'Resolved with Compromise'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='escrow_transaction')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.DateTimeField(null=True, blank=True)
    confirmation_time = models.DateTimeField(null=True, blank=True)
    scheduled_release_time = models.DateTimeField(null=True, blank=True)
    dispute_reason = models.TextField(blank=True)
    dispute_status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, blank=True, null=True)
    dispute_date = models.DateTimeField(null=True, blank=True)
    dispute_resolved_date = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolution_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Escrow for Order {self.order.id} - {self.status}"

class DisputeResponse(models.Model):
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='dispute_responses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    attachments = models.FileField(upload_to='dispute_attachments/', blank=True, null=True)

    def __str__(self):
        return f"Dispute Response for Escrow {self.escrow.id} by {self.user.username}"

class DisputeMessage(models.Model):
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='dispute_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_admin_message = models.BooleanField(default=False)
    attachments = models.FileField(upload_to='dispute_messages/', blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message in Dispute {self.escrow.id} by {self.sender.username}"

class DisputeTimeline(models.Model):
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='dispute_timeline')
    action = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status_change = models.CharField(max_length=20, choices=EscrowTransaction.DISPUTE_STATUS_CHOICES, blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Timeline Entry for Dispute {self.escrow.id}: {self.action}"

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

class SellerVerification(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected')
    ]

    seller = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verification')
    full_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=50)
    id_document = models.ImageField(upload_to='verification/id_documents/')
    business_name = models.CharField(max_length=100)
    business_address = models.TextField()
    business_location = models.CharField(max_length=100)
    business_permit = models.ImageField(upload_to='verification/business_permits/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_sellers')
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.seller.username} - {self.status}"

    class Meta:
        verbose_name = 'Seller Verification'
        verbose_name_plural = 'Seller Verifications'