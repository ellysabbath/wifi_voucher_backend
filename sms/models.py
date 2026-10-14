from django.conf import settings
from django.db import models
from core.models import BaseModel


class SMSGroup(BaseModel):
    """Custom SMS/email recipient group."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_groups",
    )

    class Meta:
        db_table = "sms_group"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SMSGroupMember(BaseModel):
    """Junction table — SMS group ↔ user account."""

    group = models.ForeignKey(
        SMSGroup, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_group_memberships",
    )

    class Meta:
        db_table = "sms_group_member"
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.group.name} — {self.user.email}"


class SMSMessage(BaseModel):
    """Bulk SMS/email campaign record."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("partial", "Partially sent"),
        ("failed", "Failed"),
    ]

    message = models.TextField()
    subject = models.CharField(max_length=200, null=True, blank=True)
    group_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_sms",
    )

    recipient_count = models.IntegerField(default=0)
    sms_sent_count = models.IntegerField(default=0)
    email_sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    class Meta:
        db_table = "sms_message"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self):
        return f"SMS #{self.id} — {self.recipient_count} recipients"


class SMSRecipient(BaseModel):
    """Individual delivery record — SMS + email per user."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    sms_message = models.ForeignKey(
        SMSMessage, on_delete=models.CASCADE, related_name="recipients"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="received_sms",
    )

    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    sms_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    email_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    sms_error = models.TextField(null=True, blank=True)
    email_error = models.TextField(null=True, blank=True)

    sms_sent_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sms_recipient"
        indexes = [models.Index(fields=["sms_message"])]

    def __str__(self):
        return f"{self.phone or self.email} — SMS:{self.sms_status} Email:{self.email_status}"