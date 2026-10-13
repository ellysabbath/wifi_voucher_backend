from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from .models import UserProfile, OTPCode, UserPreference

User = get_user_model()


# =========================================================
# REGISTRATION
# =========================================================
class RegisterSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=6)
    confirmPassword = serializers.CharField(write_only=True)
    photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_phone(self, value):
        if UserProfile.objects.filter(phone=value).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmPassword"]:
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirmPassword")
        photo = validated_data.pop("photo", None)
        full_name = validated_data.pop("fullName")
        phone = validated_data.pop("phone")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=True,
        )
        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            photo_base64=photo,
            email_verified=False,
        )
        UserPreference.objects.create(user=user)
        return user


# =========================================================
# OTP
# =========================================================
class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class OTPResendSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=["verify", "reset"])


# =========================================================
# LOGIN
# =========================================================
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# =========================================================
# PASSWORD RESET
# =========================================================
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    password = serializers.CharField(write_only=True, min_length=6)
    confirmPassword = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmPassword"]:
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match."})
        return attrs


# =========================================================
# PROFILE (read)
# =========================================================
# =========================================================
# PROFILE (read + partial update)
# =========================================================
class UserProfileSerializer(serializers.ModelSerializer):
    # Expose email as read-only via the related user
    email = serializers.EmailField(source="user.email", read_only=True)

    # Accept "photo" from the frontend, store into "photo_base64"
    photo = serializers.CharField(
        source="photo_base64",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    # Expose created_at as "joined_at" for the frontend
    joined_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "email", "full_name", "phone", "photo",
            "bio", "address", "role", "email_verified",
            "joined_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "email", "role", "email_verified",
            "joined_at", "created_at", "updated_at",
        ]

    def validate_phone(self, value):
        """Ensure phone is unique, but allow the current user to keep their own."""
        qs = UserProfile.objects.filter(phone=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value