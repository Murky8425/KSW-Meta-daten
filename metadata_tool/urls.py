from django.urls import path

from . import views


urlpatterns = [
	path("", views.index, name="index"),
	path("upload-preview/<str:filename>/", views.preview_upload, name="preview_upload"),
	path("video-editor/", views.video_editor, name="video_editor"),
	path("video-mixer/", views.video_mixer, name="video_mixer"),
	path("archive/", views.archive, name="archive"),
	path("images/<int:image_id>/delete/", views.delete_archive_image, name="delete_archive_image"),
	path("images/<int:image_id>/download/", views.download_image, name="download_image"),
]