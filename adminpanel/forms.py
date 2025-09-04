# D:\Python_Projects\korichuko-ecomm\adminpanel\forms.py
from django import forms
from store.models import Category, SubCategory, Product, Size

class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
                w.attrs["class"] = (w.attrs.get("class", "") + " form-check-input").strip()
            elif isinstance(w, forms.Select):
                w.attrs["class"] = (w.attrs.get("class", "") + " form-select").strip()
            else:
                w.attrs["class"] = (w.attrs.get("class", "") + " form-control").strip()
            if isinstance(w, (forms.TextInput, forms.Textarea)):
                w.attrs.setdefault("placeholder", field.label or name.replace("_", " ").title())

class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget.attrs.setdefault("accept", "image/*")
        self.fields["image"].help_text = "Upload a category image."

class SubCategoryForm(StyledModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name", "slug", "image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget.attrs.setdefault("accept", "image/*")
        self.fields["image"].help_text = "Upload a sub-category image."

class SizeForm(forms.ModelForm):
    class Meta:
        model = Size
        fields = ["name", "abbreviation"]

class ProductForm(StyledModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "sub_category",
            "description",
            "regular_price",   # new
            "sale_price",      # new
            "size_value",
            "size",
            "image",
            "on_sale",
            "is_new",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order size choices nicely (abbreviation ASC)
        if "size" in self.fields:
            self.fields["size"].queryset = Size.objects.all().order_by("abbreviation")
            self.fields["size"].empty_label = "— Select Unit —"

        # Default subcategory queryset; narrowed below based on chosen category
        self.fields["sub_category"].queryset = SubCategory.objects.all()

        # If editing with an existing category, or if a category is preselected in POST/GET, filter subcategories
        cat = None
        if self.instance and self.instance.pk and getattr(self.instance, "category_id", None):
            cat = self.instance.category
        else:
            cat_id = self.data.get("category") or self.initial.get("category")
            if cat_id:
                try:
                    cat = Category.objects.get(pk=cat_id)
                except (Category.DoesNotExist, ValueError, TypeError):
                    cat = None
        if cat:
            self.fields["sub_category"].queryset = SubCategory.objects.filter(category=cat).order_by("name")

        # Image helpers
        self.fields["image"].widget.attrs.setdefault("accept", "image/*")
        self.fields["image"].help_text = "Upload a product image. A live preview will appear below."
