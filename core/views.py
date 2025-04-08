from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, ProductForm, FarmForm
from django.core.paginator import Paginator  # Import Paginator
from django.views.decorators.http import require_POST
from .models import Product, Farm  # Import the Product and Farm models

def home(request):
    return render(request, 'core/home.html')

def about(request):
    return render(request, 'core/about.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')


### Add Products Feature ###
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user  # assuming your Product model has a foreign key to CustomUser
            product.save()
            messages.success(request, "Product added successfully!")
            return redirect('add_product')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()

    return render(request, 'core/add_product.html', {'form': form})

### Product Management Features ###
@login_required
def my_products(request):
    products = Product.objects.filter(farmer=request.user).order_by('-created_at')
    return render(request, 'core/my_products.html', {'products': products})

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('my_products')

@login_required
def update_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('my_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'core/update_product.html', {'form': form, 'product': product})


## Farm Management Features ##
@login_required
def add_farm(request):
    if request.method == 'POST':
        form = FarmForm(request.POST, request.FILES)
        if form.is_valid():
            farm = form.save(commit=False)
            farm.farmer = request.user
            farm.save()
            messages.success(request, "Farm registered successfully!")
            return redirect('farm_management')  # or redirect to 'add_farm' to reset form
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FarmForm()

    return render(request, 'core/add_farm.html', {'form': form})
### Farm view Feature ###
@login_required
def farm_management(request):
    farms = Farm.objects.filter(farmer=request.user)
    return render(request, 'core/farm_management.html', {'farms': farms})

### Update Farm Feature ###
@login_required
def update_farm(request, farm_id):
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)

    if request.method == 'POST':
        form = FarmForm(request.POST, request.FILES, instance=farm)
        if form.is_valid():
            form.save()
            messages.success(request, "Farm updated successfully.")
            return redirect('farm_management')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FarmForm(instance=farm)

    return render(request, 'core/update_farm.html', {'form': form, 'farm': farm})

### Delete Farm Feature ###
@login_required
@require_POST
def delete_farm(request, farm_id):
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)
    farm.delete()
    messages.success(request, "Farm deleted successfully.")
    return redirect('farm_management')



@login_required
def orders(request):
    return render(request, 'core/orders.html')





## Buyer  methods

@login_required
def browse_products(request):
    category = request.GET.get('category')
    search = request.GET.get('search')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.all()

    if category:
        products = products.filter(category__iexact=category)
    if search:
        products = products.filter(name__icontains=search)
    if min_price:
        products = products.filter(price_per_kg__gte=min_price)
    if max_price:
        products = products.filter(price_per_kg__lte=max_price)

    paginator = Paginator(products, 9)  # 9 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/browse_products.html', {'products': page_obj})