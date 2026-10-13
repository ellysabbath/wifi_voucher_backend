from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile, OTPCode, UserPreference

User = get_user_model()


# =========================================================
# ADMIN — USER
# =========================================================
class AdminUserListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""

    full_name = serializers.CharField(source="profile.full_name", read_only=True)
    phone = serializers.CharField(source="profile.phone", read_only=True)
    role = serializers.CharField(source="profile.role", read_only=True)
    email_verified = serializers.BooleanField(
        source="profile.email_verified", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "role",
            "email_verified", "is_active", "is_staff", "is_superuser",
            "date_joined", "last_login",
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Full detail — includes nested profile."""

    full_name = serializers.CharField(source="profile.full_name", required=False)
    phone = serializers.CharField(source="profile.phone", required=False)
    photo = serializers.CharField(
        source="profile.photo_base64", required=False, allow_blank=True, allow_null=True
    )
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True)
    address = serializers.CharField(source="profile.address", required=False, allow_blank=True)
    role = serializers.CharField(source="profile.role", required=False)
    email_verified = serializers.BooleanField(
        source="profile.email_verified", required=False
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "password",
            "full_name", "phone", "photo", "bio", "address", "role",
            "email_verified",
            "is_active", "is_staff", "is_superuser",
            "date_joined", "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]
        extra_kwargs = {
            "password": {"write_only": True, "required": False, "min_length": 6},
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        # Password update
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)

        # User-level fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Profile-level fields
        profile = getattr(instance, "profile", None)
        if profile and profile_data:
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


# =========================================================
# ADMIN — USER PROFILE
# =========================================================
class AdminUserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    photo = serializers.CharField(
        source="photo_base64", required=False, allow_null=True, allow_blank=True
    )
    joined_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "user_id", "email", "full_name", "phone", "photo",
            "bio", "address", "role", "email_verified",
            "joined_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "email", "joined_at", "created_at", "updated_at",
        ]


# =========================================================
# ADMIN — OTP
# =========================================================
class AdminOTPSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = OTPCode
        fields = [
            "id", "user", "email", "code", "purpose",
            "is_used", "expires_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# =========================================================
# ADMIN — USER PREFERENCE
# =========================================================
class AdminUserPreferenceSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserPreference
        fields = [
            "id", "user", "email",
            "language", "timezone",
            "email_notifications", "sms_notifications", "push_notifications",
            "event_notifications", "news_notifications", "chat_notifications",
            "theme", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =========================================================
# ADMIN — VERIFICATION ACTIONS
# =========================================================
class AdminVerifyUserSerializer(serializers.Serializer):
    """Mark a user's email as verified / unverified."""

    verified = serializers.BooleanField(default=True)

    def save(self, **kwargs):
        user = self.context["user"]
        profile = user.profile
        profile.email_verified = self.validated_data["verified"]
        profile.save(update_fields=["email_verified"])
        return profile


class AdminActivateUserSerializer(serializers.Serializer):
    """Enable / disable a user account."""

    is_active = serializers.BooleanField(default=True)

    def save(self, **kwargs):
        user = self.context["user"]
        user.is_active = self.validated_data["is_active"]
        user.save(update_fields=["is_active"])
        return user


class AdminSetRoleSerializer(serializers.Serializer):
    """Change a user's role + staff flag."""

    role = serializers.ChoiceField(choices=[
        ("admin", "Administrator"),
        ("pastor", "Pastor"),
        ("elder", "Church Elder"),
        ("leader", "Ministry Leader"),
        ("member", "Member"),
    ])
    is_staff = serializers.BooleanField(default=False)

    def save(self, **kwargs):
        user = self.context["user"]
        profile = user.profile
        profile.role = self.validated_data["role"]
        profile.save(update_fields=["role"])

        user.is_staff = self.validated_data["is_staff"]
        user.save(update_fields=["is_staff"])
        return profile