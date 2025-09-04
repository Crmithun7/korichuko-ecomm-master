# adminpanel/views.py
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum, F, Count, Case, When, DecimalField
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from .forms import CategoryForm, SubCategoryForm, ProductForm, SizeForm
from store.models import Category, SubCategory, Product, Order, OrderItem, Size


# ---------- AUTH ----------
class StaffAuthForm(AuthenticationForm):
    """Only allow staff users into the adminpanel login."""
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            from django import forms
            raise forms.ValidationError(
                "This account does not have staff access.",
                code="no_staff",
            )


def admin_login(request):
    # If already logged in as staff, go to dashboard (or ?next)
    if request.user.is_authenticated and request.user.is_staff:
        nxt = request.GET.get("next") or request.POST.get("next")
        if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
            return redirect(nxt)
        return redirect("adminpanel:dashboard")

    form = StaffAuthForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        nxt = request.POST.get("next")
        if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
            return redirect(nxt)
        return redirect("adminpanel:dashboard")

    # NOTE: render a layout that does NOT include sidebar/topbar
    return render(request, "adminpanel/login.html", {
        "form": form,
        "next": request.GET.get("next", ""),
    })


def admin_logout(request):
    logout(request)
    # After logout, send them back to the staff login
    return redirect("adminpanel:login")


