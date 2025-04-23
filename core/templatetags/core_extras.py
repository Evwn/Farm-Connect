from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def avg_rating(reviews):
    """Calculate the average rating from a queryset of reviews"""
    if not reviews:
        return 0
    return reviews.aggregate(avg=Avg('rating'))['avg'] or 0 