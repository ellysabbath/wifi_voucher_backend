from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class Event(BaseModel):
    """Church calendar event."""

    CATEGORY_CHOICES = [
        ("worship", "Worship Service"),
        ("meeting", "Meeting"),
        ("celebration", "Celebration"),
        ("session", "Leadership Session"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    event_date = models.DateField()
    event_time = models.TimeField()
    location = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_events",
    )

    class Meta:
        db_table = "event"
        ordering = ["event_date", "event_time"]
        indexes = [models.Index(fields=["event_date"])]

    def __str__(self):
        return self.title