# ---------------- DASHBOARD + METRICS ----------------
@staff_member_required(login_url="adminpanel:login")
def dashboard(request):
    # KPIs
    total_products   = Product.objects.count()
    total_orders     = Order.objects.count()
    pending_orders   = Order.objects.filter(completed=False).count()
    completed_orders = Order.objects.filter(completed=True).count()

    # Revenue across completed orders: sum(quantity * effective_unit_price)
    # effective_unit_price = sale_price if set, else regular_price
    line_price = Case(
        When(product__sale_price__isnull=False, then=F("product__sale_price")),
        default=F("product__regular_price"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    revenue = (
        OrderItem.objects.filter(order__completed=True)
        .aggregate(total=Sum(line_price * F("quantity")))
        .get("total") or Decimal("0.00")
    )

    latest_orders = Order.objects.select_related("user").order_by("-id")[:7]

    # Optional low stock if Product has 'stock'
    low_stock = Product.objects.filter(stock__lte=10).order_by("stock")[:5] if hasattr(Product, "stock") else []

    context = {
        "kpis": {
            "products": total_products,
            "orders": total_orders,
            "pending": pending_orders,
            "completed": completed_orders,
            "revenue": revenue,
        },
        "latest_orders": latest_orders,
        "low_stock": low_stock,
    }
    return render(request, "adminpanel/dashboard.html", context)


@staff_member_required(login_url="adminpanel:login")
def orders_per_day_api(request):
    """
    Returns {labels: [...], data: [...], days: N, completed_only: bool}
    Counts orders by created_at::date in the last N days (default 30).
    """
    days = int(request.GET.get("days", 30))
    completed_only = request.GET.get("completed_only", "0").lower() in ("1", "true", "yes")
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)

    qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    if completed_only:
        qs = qs.filter(completed=True)

    per_day = (
        qs.values("created_at__date")
        .annotate(cnt=Count("id"))
        .order_by("created_at__date")
    )
    by_date = {row["created_at__date"]: row["cnt"] for row in per_day}

    labels, data = [], []
    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        data.append(by_date.get(d, 0))

    return JsonResponse({"labels": labels, "data": data, "days": days, "completed_only": completed_only})


# ---------------- MIXIN ----------------
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "adminpanel:login"
    def test_func(self):
        return self.request.user.is_staff


# ---------------- CATEGORIES ----------------
@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class CategoryListView(ListView):
    model = Category
    template_name = "adminpanel/crud/category_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = Category.objects.order_by("name")
        q = self.request.GET.get("q")
        return qs.filter(name__icontains=q) if q else qs


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "adminpanel/crud/category_form.html"
    success_url = reverse_lazy("adminpanel:categories")

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully with image support.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "adminpanel/crud/category_form.html"
    success_url = reverse_lazy("adminpanel:categories")

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully with image support.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class CategoryDeleteView(DeleteView):
    model = Category
    template_name = "adminpanel/crud/confirm_delete.html"
    success_url = reverse_lazy("adminpanel:categories")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Category deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ---------------- SUBCATEGORIES ----------------
@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SubCategoryListView(ListView):
    model = SubCategory
    template_name = "adminpanel/crud/subcategory_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = SubCategory.objects.select_related("category").order_by("category__name", "name")
        q = self.request.GET.get("q")
        return qs.filter(name__icontains=q) if q else qs


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SubCategoryCreateView(CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = "adminpanel/crud/subcategory_form.html"
    success_url = reverse_lazy("adminpanel:subcategories")

    def form_valid(self, form):
        messages.success(self.request, "Sub-category created successfully with image support.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SubCategoryUpdateView(UpdateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = "adminpanel/crud/subcategory_form.html"
    success_url = reverse_lazy("adminpanel:subcategories")

    def form_valid(self, form):
        messages.success(self.request, "Sub-category updated successfully with image support.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SubCategoryDeleteView(DeleteView):
    model = SubCategory
    template_name = "adminpanel/crud/confirm_delete.html"
    success_url = reverse_lazy("adminpanel:subcategories")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Sub-category deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ---------------- PRODUCTS ----------------
class ProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = "adminpanel/crud/product_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.select_related("category", "sub_category").order_by("-id")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(category__name__icontains=q)
                | Q(sub_category__name__icontains=q)
            )
        return qs


class ProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "adminpanel/crud/product_form.html"
    success_url = reverse_lazy("adminpanel:products")

    def form_valid(self, form):
        messages.success(self.request, "Product created.")
        return super().form_valid(form)


class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "adminpanel/crud/product_form.html"
    success_url = reverse_lazy("adminpanel:products")

    def form_valid(self, form):
        messages.success(self.request, "Product updated.")
        return super().form_valid(form)


class ProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = "adminpanel/crud/confirm_delete.html"
    success_url = reverse_lazy("adminpanel:products")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Product deleted.")
        return super().delete(request, *args, **kwargs)


# ---------------- ORDERS ----------------
class OrderListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = "adminpanel/sections/orders.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        qs = Order.objects.select_related("user").order_by("-id")
        status = self.request.GET.get("status")
        q = self.request.GET.get("q")
        if status == "pending":
            qs = qs.filter(completed=False)
        elif status == "completed":
            qs = qs.filter(completed=True)
        if q:
            qs = qs.filter(Q(user__username__icontains=q) | Q(id__icontains=q))
        return qs


class OrderDetailView(StaffRequiredMixin, DetailView):
    model = Order
    template_name = "adminpanel/sections/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = OrderItem.objects.select_related("product").filter(order=self.object)
        return ctx


@staff_member_required(login_url="adminpanel:login")
def order_toggle_completed(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.completed = not order.completed
    order.save()
    messages.success(request, f"Order #{order.id} marked as {'Completed' if order.completed else 'Pending'}.")
    return redirect("adminpanel:order_detail", pk=pk)


# ---------------- CUSTOMERS ----------------
User = get_user_model()


class CustomerListView(StaffRequiredMixin, ListView):
    template_name = "adminpanel/sections/customers.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Order.objects.values("user__id", "user__username")
            .annotate(orders_count=Count("id"))
            .order_by("-orders_count")
        )
        q = self.request.GET.get("q")
        return qs.filter(Q(user__username__icontains=q) | Q(user__id__icontains=q)) if q else qs


class CustomerDetailView(StaffRequiredMixin, DetailView):
    model = User
    pk_url_kwarg = "user_id"
    template_name = "adminpanel/sections/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        orders = Order.objects.filter(user=self.object).order_by("-id")
        ctx["orders"] = orders
        ctx["orders_count"] = orders.count()
        ctx["total_spend"] = sum(Decimal(o.total_price or 0) for o in orders)
        return ctx


# ---------------- SIZES ----------------
@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SizeListView(ListView):
    model = Size
    template_name = "adminpanel/crud/size_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = Size.objects.order_by("abbreviation")
        q = self.request.GET.get("q")
        return qs.filter(Q(name__icontains=q) | Q(abbreviation__icontains=q)) if q else qs


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SizeCreateView(CreateView):
    model = Size
    form_class = SizeForm
    template_name = "adminpanel/crud/size_form.html"
    success_url = reverse_lazy("adminpanel:sizes")

    def form_valid(self, form):
        messages.success(self.request, "Size created successfully.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SizeUpdateView(UpdateView):
    model = Size
    form_class = SizeForm
    template_name = "adminpanel/crud/size_form.html"
    success_url = reverse_lazy("adminpanel:sizes")

    def form_valid(self, form):
        messages.success(self.request, "Size updated successfully.")
        return super().form_valid(form)


@method_decorator(staff_member_required(login_url="adminpanel:login"), name="dispatch")
class SizeDeleteView(DeleteView):
    model = Size
    template_name = "adminpanel/crud/confirm_delete.html"
    success_url = reverse_lazy("adminpanel:sizes")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Size deleted successfully.")
        return super().delete(request, *args, **kwargs)
