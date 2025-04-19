from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='core/login.html',
        redirect_field_name='next',
        next_page=None
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ✅ Farmer-specific routes
    path('dashboard/add-products/', views.add_product, name='add_product'),
    path('dashboard/my-products/', views.my_products, name='my_products'),
    path('dashboard/update-product/<int:product_id>/', views.update_product, name='update_product'),
    path('dashboard/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    
    
    path('dashboard/add-farm/', views.add_farm, name='add_farm'),
    path('dashboard/farm-management/', views.farm_management, name='farm_management'),
    path('dashboard/update-farm/<int:farm_id>/', views.update_farm, name='update_farm'),
    path('dashboard/delete-farm/<int:farm_id>/', views.delete_farm, name='delete_farm'),
    path('dashboard/browse-farms/', views.browse_farms, name='browse_farms'),
    # Add farm_detail URL (if implemented)
    path('dashboard/farm/<int:farm_id>/', views.farm_detail, name='farm_detail'),
    
    path('dashboard/orders/', views.orders, name='orders'),
    path('dashboard/orders/<int:order_id>/update/', views.update_order_status, name='update_order_status'),
    
    # Buyer-specific routes
    path('dashboard/browse-products/', views.browse_products, name='browse_products'),
    path('dashboard/order/<int:product_id>/', views.order_product, name='order_product'),
    path('dashboard/submit-order/', views.submit_order, name='submit_order'),
    path('dashboard/order-history/', views.order_history, name='order_history'),
    path('dashboard/my-purchases/', views.my_purchases, name='my_purchases'),
    
    # Order and Payment routes
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/payment/', views.escrow_payment, name='escrow_payment'),
    path('order/<int:order_id>/release/', views.release_escrow, name='release_escrow'),
    path('order/<int:order_id>/dispute/', views.dispute_escrow, name='dispute_escrow'),
    path('dashboard/reorder/<int:order_id>/', views.reorder, name='reorder'),
    
    # Dispute routes
    path('disputes/', views.dispute_list, name='dispute_list'),
    path('dispute/<int:order_id>/', views.dispute_detail, name='dispute_detail'),
    path('dispute/<int:order_id>/seller-response/', views.seller_dispute_response, name='seller_dispute_response'),
    path('dispute/<int:order_id>/admin-resolution/', views.admin_dispute_resolution, name='admin_dispute_resolution'),
    
    # Payment gateway callbacks
    path('order/<int:order_id>/paypal/success/', views.paypal_success, name='paypal_success'),
    path('order/<int:order_id>/paypal/cancel/', views.paypal_cancel, name='paypal_cancel'),
    path('order/<int:order_id>/paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('order/<int:order_id>/skrill/status/', views.skrill_status, name='skrill_status'),
    path('order/<int:order_id>/confirm/', views.confirm_order, name='confirm_order'),
    path('check-pending-releases/', views.check_pending_releases, name='check_pending_releases'),
]
