from django.db import models
from core.models import BaseModel


class Ministry(BaseModel):
    """Church ministry / department."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    leader_name = models.CharField(max_length=150, null=True, blank=True)
    meeting_day = models.CharField(max_length=20)
    meeting_time = models.TimeField(null=True, blank=True)
    icon = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ministry"
        verbose_name_plural = "Ministries"
        ordering = ["name"]

    def __str__(self):
        return self.name