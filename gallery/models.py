from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class GalleryItem(BaseModel):
    """Church photo gallery item."""

    title = models.CharField(max_length=200)
    image_base64 = models.TextField()
    album = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gallery_uploads",
    )

    class Meta:
        db_table = "gallery_item"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["album"])]

    def __str__(self):
        return self.title