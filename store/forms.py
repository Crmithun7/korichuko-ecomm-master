from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomerAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("Account disabled.", code="inactive")
        if user.is_staff:
            # Staff must use the admin login
            raise forms.ValidationError("Please use the admin login.", code="not_customer")
