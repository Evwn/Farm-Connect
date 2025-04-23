from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg
from .models import Review, Product

@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    reviews = Review.objects.filter(product=product)
    
    # Calculate new average rating
    avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
    
    # Update product fields
    product.average_rating = avg_rating
    product.total_ratings = reviews.count()
    product.save() 