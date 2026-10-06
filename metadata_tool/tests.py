import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import StoredImage, UserPreference


class UserImageArchiveTests(TestCase):
    def make_png(self):
        image = Image.new("RGB", (200, 100), "teal")
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def register_max(self):
        return self.client.post("/accounts/register/", {
            "username": "Max",
            "password1": "ImageVault99!abc",
            "password2": "ImageVault99!abc",
        })

    def test_registration_rejects_trivial_password(self):
        response = self.client.post("/accounts/register/", {
            "username": "Max",
            "password1": "123",
            "password2": "123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="Max").exists())

    def test_registration_upload_download_and_private_archive(self):
        registration = self.register_max()
        self.assertRedirects(registration, "/")

        image_data = self.make_png()
        upload = SimpleUploadedFile("urlaub.png", image_data, content_type="image/png")
        response = self.client.post("/", {"images": upload})
        self.assertRedirects(response, "/")

        stored_image = StoredImage.objects.get(original_filename="urlaub.png")
        self.assertEqual(bytes(stored_image.image_data), image_data)
        self.assertContains(self.client.get("/archive/"), "urlaub.png")
        download = self.client.get(f"/images/{stored_image.id}/download/")
        self.assertEqual(download.content, image_data)
        self.assertIn("attachment", download["Content-Disposition"])

        other_user = get_user_model().objects.create_user(username="anna", password="AnotherPassword94!")
        self.client.force_login(other_user)
        self.assertNotContains(self.client.get("/archive/"), "urlaub.png")
        self.assertEqual(self.client.get(f"/images/{stored_image.id}/download/").status_code, 404)

    def test_resize_preference_is_saved_and_accepts_95_percent(self):
        user = get_user_model().objects.create_user(username="max", password="ImageVault99!abc")
        self.client.force_login(user)
        upload = SimpleUploadedFile("foto.png", self.make_png(), content_type="image/png")
        self.client.post("/", {"images": upload})
        stored_image = StoredImage.objects.get(owner=user)

        response = self.client.post("/", {
            "action": "resize",
            "selected": stored_image.storage_name,
            "scale": "95",
        })

        resized = Image.open(io.BytesIO(response.content))
        self.assertEqual(resized.size, (190, 95))
        self.assertEqual(UserPreference.objects.get(owner=user).preferred_scale, 95)
        page = self.client.get("/")
        self.assertEqual(page.context["preferred_scale"], 95)