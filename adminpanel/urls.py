# adminpanel/urls.py
from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("products/", views.ProductListView.as_view(), name="products"),
    path("products/create/", views.ProductCreateView.as_view(), name="product_create"),
    path(
        "products/<int:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_update",
    ),
    path(
        "products/<int:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path(
        "categories/create/", views.CategoryCreateView.as_view(), name="category_create"
    ),
    path(
        "categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_update",
    ),
    path(
        "categories/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    path("subcategories/", views.SubCategoryListView.as_view(), name="subcategories"),
    path(
        "subcategories/create/",
        views.SubCategoryCreateView.as_view(),
        name="subcategory_create",
    ),
    path(
        "subcategories/<int:pk>/edit/",
        views.SubCategoryUpdateView.as_view(),
        name="subcategory_update",
    ),
    path(
        "subcategories/<int:pk>/delete/",
        views.SubCategoryDeleteView.as_view(),
        name="subcategory_delete",
    ),
    path("orders/", views.OrderListView.as_view(), name="orders"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path(
        "orders/<int:pk>/toggle/",
        views.order_toggle_completed,
        name="order_toggle_completed",
    ),
    path("customers/", views.CustomerListView.as_view(), name="customers"),
    path(
        "customers/<int:user_id>/",
        views.CustomerDetailView.as_view(),
        name="customer_detail",
    ),
    # Size CRUD
    path("sizes/", views.SizeListView.as_view(), name="sizes"),
    path("sizes/create/", views.SizeCreateView.as_view(), name="size_create"),
    path("sizes/<int:pk>/edit/", views.SizeUpdateView.as_view(), name="size_update"),
    path("sizes/<int:pk>/delete/", views.SizeDeleteView.as_view(), name="size_delete"),
    path(
        "api/metrics/orders-per-day/",
        views.orders_per_day_api,
        name="orders_per_day_api",
    ),
]
