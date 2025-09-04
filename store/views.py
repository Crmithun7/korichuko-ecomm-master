# store/views.py
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Sum, F, Case, When, DecimalField
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

import razorpay

from .models import Category, Order, OrderItem, Product


# ---------------------------
# Auth
# ---------------------------
def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_staff = False  # customer, not admin
            user.save()
            login(request, user)
            return redirect("store:home")
    else:
        form = UserCreationForm()
    return render(request, "store/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("store:home")
    else:
        form = AuthenticationForm(request)
    return render(request, "store/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("store:home")


# ---------------------------
# Pages
# ---------------------------
def home(request):
    discounted_products = Product.objects.filter(on_sale=True)[:6]
    new_products = Product.objects.filter(is_new=True).order_by("-created_at")[:6]
    categories = Category.objects.all()
    return render(
        request,
        "store/home.html",
        {
            "discounted_products": discounted_products,
            "new_products": new_products,
            "categories": categories,
        },
    )


def shop(request):
    category_slug = request.GET.get("category")
    max_price = request.GET.get("max_price")
    sort = request.GET.get("sort")

    # sale_price if set, else regular_price
    price_expr = Case(
        When(sale_price__isnull=False, then=F("sale_price")),
        default=F("regular_price"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    products = Product.objects.all().annotate(effective_price=price_expr)
    categories = Category.objects.all()

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if max_price:
        try:
            products = products.filter(effective_price__lte=float(max_price))
        except ValueError:
            pass

    if sort == "price_asc":
        products = products.order_by("effective_price")
    elif sort == "price_desc":
        products = products.order_by("-effective_price")
    else:
        products = products.order_by("-created_at")

    return render(
        request,
        "store/shop.html",
        {"products": products, "categories": categories, "max_price": max_price},
    )


# def product_detail(request, pk):
#     product = get_object_or_404(Product, pk=pk)
#     related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
#     return render(
#         request, "store/product_detail.html", {"product": product, "related_products": related_products}
#     )

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Get related products and compute discount % in Python (no template math)
    related_products = list(
        Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    )
    for rp in related_products:
        try:
            if rp.sale_price and rp.regular_price and Decimal(rp.regular_price) > 0:
                rp.discount_percent = int(
                    ((Decimal(rp.regular_price) - Decimal(rp.sale_price))
                     / Decimal(rp.regular_price)) * 100
                )
            else:
                rp.discount_percent = 0
        except Exception:
            rp.discount_percent = 0

    return render(
        request,
        "store/product_detail.html",
        {"product": product, "related_products": related_products},
    )

# ---------------------------
# Cart helpers
# ---------------------------
def _get_or_create_open_order(user):
    try:
        return Order.objects.get(user=user, completed=False)
    except Order.DoesNotExist:
        return Order.objects.create(user=user, completed=False)


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _json_cart_payload(order, request, message="", status="success"):
    cart_count = order.items.aggregate(total=Sum("quantity"))["total"] or 0
    cart_html = render_to_string("store/_cart_items.html", {"order": order}, request=request)
    total_price = getattr(order, "total_price", Decimal("0.00"))
    try:
        total_price = float(total_price)
    except Exception:
        total_price = 0.0
    return {
        "status": status,              # must be "success" for base.html handler
        "message": message,
        "cart_count": int(cart_count),
        "total_price": total_price,
        "cart_html": cart_html,
    }


# ---------------------------
# Cart views (match urls.py)
# ---------------------------
@login_required(login_url="store:login")
def cart(request):
    order = _get_or_create_open_order(request.user)
    return render(request, "store/cart.html", {"order": order})


def add_to_cart(request, pk):
    ajax = _is_ajax(request)

    if not request.user.is_authenticated:
        if ajax:
            return JsonResponse(
                {"status": "unauthenticated", "message": "Please log in to add items"}, status=401
            )
        return redirect("store:login")

    product = get_object_or_404(Product, pk=pk)
    order = _get_or_create_open_order(request.user)
    item, created = OrderItem.objects.get_or_create(order=order, product=product, defaults={"quantity": 1})
    if not created:
        OrderItem.objects.filter(pk=item.pk).update(quantity=F("quantity") + 1)

    payload = _json_cart_payload(order, request, message=f'"{product.name}" added to cart')
    if ajax:
        return JsonResponse(payload)
    return redirect("store:cart")


@login_required(login_url="store:login")
def remove_from_cart(request, item_id):
    item = get_object_or_404(
        OrderItem, pk=item_id, order__user=request.user, order__completed=False
    )
    order = item.order
    name = item.product.name
    item.delete()

    if _is_ajax(request):
        return JsonResponse(_json_cart_payload(order, request, message=f'"{name}" removed from cart'))
    return redirect("store:cart")


@login_required(login_url="store:login")
def update_cart_quantity(request, item_id):
    """
    POST with action=increase|decrease  OR quantity=<int>
    """
    item = get_object_or_404(
        OrderItem, pk=item_id, order__user=request.user, order__completed=False
    )

    if request.method == "POST":
        action = request.POST.get("action")
        qty = request.POST.get("quantity")

        if qty is not None:
            try:
                item.quantity = max(1, int(qty))
            except ValueError:
                pass
        elif action == "increase":
            item.quantity += 1
        elif action == "decrease":
            item.quantity = max(1, item.quantity - 1)
        item.save()

    if _is_ajax(request):
        return JsonResponse(_json_cart_payload(item.order, request, message="Quantity updated"))
    return redirect("store:cart")


# ---------------------------
# Checkout & Payment
# ---------------------------
@login_required(login_url="store:login")
def checkout(request):
    order = get_object_or_404(Order, user=request.user, completed=False)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if payment_method == "cod":
            order.completed = True
            order.save()
            return redirect("store:order_success", order_id=order.id)

        elif payment_method == "razorpay":
            # create razorpay order and send to the dedicated payment page
            razorpay_client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            amount_paise = int(order.total_price * 100)
            rp_order = razorpay_client.order.create(
                dict(amount=amount_paise, currency="INR", payment_capture="1")
            )
            context = {
                "order": order,
                "razorpay_order_id": rp_order["id"],
                "razorpay_merchant_key": settings.RAZORPAY_KEY_ID,
                "razorpay_amount": amount_paise,
                "callback_url": request.build_absolute_uri(
                    reverse("store:paymenthandler", args=[order.id])
                ),
            }
            return render(request, "store/razorpay_payment.html", context)

    return render(request, "store/checkout.html", {"order": order})


@csrf_exempt
@login_required(login_url="store:login")
def paymenthandler(request, order_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid Request")

    order = get_object_or_404(Order, pk=order_id, user=request.user, completed=False)
    try:
        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        params_dict = {
            "razorpay_order_id": request.POST.get("razorpay_order_id", ""),
            "razorpay_payment_id": request.POST.get("razorpay_payment_id", ""),
            "razorpay_signature": request.POST.get("razorpay_signature", ""),
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
        order.completed = True
        order.save()
        return redirect("store:order_success", order_id=order.id)
    except Exception:
        return HttpResponseBadRequest("Payment Verification Failed")


@login_required(login_url="store:login")
def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, completed=True)
    return render(request, "store/order_success.html", {"order": order})
