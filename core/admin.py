from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Product, Farm, Order, EscrowTransaction, DisputeResponse, DisputeMessage, DisputeTimeline, SellerVerification
from django.utils.html import format_html
from django.urls import reverse

class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        
        # Add custom links to the Core app
        for app in app_list:
            if app['app_label'] == 'core':
                app['models'].append({
                    'name': 'Verification Management',
                    'object_name': 'VerificationManagement',
                    'admin_url': '/admin/core/sellerverification/',
                    'view_only': True,
                })
        return app_list

# Create an instance of the custom admin site
admin_site = CustomAdminSite(name='admin')

class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'status', 'dispute_status', 'created_at', 'dispute_actions')
    list_filter = ('status', 'dispute_status')
    search_fields = ('order__id', 'order__buyer__username', 'order__product__name')
    readonly_fields = ('created_at', 'updated_at')
    
    def dispute_actions(self, obj):
        if obj.status == 'Disputed':
            return format_html(
                '<a class="button" href="{}">View Dispute</a>',
                reverse('dispute_detail', args=[obj.order.id])
            )
        return '-'
    dispute_actions.short_description = 'Actions'

class DisputeResponseAdmin(admin.ModelAdmin):
    list_display = ('escrow', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('escrow__order__id', 'user__username')

class DisputeMessageAdmin(admin.ModelAdmin):
    list_display = ('escrow', 'sender', 'is_admin_message', 'created_at')
    list_filter = ('is_admin_message', 'created_at')
    search_fields = ('escrow__order__id', 'sender__username')

class DisputeTimelineAdmin(admin.ModelAdmin):
    list_display = ('escrow', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('escrow__order__id', 'actor__username')

@admin.register(SellerVerification)
class SellerVerificationAdmin(admin.ModelAdmin):
    list_display = ('seller', 'status', 'created_at', 'verification_date')
    list_filter = ('status', 'created_at')
    search_fields = ('seller__username', 'full_name', 'business_name')
    readonly_fields = ('created_at', 'verification_date')
    fieldsets = (
        ('Personal Information', {
            'fields': ('seller', 'full_name', 'id_number', 'id_document')
        }),
        ('Business Information', {
            'fields': ('business_name', 'business_address', 'business_location', 'business_permit')
        }),
        ('Verification Status', {
            'fields': ('status', 'rejection_reason', 'created_at', 'verification_date')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller')

    def get_list_display_links(self, request, list_display):
        return ['seller']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

# Register models with the custom admin site
admin_site.register(CustomUser, UserAdmin)
admin_site.register(Product)
admin_site.register(Farm)
admin_site.register(Order)
admin_site.register(EscrowTransaction, EscrowTransactionAdmin)
admin_site.register(DisputeResponse, DisputeResponseAdmin)
admin_site.register(DisputeMessage, DisputeMessageAdmin)
admin_site.register(DisputeTimeline, DisputeTimelineAdmin)
admin_site.register(SellerVerification, SellerVerificationAdmin)