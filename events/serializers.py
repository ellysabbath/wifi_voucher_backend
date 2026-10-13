from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Event

User = get_user_model()


class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.UUIDField(source="created_by_id", read_only=True)
    created_by_email = serializers.EmailField(
        source="created_by.email", read_only=True
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "event_date",
            "event_time",
            "location",
            "category",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()

    def validate_location(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Location is required.")
        return value.strip()

    def validate_category(self, value):
        valid = {"worship", "meeting", "celebration", "session"}
        if value not in valid:
            raise serializers.ValidationError(
                f"Category must be one of: {', '.join(sorted(valid))}."
            )
        return value