from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError

from .models import AccountLifecycle


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-Mail-Adresse")

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("Diese E-Mail-Adresse wird bereits verwendet.")
        return email


class AccountLoginForm(AuthenticationForm):
    recovery_code = forms.CharField(
        required=False,
        label="Recovery-Code (nur für gesperrte Konten)",
        widget=forms.PasswordInput(attrs={"autocomplete": "one-time-code"}),
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return self.cleaned_data

        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            self.user_cache = user
            return self.cleaned_data

        user_model = get_user_model()
        inactive_user = user_model.objects.filter(username=username).first()
        if inactive_user is None or not inactive_user.check_password(password):
            raise self.get_invalid_login_error()

        lifecycle = AccountLifecycle.objects.filter(owner=inactive_user).first()
        if lifecycle is None or not lifecycle.email_verified:
            raise ValidationError("Bitte bestätige zuerst deine E-Mail-Adresse.")
        if not lifecycle.deactivated_at:
            raise self.get_invalid_login_error()

        code = self.cleaned_data.get("recovery_code", "").strip()
        if not code or not check_password(code, lifecycle.recovery_code_hash):
            raise ValidationError("Für die Wiederherstellung ist ein gültiger Recovery-Code erforderlich.")

        lifecycle.deactivated_at = None
        lifecycle.warning_sent_at = None
        lifecycle.recovery_code_hash = ""
        lifecycle.save(update_fields=["deactivated_at", "warning_sent_at", "recovery_code_hash"])
        inactive_user.is_active = True
        inactive_user.save(update_fields=["is_active"])
        inactive_user.backend = "django.contrib.auth.backends.ModelBackend"
        self.user_cache = inactive_user
        return self.cleaned_data