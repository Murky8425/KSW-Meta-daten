from django.urls import include, path


urlpatterns = [path("", include("metadata_tool.urls"))]