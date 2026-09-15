from django.db import models


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