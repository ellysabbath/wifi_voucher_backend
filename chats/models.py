from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from core.models import BaseModel


class ChatRoom(BaseModel):
    """Chat room."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_rooms",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "chat_room"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ChatMessage(BaseModel):
    """Chat message inside a room."""

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    message = models.TextField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.sender.email} @ {self.room.name}"