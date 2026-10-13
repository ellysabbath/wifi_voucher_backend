from django.db import models

# Create your models here.
import uuid
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.db import models
from django.utils import timezone
from core.models import BaseModel


class UserManager(BaseUserManager):
    """Custom manager — email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user — UUID PK, email login."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class UserProfile(BaseModel):
    """Extended profile — one-to-one with User."""

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("pastor", "Pastor"),
        ("elder", "Church Elder"),
        ("leader", "Ministry Leader"),
        ("member", "Member"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    photo_base64 = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    email_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "user_profile"

    def __str__(self):
        return self.full_name


class OTPCode(BaseModel):
    """One-time password (email verification & password reset)."""

    PURPOSE_CHOICES = [
        ("verify", "Email Verification"),
        ("reset", "Password Reset"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "otp_code"
        indexes = [models.Index(fields=["user", "purpose"])]

    def is_valid(self):
        return (not self.is_used) and (timezone.now() < self.expires_at)


class UserPreference(BaseModel):
    """User preferences / notification settings."""

    THEME_CHOICES = [("light", "Light"), ("dark", "Dark"), ("system", "System")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    language = models.CharField(max_length=5, default="en")
    timezone = models.CharField(max_length=50, default="Africa/Dar_es_Salaam")
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
    event_notifications = models.BooleanField(default=True)
    news_notifications = models.BooleanField(default=True)
    chat_notifications = models.BooleanField(default=True)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="light")

    class Meta:
        db_table = "user_preference"