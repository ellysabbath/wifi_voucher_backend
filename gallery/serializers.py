from rest_framework import serializers

from .models import GalleryItem


class GalleryItemSerializer(serializers.ModelSerializer):
    # Frontend sends "image" → stored in "image_base64"
    image = serializers.CharField(source="image_base64")

    # Nested lookup — keep the source
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email", read_only=True
    )

    # NOTE: no `source=` — `uploaded_by_id` matches the model attribute directly.
    uploaded_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = GalleryItem
        fields = [
            "id",
            "title",
            "image",
            "album",
            "uploaded_by_id",
            "uploaded_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uploaded_by_id",
            "uploaded_by_email",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()

    def validate_album(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Album is required.")
        return value.strip()

    def validate_image(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Image is required.")
        return value