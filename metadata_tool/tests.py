import io
import zipfile

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
        original_data = self.make_png()
        upload = SimpleUploadedFile("foto.png", original_data, content_type="image/png")
        self.client.post("/", {"images": upload})
        stored_image = StoredImage.objects.get(owner=user)

        response = self.client.post("/", {
            "action": "resize",
            "selected": stored_image.storage_name,
            "scale": "95",
        })

        resized = Image.open(io.BytesIO(response.content))
        self.assertEqual(resized.size, (190, 95))
        stored_image.refresh_from_db()
        self.assertEqual(bytes(stored_image.image_data), original_data)
        resized_image = StoredImage.objects.get(owner=user, original_filename="foto-95prozent.png")
        self.assertEqual(resized_image.last_scale, 95)
        archived = Image.open(io.BytesIO(bytes(resized_image.image_data)))
        self.assertEqual(archived.size, (190, 95))
        self.assertContains(self.client.get("/archive/"), "foto-95prozent.png")
        self.assertEqual(UserPreference.objects.get(owner=user).preferred_scale, 95)

        repeated_resize = self.client.post("/", {
            "action": "resize",
            "selected": stored_image.storage_name,
            "scale": "50",
        })
        self.assertEqual(Image.open(io.BytesIO(repeated_resize.content)).size, (100, 50))
        resized_50_image = StoredImage.objects.get(owner=user, original_filename="foto-50prozent.png")
        self.assertEqual(resized_50_image.last_scale, 50)
        self.assertEqual(
            Image.open(io.BytesIO(self.client.get(f"/images/{resized_50_image.id}/download/").content)).size,
            (100, 50),
        )
        page = self.client.get("/")
        self.assertEqual(page.context["preferred_scale"], 50)

    def test_batch_resize_archives_scaled_copies_and_keeps_originals(self):
        user = get_user_model().objects.create_user(username="batchscale", password="ImageVault99!abc")
        self.client.force_login(user)
        original_data = self.make_png()
        uploads = [
            SimpleUploadedFile("erstes.png", original_data, content_type="image/png"),
            SimpleUploadedFile("zweites.png", original_data, content_type="image/png"),
        ]
        self.client.post("/", {"images": uploads})
        originals = list(StoredImage.objects.filter(owner=user))

        response = self.client.post("/", {"action": "batch-resize", "scale": "30"})

        self.assertEqual(response["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()), {"erstes-30prozent.png", "zweites-30prozent.png"})
            for filename in archive.namelist():
                self.assertEqual(Image.open(io.BytesIO(archive.read(filename))).size, (60, 30))
        for original in originals:
            original.refresh_from_db()
            self.assertEqual(bytes(original.image_data), original_data)
        scaled_images = StoredImage.objects.filter(owner=user).exclude(id__in=[image.id for image in originals])
        self.assertEqual(scaled_images.count(), 2)
        self.assertEqual(set(scaled_images.values_list("original_filename", flat=True)), {
            "erstes-30prozent.png", "zweites-30prozent.png",
        })
        self.assertEqual(set(scaled_images.values_list("last_scale", flat=True)), {30})

    def test_archive_opens_but_does_not_offer_direct_download(self):
        user = get_user_model().objects.create_user(username="archiveuser", password="ImageVault99!abc")
        self.client.force_login(user)
        upload = SimpleUploadedFile("archivfoto.png", self.make_png(), content_type="image/png")
        self.client.post("/", {"images": upload})

        response = self.client.get("/archive/")
        self.assertContains(response, "Im Editor öffnen")
        self.assertNotContains(response, "Bild herunterladen")
        self.assertContains(response, "?load=")

    def test_loading_archive_image_shows_only_that_image_in_editor(self):
        user = get_user_model().objects.create_user(username="loadarchive", password="ImageVault99!abc")
        self.client.force_login(user)
        first = SimpleUploadedFile("erstes.png", self.make_png(), content_type="image/png")
        second = SimpleUploadedFile("zweites.png", self.make_png(), content_type="image/png")
        self.client.post("/", {"images": [first, second]})
        selected = StoredImage.objects.get(owner=user, original_filename="zweites.png")

        response = self.client.get(f"/?load={selected.storage_name}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([file["name"] for file in response.context["files"]], [selected.storage_name])
        self.assertEqual(response.context["selected_name"], selected.storage_name)

    def test_scale_remains_visible_when_reopening_editor(self):
        user = get_user_model().objects.create_user(username="scalecheck", password="ImageVault99!abc")
        self.client.force_login(user)
        upload = SimpleUploadedFile("scale.png", self.make_png(), content_type="image/png")
        self.client.post("/", {"images": upload})
        stored_image = StoredImage.objects.get(owner=user)

        self.client.post("/", {
            "action": "resize",
            "selected": stored_image.storage_name,
            "scale": "30",
        })

        resized_image = StoredImage.objects.get(owner=user, original_filename="scale-30prozent.png")
        page = self.client.get(f"/?selected={resized_image.storage_name}")
        self.assertEqual(page.context["current_scale"], 30)
        self.assertContains(page, "const currentScale = 30;")

    def test_delete_selected_image_and_archive_entry(self):
        user = get_user_model().objects.create_user(username="deleteuser", password="ImageVault99!abc")
        self.client.force_login(user)
        upload = SimpleUploadedFile("delete.png", self.make_png(), content_type="image/png")
        self.client.post("/", {"images": upload})
        stored_image = StoredImage.objects.get(owner=user)

        delete_response = self.client.post("/", {
            "action": "delete-selected",
            "selected": stored_image.storage_name,
        })
        self.assertRedirects(delete_response, "/")
        self.assertFalse(StoredImage.objects.filter(id=stored_image.id).exists())

        self.client.post("/", {"images": upload})
        archived_image = StoredImage.objects.get(owner=user)
        archive_response = self.client.post(f"/images/{archived_image.id}/delete/", {})
        self.assertEqual(archive_response.status_code, 302)
        self.assertFalse(StoredImage.objects.filter(id=archived_image.id).exists())