from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class News(BaseModel):
    """Church news & announcements."""

    CATEGORY_CHOICES = [
        ("announcement", "Announcement"),
        ("event", "Event"),
        ("news", "News"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    image_base64 = models.TextField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_articles",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "news"
        verbose_name_plural = "News"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title