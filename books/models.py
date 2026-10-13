from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class Book(BaseModel):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    # cover_base64 = models.TextField(null=True, blank=True)   ← removed
    file_base64 = models.TextField()
    file_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_uploads",
    )

    class Meta:
        db_table = "book"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category"])]

    def __str__(self):
        return self.title