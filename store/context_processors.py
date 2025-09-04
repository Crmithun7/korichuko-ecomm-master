# store/context_processors.py
from .models import Order

def cart_context(request):
    order = None
    if request.user.is_authenticated:
        order = Order.objects.filter(user=request.user, completed=False).first()
    return {"order": order}
