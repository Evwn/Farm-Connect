from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Product, Farm, Order

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

class ProductForm(forms.ModelForm):
    is_organic = forms.BooleanField(required=False, label="Organic Certified")
    location = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter farm location'}))

    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'price_per_kg',
            'description',
            'stock_quantity',
            'harvest_date',
            'location',  # New field
            'is_organic',
            'image',
        ]
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
        }
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['product', 'quantity']
class FarmForm(forms.ModelForm):
    is_organic_certified = forms.BooleanField(required=False)
    is_fair_trade_certified = forms.BooleanField(required=False)

    class Meta:
        model = Farm
        fields = [
            'name', 'established_year', 'address',
            'total_area', 'primary_crop', 'soil_type',
            'description', 'is_organic_certified', 'is_fair_trade_certified', 'gallery_images'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'established_year': forms.NumberInput(attrs={'min': 1900, 'max': 2100}),
        }