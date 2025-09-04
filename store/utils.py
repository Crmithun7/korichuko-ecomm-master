from .models import Order

def get_or_create_open_order(user):
    """
    Return the single open (completed=False) order for the user.
    If none exists, create it. If multiples exist (bad state), keep the oldest.
    """
    qs = Order.objects.filter(user=user, completed=False).order_by("id")
    if qs.exists():
        order = qs.first()
        # clean up accidental duplicates
        Order.objects.filter(user=user, completed=False).exclude(pk=order.pk).delete()
        return order
    return Order.objects.create(user=user, completed=False)
