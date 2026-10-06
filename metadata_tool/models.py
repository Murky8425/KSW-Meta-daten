from django.conf import settings
from django.db import models


class StoredImage(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stored_images")
    original_filename = models.CharField(max_length=255)
    storage_name = models.CharField(max_length=255, unique=True)
    image_data = models.BinaryField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class UserPreference(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="image_preferences")
    preferred_scale = models.PositiveSmallIntegerField(default=100)

    def save(self, *args, **kwargs):
        self.preferred_scale = min(200, max(10, self.preferred_scale))
        super().save(*args, **kwargs)


class ExtractedMetadata(models.Model):
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, unique=True)
    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    creator = models.TextField(blank=True)
    rights = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    all_metadata = models.TextField()
    extracted_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ausgelesene_metadaten"
        ordering = ["-extracted_at"]