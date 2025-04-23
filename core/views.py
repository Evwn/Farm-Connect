from decimal import Decimal  # Add this at the top
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .forms import CustomUserCreationForm, ProductForm, FarmForm, SellerVerificationForm
from django.db.models import Q, Sum  # Import Q and Sum for complex queries and aggregations
from django.core.paginator import Paginator  # Import Paginator
from django.http import JsonResponse, HttpResponse
import json  # Import json for handling JSON data
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # Import csrf_exempt
from .models import Product, Farm, Order, EscrowTransaction, DisputeResponse, DisputeMessage, DisputeTimeline, SellerVerification
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from .payment_gateways import PayPalGateway, PaystackGateway, SkrillGateway
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_authenticated and user.is_staff

def home(request):
    return render(request, 'core/home.html')

def about(request):
    return render(request, 'core/about.html')

def register(request):
    # Handle registration
    if request.method == 'POST' and 'email' in request.POST:  # Registration form submit
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '🎉 Registration successful! Welcome to FarmConnect')
            return redirect('dashboard')
        else:
            errors = [f"{field.replace('_', ' ').title()}: {error}" 
                     for field, errors in form.errors.items() 
                     for error in errors]
            messages.error(request, '<br>• '.join([''] + errors)[4:])
    
    # Handle login
    elif request.method == 'POST' and 'password' in request.POST:  # Login form submit
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, '👋 Welcome back! Redirecting to dashboard...')
            return redirect('dashboard')
        else:
            messages.error(request, '''
                ⚠️ Login Failed!<br>
                Please check:
                <ul class="text-start">
                    <li>Correct username</li>
                    <li>Valid password</li>
                    <li>Caps Lock status</li>
                </ul>
            ''')
    
    else:
        messages.get_messages(request).used = True  # Clear existing messages
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def dashboard(request):
    context = {}

    if request.user.role == 'farmer':
        # For farmers: Show stats for their products and orders
        total_harvested = Product.objects.filter(farmer=request.user).aggregate(total_stock=Sum('stock_quantity'))['total_stock'] or 0
        total_sold = Order.objects.filter(product__farmer=request.user, status='Completed').aggregate(total_sales=Sum('quantity'))['total_sales'] or 0
        current_harvest = total_harvested - total_sold  # Remaining stock available for sale

        # Add data to context for the farmer's dashboard
        context['current_harvest'] = current_harvest
        context['total_sold'] = total_sold
        context['total_orders'] = Order.objects.filter(product__farmer=request.user).count()

    elif request.user.role == 'buyer':
        # For buyers: Show stats for their orders with completed escrow payment
        total_orders = Order.objects.filter(
            buyer=request.user,
            payment_status__in=['In Escrow', 'Released']
        ).count()
        
        pending_orders = Order.objects.filter(
            buyer=request.user, 
            status='Pending',
            payment_status__in=['In Escrow', 'Released']
        ).count()
        
        completed_orders = Order.objects.filter(
            buyer=request.user, 
            status='Completed',
            payment_status__in=['In Escrow', 'Released']
        ).count()

        # Add data to context for the buyer's dashboard
        context['total_orders'] = total_orders
        context['pending_orders'] = pending_orders
        context['completed_orders'] = completed_orders

    return render(request, 'core/dashboard.html', context)


### Add Products Feature ###
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
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

def update_product(request, product_id):
    # Get the product to update
    product = get_object_or_404(Product, id=product_id, farmer=request.user)

    if request.method == 'POST':
        # Create a form instance with the submitted data and product instance
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully!")
            return redirect('my_products')  # Redirect back to the list of products
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # If it's a GET request, create the form with the existing product data
        form = ProductForm(instance=product)

    return render(request, 'core/update_product.html', {'form': form, 'product': product})

@login_required
@require_POST
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('my_products')

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

