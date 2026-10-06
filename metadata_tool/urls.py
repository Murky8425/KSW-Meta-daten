from django.urls import path

from . import views


urlpatterns = [
	path("", views.index, name="index"),
	path("archive/", views.archive, name="archive"),
	path("images/<int:image_id>/delete/", views.delete_archive_image, name="delete_archive_image"),
	path("images/<int:image_id>/download/", views.download_image, name="download_image"),
]