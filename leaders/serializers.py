from rest_framework import serializers

from .models import Leader


class LeaderSerializer(serializers.ModelSerializer):
    # Nested user fields — read-only
    user_id = serializers.UUIDField(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.profile.full_name", read_only=True
    )
    user_phone = serializers.CharField(
        source="user.profile.phone", read_only=True
    )
    user_photo = serializers.CharField(
        source="user.profile.photo_base64", read_only=True
    )

    class Meta:
        model = Leader
        fields = [
            "id",
            "user_id",
            "user_email",
            "user_full_name",
            "user_phone",
            "user_photo",
            "position",
            "bio",
            "display_order",
            "is_active",
            "appointed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "user_email",
            "user_full_name",
            "user_phone",
            "user_photo",
            "created_at",
            "updated_at",
        ]

    def validate_position(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Position is required.")
        return value.strip()