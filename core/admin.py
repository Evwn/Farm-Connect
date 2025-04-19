from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Product, Farm, Order, EscrowTransaction, DisputeResponse, DisputeMessage, DisputeTimeline
from django.utils.html import format_html
from django.urls import reverse

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

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Product)
admin.site.register(Farm)
admin.site.register(Order)
admin.site.register(EscrowTransaction, EscrowTransactionAdmin)
admin.site.register(DisputeResponse, DisputeResponseAdmin)
admin.site.register(DisputeMessage, DisputeMessageAdmin)
admin.site.register(DisputeTimeline, DisputeTimelineAdmin)