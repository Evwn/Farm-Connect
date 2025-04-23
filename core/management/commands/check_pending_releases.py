from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import EscrowTransaction, Order

class Command(BaseCommand):
    help = 'Checks for and releases escrow payments that have passed their 12-hour waiting period'

    def handle(self, *args, **options):
        current_time = timezone.now()
        
        # Find all orders that are ready for release
        ready_for_release = Order.objects.filter(
            status='Completed',
            payment_status='In Escrow',
            completed_at__isnull=False,
            completed_at__lte=current_time - timezone.timedelta(hours=12)
        )
        
        released_count = 0
        for order in ready_for_release:
            # Update escrow status
            escrow = order.escrow_transaction
            escrow.status = 'Released'
            escrow.release_date = current_time
            escrow.save()
            
            # Update the order payment status
            order.payment_status = 'Released'
            order.save()
            
            released_count += 1
            self.stdout.write(f'Released payment for order {order.id}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully released {released_count} payments')) 