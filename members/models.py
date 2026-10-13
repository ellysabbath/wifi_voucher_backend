from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class Member(BaseModel):
    """Church member record."""

    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]
    AGE_GROUP_CHOICES = [
        ("child", "Child"),
        ("youth", "Youth"),
        ("elder", "Elder"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="member_record",
    )
    ministry = models.ForeignKey(
        "ministries.Ministry",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="members",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES)
    baptized = models.BooleanField(default=False)
    baptism_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    photo_base64 = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "member"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
            models.Index(fields=["ministry"]),
        ]

    def __str__(self):
        return self.full_name