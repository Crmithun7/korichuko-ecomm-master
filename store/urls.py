from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    # auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    # cart
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path(
        "cart/update-quantity/<int:item_id>/",
        views.update_cart_quantity,
        name="update_cart_quantity",
    ),
    # checkout / payment
    path("checkout/", views.checkout, name="checkout"),
    path("paymenthandler/<int:order_id>/", views.paymenthandler, name="paymenthandler"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
]
