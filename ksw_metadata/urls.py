from django.contrib.auth import views as auth_views
from django.urls import include, path

from metadata_tool import views


urlpatterns = [
	path("accounts/login/", auth_views.LoginView.as_view(template_name="metadata_tool/login.html"), name="login"),
	path("accounts/logout/", views.logout_view, name="logout"),
	path("accounts/register/", views.register, name="register"),
	path("", include("metadata_tool.urls")),
]