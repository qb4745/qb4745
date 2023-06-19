from django import template
from core.models import Order

register = template.Library()

@register.filter
def cart_item_count(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False)
        if qs.exists():
            total_quantity = sum(order_item.quantity for order_item in qs[0].items.all())
            return total_quantity
    return 0