from rest_framework import serializers

from .models import News


class NewsSerializer(serializers.ModelSerializer):
    # Accept "image" from the frontend, store into "image_base64"
    image = serializers.CharField(
        source="image_base64",
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    author_email = serializers.EmailField(source="author.email", read_only=True)
    # NOTE: no `source=` here — `author_id` matches the model field directly.
    author_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "content",
            "image",
            "author_id",
            "author_email",
            "category",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author_id",
            "author_email",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Content is required.")
        return value.strip()

    def validate_category(self, value):
        valid = {"announcement", "event", "news"}
        if value not in valid:
            raise serializers.ValidationError(
                f"Category must be one of: {', '.join(sorted(valid))}."
            )
        return value