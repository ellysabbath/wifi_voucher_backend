from django.conf import settings
from django.db import models
from core.models import BaseModel


class Leader(BaseModel):
    """Church leadership position — linked to a user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leadership",
        null=True,
        blank=True,
    )
    position = models.CharField(max_length=100)
    bio = models.TextField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    appointed_at = models.DateField()

    class Meta:
        db_table = "leader"
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.user.email if self.user else 'Unlinked'} — {self.position}"