def update_farm(request, farm_id):
    # Get the farm to update
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)

    if request.method == 'POST':
        # Create a form instance with the submitted data and farm instance
        form = FarmForm(request.POST, request.FILES, instance=farm)
        if form.is_valid():
            form.save()
            messages.success(request, "Farm updated successfully!")
            return redirect('farm_management')  # Redirect back to the list of farms
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # If it's a GET request, create the form with the existing farm data
        form = FarmForm(instance=farm)

    return render(request, 'core/update_farm.html', {'form': form, 'farm': farm})

# Delete Farm Feature
@login_required
@require_POST
def delete_farm(request, farm_id):
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)
    farm.delete()
    messages.success(request, "Farm deleted successfully.")
    return redirect('farm_management')

@login_required
def orders(request):
    status_filter = request.GET.get('status', 'all')
    orders = Order.objects.filter(product__farmer=request.user)
    
    if status_filter != 'all':
        if status_filter == 'refunded':
            # For refunded orders, check both status and payment_status
            orders = orders.filter(
                Q(status='Refunded') | 
                Q(payment_status='Refunded')
            )
        else:
            orders = orders.filter(status=status_filter.capitalize())
    
    status_counts = {
        'all': Order.objects.filter(product__farmer=request.user).count(),
        'pending': Order.objects.filter(product__farmer=request.user, status='Pending').count(),
        'processing': Order.objects.filter(product__farmer=request.user, status='Processing').count(),
        'shipped': Order.objects.filter(product__farmer=request.user, status='Shipped').count(),
        'completed': Order.objects.filter(product__farmer=request.user, status='Completed').count(),
        'cancelled': Order.objects.filter(product__farmer=request.user, status='Cancelled').count(),
        'refunded': Order.objects.filter(
            product__farmer=request.user
        ).filter(
            Q(status='Refunded') | 
            Q(payment_status='Refunded')
        ).count(),
    }

    context = {
        'orders': orders.order_by('-created_at'),
        'status_filter': status_filter,
        'status_counts': status_counts
    }
    return render(request, 'core/orders.html', context)

@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id, product__farmer=request.user)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        # Set completed_at timestamp when status is changed to Completed
        if new_status == 'Completed':
            order.completed_at = timezone.now()
        # Handle refund when order is cancelled
        elif new_status == 'Cancelled' and order.escrow_transaction:
            order.escrow_transaction.status = 'Refunded'
            order.escrow_transaction.save()
            order.payment_status = 'Refunded'
            order.save()
            messages.success(request, f"Order #{order.id} cancelled and payment refunded")
            return JsonResponse({'success': True})
        order.save()
        messages.success(request, f"Order #{order.id} status updated to {new_status}")
        return JsonResponse({'success': True})
    else:
        messages.error(request, "Invalid status update")
        return JsonResponse({'success': False, 'message': 'Invalid status update'})
    
    return redirect('orders')


### Buyer Features ###

# View products for buyers
@login_required
def browse_products(request):
    products = Product.objects.all()
    
    # Show pending orders that are waiting for escrow payment
    pending_orders = Order.objects.filter(
        buyer=request.user, 
        status='Pending',
        payment_status='Pending'
    )
    
    # Add category choices to context
    product_categories = Product.CATEGORY_CHOICES
    cart_total = sum(order.total_price for order in pending_orders)
    
    context = {
        'products': products,
        'pending_orders': pending_orders,
        'product_categories': product_categories,
        'cart_total': cart_total
    }
    return render(request, 'core/browse_products.html', context)
@login_required
def browse_farms(request):
    # Fetch all farms
    farms = Farm.objects.all()

    # Context to pass to the template
    context = {
        'farms': farms,
    }

    return render(request, 'core/browse_farms.html', context)
@login_required
def farm_detail(request, farm_id):
    # Fetch the specific farm by its ID
    farm = get_object_or_404(Farm, id=farm_id)
    
    context = {
        'farm': farm,
    }

    return render(request, 'core/farm_detail.html', context)

