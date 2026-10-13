from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class SMSGroup(BaseModel):
    """Custom SMS recipient group."""

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
    """Junction table — SMS group ↔ member."""

    group = models.ForeignKey(SMSGroup, on_delete=models.CASCADE, related_name="members")
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="sms_groups"
    )

    class Meta:
        db_table = "sms_group_member"
        unique_together = ("group", "member")

    def __str__(self):
        return f"{self.group.name} — {self.member.full_name}"


class SMSMessage(BaseModel):
    """Bulk SMS message record."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    message = models.TextField()
    group_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_sms",
    )
    recipient_count = models.IntegerField(default=0)

    class Meta:
        db_table = "sms_message"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self):
        return f"SMS #{self.id} — {self.recipient_count} recipients"


class SMSRecipient(BaseModel):
    """Individual SMS recipient (junction table)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    sms_message = models.ForeignKey(
        SMSMessage, on_delete=models.CASCADE, related_name="recipients"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="received_sms"
    )
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sms_recipient"
        unique_together = ("sms_message", "member")
        indexes = [models.Index(fields=["sms_message"])]

    def __str__(self):
        return f"{self.phone} — {self.status}"