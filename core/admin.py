from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Product, Farm, Order

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Product) 
admin.site.register(Farm)
admin.site.register(Order)  # Register the Order model in the admin site