# Order Product functionality (This replaces the old Add to Cart functionality)
@login_required
@csrf_exempt  
@require_POST
def order_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            raise ValueError("Quantity must be at least 1kg")
            
        if quantity > product.stock_quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity}kg available'
            }, status=400)

        # Create order with Pending status
        order = Order.objects.create(
            buyer=request.user,
            product=product,
            quantity=quantity,
            total_price=quantity * product.price_per_kg,
            status='Pending'  # Changed to Pending
        )
        
        # Create escrow transaction
        escrow = EscrowTransaction.objects.create(
            order=order,
            amount=order.total_price,
            status='Pending'
        )
        
        product.stock_quantity -= quantity
        product.save()

        return JsonResponse({
            'success': True,
            'total_price': float(order.total_price),
            'new_stock': product.stock_quantity,
            'redirect_url': reverse('escrow_payment', kwargs={'order_id': order.id})
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

## submit order ##
@login_required
@require_POST
def submit_order(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity'))
        
        product = get_object_or_404(Product, id=product_id)
        total_price = product.price_per_kg * quantity
        
        # Create the order
        order = Order.objects.create(
            buyer=request.user,
            product=product,
            quantity=quantity,
            total_price=total_price,
            status='Pending',
            payment_status='Pending'
        )
        
        # Create escrow transaction
        escrow = EscrowTransaction.objects.create(
            order=order,
            amount=total_price,
            status='Pending'
        )
        
        # Update product stock
        product.stock_quantity -= quantity
        product.save()
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'escrow_id': str(order.escrow_id),
            'amount': str(total_price)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def escrow_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'paypal':
            # Initialize PayPal payment
            paypal = PayPalGateway()
            result = paypal.create_payment(order)
            logger.info(f"PayPal payment creation result: {result}")
            
            if result['success']:
                # Store PayPal order ID in session
                paypal_order_id = result.get('payment_id')
                if paypal_order_id:
                    request.session['paypal_order_id'] = paypal_order_id
                    logger.info(f"Stored PayPal order ID in session: {paypal_order_id}")
                    return redirect(result['approval_url'])
                else:
                    logger.error("No PayPal order ID returned")
                    messages.error(request, "Error creating PayPal payment. Please try again.")
            else:
                logger.error(f"PayPal payment creation failed: {result.get('error', 'Unknown error')}")
                messages.error(request, f"PayPal Error: {result.get('error', 'Unknown error')}")
        
        elif payment_method == 'paystack':
            # Initialize Paystack payment
            paystack = PaystackGateway()
            callback_url = request.build_absolute_uri(reverse('paystack_callback', kwargs={'order_id': order.id}))
            
            result = paystack.create_transaction(order, callback_url)
            
            if result['success']:
                # Store reference in session for later use
                request.session['paystack_reference'] = result['reference']
                return redirect(result['authorization_url'])
            else:
                messages.error(request, f"Paystack Error: {result.get('error', 'Unknown error')}")
        
        elif payment_method == 'skrill':
            # Initialize Skrill payment
            skrill = SkrillGateway()
            result = skrill.create_payment(order)
            
            if result['success']:
                # Render a form that will auto-submit to Skrill
                return render(request, 'core/skrill_payment.html', {
                    'payment_url': result['payment_url'],
                    'payment_data': result['payment_data']
                })
            else:
                messages.error(request, f"Skrill Error: {result.get('error', 'Unknown error')}")
        
        else:
            messages.error(request, "Invalid payment method selected")
    
    return render(request, 'core/escrow_payment.html', {
        'order': order,
        'escrow': escrow
    })

@login_required
def paypal_success(request, order_id):
    """Handle successful PayPal payment"""
    try:
        order = Order.objects.get(id=order_id)
        if order.buyer != request.user:
            messages.error(request, "You are not authorized to view this order.")
            return redirect('dashboard')
        
        # Get the token and PayerID from the request
        token = request.GET.get('token')
        payer_id = request.GET.get('PayerID')
        
        if not token or not payer_id:
            messages.error(request, "Invalid PayPal response.")
            return redirect('order_detail', order_id=order.id)
        
        # Execute the payment
        paypal = PayPalGateway()
        result = paypal.execute_payment(token)
        
        if result['success']:
            # Update order and escrow status
            order.payment_status = 'In Escrow'
            order.save()
            
            escrow = order.escrow_transaction
            escrow.status = 'Funded'
            escrow.save()
            
            messages.success(request, "Payment successful! Your order is now in escrow.")
            return redirect('order_detail', order_id=order.id)
        else:
            messages.error(request, f"Payment execution failed: {result.get('error', 'Unknown error')}")
            return redirect('order_detail', order_id=order.id)
            
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('dashboard')
    except Exception as e:
        logger.error(f"Error processing PayPal success: {str(e)}")
        messages.error(request, "An error occurred while processing your payment.")
        return redirect('dashboard')

@login_required
def paypal_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    messages.warning(request, "PayPal payment was cancelled")
    
    # Clear session data
    if 'paypal_order_id' in request.session:
        del request.session['paypal_order_id']
    
    # Render the cancel template
    return render(request, 'core/paypal_cancel.html', {
        'order': order
    })

@login_required
def paystack_callback(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    reference = request.GET.get('reference')
    
    # Verify reference matches what we stored
    if reference != request.session.get('paystack_reference'):
        messages.error(request, "Payment verification failed")
        return redirect('order_detail', order_id=order.id)
    
    # Verify the transaction
    paystack = PaystackGateway()
    result = paystack.verify_transaction(reference)
    
    if result['success']:
        # Update escrow status
        escrow = order.escrow_transaction
        escrow.status = 'Funded'
        escrow.payment_reference = result['transaction_id']
        escrow.save()
        
        # Update order payment status
        order.payment_status = 'In Escrow'
        order.save()

        messages.success(request, 'Payment successful! Your funds are now in escrow.')
    else:
        messages.error(request, f"Payment failed: {result.get('error', 'Unknown error')}")
    
    # Clear session data
    if 'paystack_reference' in request.session:
        del request.session['paystack_reference']
    
    return redirect('order_detail', order_id=order.id)

@csrf_exempt
def skrill_status(request):
    """Handle Skrill payment status notifications"""
    if request.method == 'POST':
        # Verify the payment
        skrill = SkrillGateway()
        result = skrill.verify_payment(request.POST)
        
        if result['success']:
            order_id = result['order_id']
            order = get_object_or_404(Order, id=order_id)
            
            # Update escrow status
            escrow = order.escrow_transaction
            escrow.status = 'Funded'
            escrow.payment_reference = result['transaction_id']
            escrow.save()
            
            # Update order payment status
            order.payment_status = 'In Escrow'
            order.save()
            
            # Send email notification to buyer
            # This would be implemented in a real system
        
        # Always return OK to Skrill
        return HttpResponse("OK")
    
    return HttpResponse("Method not allowed", status=405)

@login_required
def release_escrow(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    # Check if user is the farmer (seller)
    if request.user != order.product.farmer:
        messages.error(request, 'Only the seller can release escrow funds for this order.')
        return redirect('order_detail', order_id=order.id)
    
    if order.status == 'Completed' and escrow.status == 'Funded':
        escrow.status = 'Released'
        escrow.release_date = timezone.now()
        escrow.save()
        
        order.payment_status = 'Released'
        order.save()

        messages.success(request, 'Escrow funds have been released to the farmer.')
    else:
        messages.error(request, 'Cannot release escrow funds. Order must be completed first.')
    
    return redirect('order_detail', order_id=order.id)

@login_required
def dispute_escrow(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    if request.method == 'POST':
        dispute_reason = request.POST.get('dispute_reason')
        if dispute_reason:
            # Update escrow status
            escrow.status = 'Disputed'
            escrow.dispute_reason = dispute_reason
            escrow.dispute_status = 'Pending'
            escrow.dispute_date = timezone.now()
            escrow.save()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                escrow=escrow,
                action='Dispute Filed',
                description=f'Buyer filed a dispute: {dispute_reason}',
                actor=request.user,
                status_change='Pending'
            )
            
            messages.success(request, 'Dispute has been filed. Our team will review it shortly.')
        else:
            messages.error(request, 'Please provide a reason for the dispute.')
    
    return redirect('dispute_detail', order_id=order_id)

@login_required
def dispute_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    # Check if user has permission to view
    if not (request.user == order.buyer or request.user == order.product.farmer or request.user.is_staff):
        messages.error(request, 'You do not have permission to view this dispute.')
        return redirect('dashboard')
    
    dispute_messages = escrow.dispute_messages.all()
    dispute_timeline = escrow.dispute_timeline.all()
    dispute_responses = escrow.dispute_responses.all()
    
    if request.method == 'POST':
        message = request.POST.get('message')
        attachment = request.FILES.get('attachment')
        
        if message:
            # Only mark as admin message if user is an actual administrator
            is_admin = request.user.is_authenticated and request.user.is_staff and request.user.is_superuser
            
            new_message = DisputeMessage.objects.create(
                escrow=escrow,
                sender=request.user,
                message=message,
                is_admin_message=is_admin,
                attachments=attachment
            )
            
            # Create timeline entry for the message
            DisputeTimeline.objects.create(
                escrow=escrow,
                action='Message Sent',
                description=f"Message sent by {'Admin' if is_admin else request.user.username}",
                actor=request.user
            )
            
            messages.success(request, 'Message sent successfully.')
    
    context = {
        'order': order,
        'escrow': escrow,
        'dispute_messages': dispute_messages,
        'dispute_timeline': dispute_timeline,
        'dispute_responses': dispute_responses,
        'is_admin': request.user.is_staff,
        'is_seller': request.user == order.product.farmer,
        'is_buyer': request.user == order.buyer
    }
    
    return render(request, 'core/dispute_detail.html', context)

@login_required
def seller_dispute_response(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    # Check if user is the seller
    if request.user != order.product.farmer:
        messages.error(request, 'Only the seller can respond to this dispute.')
        return redirect('dispute_detail', order_id=order_id)
    
    if request.method == 'POST':
        response = request.POST.get('response')
        attachment = request.FILES.get('attachment')
        
        if response:
            # Create seller's response
            DisputeResponse.objects.create(
                escrow=escrow,
                user=request.user,
                response=response,
                attachments=attachment
            )
            
            # Update dispute status
            escrow.dispute_status = 'Seller_Responded'
            escrow.save()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                escrow=escrow,
                action='Seller Response',
                description='Seller has responded to the dispute',
                actor=request.user,
                status_change='Seller_Responded'
            )
            
            messages.success(request, 'Your response has been recorded.')
            
    return redirect('dispute_detail', order_id=order_id)

@login_required
@user_passes_test(is_admin)
def admin_dispute_resolution(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    escrow = get_object_or_404(EscrowTransaction, order=order)
    
    if request.method == 'POST':
        resolution_type = request.POST.get('resolution_type')
        resolution_notes = request.POST.get('resolution_notes')
        resolution_amount = request.POST.get('resolution_amount')
        
        if resolution_type and resolution_notes:
            # Update escrow status based on resolution
            escrow.dispute_status = resolution_type
            escrow.resolution_notes = resolution_notes
            escrow.dispute_resolved_date = timezone.now()
            
            if resolution_amount:
                escrow.resolution_amount = float(resolution_amount)
            
            if resolution_type == 'Resolved_Seller':
                escrow.status = 'Released'
                order.status = 'Completed'
            elif resolution_type == 'Resolved_Buyer':
                escrow.status = 'Refunded'
                order.status = 'Refunded'
                order.payment_status = 'Refunded'
            elif resolution_type == 'Resolved_Compromise':
                escrow.status = 'Released'
                order.status = 'Completed'
            
            escrow.save()
            order.save()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                escrow=escrow,
                action='Dispute Resolved',
                description=f'Admin resolved the dispute: {resolution_notes}',
                actor=request.user,
                status_change=resolution_type
            )
            
            messages.success(request, 'Dispute has been resolved.')
            
    return redirect('dispute_detail', order_id=order_id)

@login_required
def dispute_list(request):
    # For admin: show all disputes
    # For users: show only their disputes
    if request.user.is_staff:
        disputes = EscrowTransaction.objects.filter(status='Disputed')
    else:
        disputes = EscrowTransaction.objects.filter(
            Q(status='Disputed') & 
            (Q(order__buyer=request.user) | Q(order__product__farmer=request.user))
        )
    
    context = {
        'disputes': disputes,
        'is_admin': request.user.is_staff
    }
    
    return render(request, 'core/dispute_list.html', context)

@login_required
def order_detail(request, order_id):
    # Get the order or return 404 if it doesn't exist
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user has permission to view the order
    if request.user != order.buyer and request.user != order.product.farmer:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('dashboard')
    
    # Try to get the escrow transaction, but don't raise 404 if it doesn't exist
    try:
        escrow = order.escrow_transaction
    except EscrowTransaction.DoesNotExist:
        # Create a new escrow transaction if one doesn't exist
        escrow = EscrowTransaction.objects.create(
            order=order,
            amount=order.total_price,
            status='Pending'
        )
        messages.info(request, 'An escrow transaction was created for this order.')
    
    return render(request, 'core/order_detail.html', {
        'order': order,
        'escrow': escrow
    })

# Order history view (for the buyer)
@login_required
def order_history(request):
    # Show all orders for the buyer, regardless of payment status
    orders = Order.objects.filter(
        buyer=request.user
    ).select_related('product').order_by('-created_at')
    
    context = {
        'orders': orders
    }
    return render(request, 'core/order_history.html', context)

# My Purchases function for buyers
@login_required
def my_purchases(request):
    # Show orders with released or refunded payments for the buyer
    orders = Order.objects.filter(
        buyer=request.user,
        payment_status__in=['Released', 'Refunded']
    ).select_related('product', 'escrow_transaction').order_by('-created_at')
    
    # Debug information to help troubleshoot
    print(f"Total orders with released/refunded payments: {orders.count()}")
    
    context = {
        'orders': orders
    }
    return render(request, 'core/my_purchases.html', context)

@login_required
@require_POST
@csrf_exempt
def reorder(request, order_id):
    # Get the original order
    original_order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    try:
        # Get quantity from form data
        quantity = int(request.POST.get('quantity', original_order.quantity))
        
        # Check if the product is still available
        if original_order.product.stock_quantity < quantity:
            messages.error(request, f'Only {original_order.product.stock_quantity}kg available')
            return redirect('order_history')
        
        # Create a new order with the same product and quantity
        new_order = Order.objects.create(
            buyer=request.user,
            product=original_order.product,
            quantity=quantity,
            total_price=quantity * original_order.product.price_per_kg,
            status='Pending',
            payment_status='Pending'
        )
        
        # Create a new escrow transaction for the new order
        escrow = EscrowTransaction.objects.create(
            order=new_order,
            amount=new_order.total_price,
            status='Pending'
        )
        
        # Update product stock
        original_order.product.stock_quantity -= quantity
        original_order.product.save()
        
        # Redirect to escrow payment page
        return redirect('escrow_payment', order_id=new_order.id)
        
    except Exception as e:
        messages.error(request, f"Error reordering: {str(e)}")
        return redirect('order_history')

@login_required
@require_POST
def auto_release_escrow(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Check if order is in correct state for auto-release
    if order.status != 'Completed' or order.payment_status != 'In Escrow':
        return JsonResponse({
            'success': False,
            'error': 'Order is not in a valid state for auto-release'
        })
    
    # Check if 12 hours have passed since completion
    if not order.completed_at:
        return JsonResponse({
            'success': False,
            'error': 'Order completion time not set'
        })
    
    time_since_completion = timezone.now() - order.completed_at
    if time_since_completion.total_seconds() < 12 * 60 * 60:
        return JsonResponse({
            'success': False,
            'error': '12 hours have not passed since order completion'
        })
    
    # Release the escrow
    try:
        escrow = order.escrow_transaction
        escrow.status = 'Released'
        escrow.release_date = timezone.now()
        escrow.save()
        
        order.payment_status = 'Released'
        order.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_POST
def confirm_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if order.status != 'Completed' or not order.escrow_transaction or order.escrow_transaction.status != 'Funded':
        return JsonResponse({
            'success': False,
            'error': 'Order is not in a valid state for confirmation'
        })
    
    try:
        # Release the escrow immediately
        escrow = order.escrow_transaction
        escrow.status = 'Released'
        escrow.release_date = timezone.now()
        escrow.save()
        
        order.payment_status = 'Released'
        order.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def check_pending_releases(request):
    """This function should be called by a cron job every hour"""
    current_time = timezone.now()
    
    # Find all escrow transactions that are ready for release
    ready_for_release = EscrowTransaction.objects.filter(
        status='Funded',
        order__status='Completed',
        order__completed_at__isnull=False,
        order__completed_at__lte=current_time - timezone.timedelta(hours=12)
    )
    
    for escrow in ready_for_release:
        # Update escrow status
        escrow.status = 'Released'
        escrow.release_date = current_time
        escrow.save()
        
        # Update the order payment status
        order = escrow.order
        order.payment_status = 'Released'
        order.save()
    
    return JsonResponse({'success': True, 'released_count': ready_for_release.count()})

@csrf_exempt
@require_POST
def paypal_webhook(request):
    """Handle PayPal webhook notifications"""
    try:
        # Get the webhook data
        webhook_data = json.loads(request.body)
        logger.info(f"Received PayPal webhook: {webhook_data}")
        
        # Verify webhook signature in live mode
        if settings.PAYPAL_MODE == 'live':
            paypal = PayPalGateway()
            if not paypal.verify_webhook_signature(request):
                logger.error("Invalid PayPal webhook signature")
                return HttpResponse(status=400)
        
        # Extract event type and resource
        event_type = webhook_data.get('event_type')
        resource = webhook_data.get('resource', {})
        
        # Get order ID from custom_id
        order_id = resource.get('custom_id')
        if not order_id:
            logger.error("No order ID found in webhook data")
            return HttpResponse(status=400)
        
        # Get the order and escrow transaction
        try:
            order = Order.objects.get(id=order_id)
            escrow = order.escrow_transaction
            logger.info(f"Found order {order_id} and escrow transaction")
        except (Order.DoesNotExist, EscrowTransaction.DoesNotExist) as e:
            logger.error(f"Error finding order or escrow: {str(e)}")
            return HttpResponse(status=404)
        
        # Process different event types
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            # Update escrow status
            escrow.status = 'Funded'
            escrow.payment_reference = resource.get('id')
            escrow.save()
            logger.info(f"Updated escrow status to Funded for order {order_id}")
            
            # Update order payment status
            order.payment_status = 'In Escrow'
            order.save()
            logger.info(f"Updated order payment status to In Escrow for order {order_id}")
            
            logger.info(f"Payment completed for order {order_id}")
            
        elif event_type == 'PAYMENT.CAPTURE.REFUNDED':
            # Update escrow status
            escrow.status = 'Refunded'
            escrow.save()
            logger.info(f"Updated escrow status to Refunded for order {order_id}")
            
            # Update order payment status
            order.payment_status = 'Refunded'
            order.save()
            logger.info(f"Updated order payment status to Refunded for order {order_id}")
            
            logger.info(f"Payment refunded for order {order_id}")
            
        elif event_type == 'PAYMENT.CAPTURE.DENIED':
            # Update escrow status
            escrow.status = 'Failed'
            escrow.save()
            logger.info(f"Updated escrow status to Failed for order {order_id}")
            
            # Update order payment status
            order.payment_status = 'Failed'
            order.save()
            logger.info(f"Updated order payment status to Failed for order {order_id}")
            
            logger.info(f"Payment denied for order {order_id}")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        return HttpResponse(status=500)

@login_required
def seller_verification(request):
    try:
        verification = request.user.verification
        if verification.status == 'Verified':
            messages.info(request, 'Your account is already verified.')
            return redirect('dashboard')
    except SellerVerification.DoesNotExist:
        verification = None

    if request.method == 'POST':
        form = SellerVerificationForm(request.POST, request.FILES, instance=verification)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.seller = request.user
            verification.status = 'Pending'
            verification.save()
            messages.success(request, 'Your verification request has been submitted. We will review it shortly.')
            return redirect('dashboard')
    else:
        form = SellerVerificationForm(instance=verification)

    context = {
        'form': form,
        'verification': verification
    }
    return render(request, 'core/seller_verification.html', context)

@login_required
@user_passes_test(is_admin)
def verify_seller(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            verification.status = 'Verified'
            verification.verified_by = request.user
            verification.verification_date = timezone.now()
            verification.save()
            messages.success(request, f'Seller {verification.seller.username} has been verified.')
        elif action == 'reject':
            verification.status = 'Rejected'
            verification.rejection_reason = request.POST.get('rejection_reason')
            verification.save()
            messages.warning(request, f'Seller {verification.seller.username} has been rejected.')
        return redirect('pending_verifications')
    
    context = {
        'verification': verification
    }
    return render(request, 'core/verify_seller.html', context)

@login_required
@user_passes_test(is_admin)
def pending_verifications(request):
    verifications = SellerVerification.objects.filter(status='Pending').order_by('-created_at')
    context = {
        'verifications': verifications
    }
    return render(request, 'core/pending_verifications.html', context)

@login_required
@user_passes_test(is_admin)
def verification_list(request):
    verifications = SellerVerification.objects.all().order_by('-created_at')
    return render(request, 'core/admin/verification_list.html', {'verifications': verifications})

@login_required
@user_passes_test(is_admin)
def get_verification_details(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    data = {
        'full_name': verification.full_name,
        'id_number': verification.id_number,
        'id_document': verification.id_document.url if verification.id_document else '',
        'business_name': verification.business_name,
        'business_address': verification.business_address,
        'business_location': verification.business_location,
        'business_permit': verification.business_permit.url if verification.business_permit else '',
        'status': verification.status
    }
    return JsonResponse(data)

@login_required
@user_passes_test(is_admin)
@require_POST
def approve_verification(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    verification.status = 'Verified'
    verification.verified_by = request.user
    verification.verification_date = timezone.now()
    verification.save()
    return JsonResponse({'success': True})

@login_required
@user_passes_test(is_admin)
@require_POST
def reject_verification(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    verification.status = 'Rejected'
    verification.rejection_reason = request.POST.get('reason', '')
    verification.save()
    return JsonResponse({'success': True})

@login_required
@staff_member_required
def admin_verifications(request):
    verifications = SellerVerification.objects.select_related('user').all()
    return render(request, 'core/admin_verifications.html', {
        'verifications': verifications
    })

@login_required
@staff_member_required
def admin_verify_seller(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    
    if request.method == 'POST':
        verification.status = 'Verified'
        verification.verification_date = timezone.now()
        verification.save()
        
        messages.success(request, f'Seller {verification.user.username} has been verified successfully.')
    else:
        messages.error(request, 'Invalid request method.')
    
    return redirect('admin_verifications')

@login_required
@staff_member_required
def admin_reject_seller(request, verification_id):
    verification = get_object_or_404(SellerVerification, id=verification_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason')
        if rejection_reason:
            verification.status = 'Rejected'
            verification.rejection_reason = rejection_reason
            verification.save()
            
            messages.success(request, f'Seller {verification.user.username} has been rejected.')
        else:
            messages.error(request, 'Please provide a rejection reason.')
    else:
        messages.error(request, 'Invalid request method.')
    
    return redirect('admin_verifications')