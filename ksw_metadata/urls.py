from django.urls import include, path

from metadata_tool import views


urlpatterns = [
	path("accounts/login/", views.login_view, name="login"),
	path("accounts/logout/", views.logout_view, name="logout"),
	path("accounts/register/", views.register, name="register"),
	path("accounts/resend-verification/", views.resend_verification, name="resend_verification"),
	path("accounts/verify/<str:token>/", views.verify_email, name="verify_email"),
	path("accounts/delete/", views.account_delete, name="account_delete"),
	path("accounts/delete/confirm/<str:token>/", views.confirm_account_deletion, name="confirm_account_deletion"),
	path("", include("metadata_tool.urls")),
]