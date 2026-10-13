from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Book

User = get_user_model()


class BookSerializer(serializers.ModelSerializer):
    """Read/write serializer for Book with base64 file."""

    # Frontend sends this exact name
    file = serializers.CharField(
        source="file_base64",
        required=False,
        allow_blank=True,
    )
    uploaded_by = serializers.UUIDField(source="uploaded_by_id", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "description",
            "file",
            "file_name",
            "category",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "uploaded_by"]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()

    def validate_author(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Author is required.")
        return value.strip()

    def validate_file_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("File name is required.")
        return value.strip()