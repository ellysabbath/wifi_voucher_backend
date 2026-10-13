from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view, permission_classes, authentication_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode, UserProfile
from .serializers import (
    RegisterSerializer, OTPVerifySerializer, OTPResendSerializer,
    LoginSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UserProfileSerializer,
)
from .utils import generate_otp, send_otp_email

User = get_user_model()


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# =========================================================
# REGISTER  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])          # ← no JWT needed
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    code = generate_otp(user, "verify")
    try:
        send_otp_email(user, code, "verify")
    except Exception as e:
        return Response(
            {"detail": f"Account created but email failed: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {"detail": "Account created. Check your email for the 6-digit code.",
         "email": user.email},
        status=status.HTTP_201_CREATED,
    )


# =========================================================
# VERIFY EMAIL  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_otp_view(request):
    serializer = OTPVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].lower()
    code = serializer.validated_data["code"]

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"detail": "Invalid email."}, status=status.HTTP_400_BAD_REQUEST)

    otp = OTPCode.objects.filter(
        user=user, code=code, purpose="verify", is_used=False
    ).order_by("-created_at").first()

    if not otp or not otp.is_valid():
        return Response({"detail": "Invalid or expired code."},
                        status=status.HTTP_400_BAD_REQUEST)

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    profile = user.profile
    profile.email_verified = True
    profile.save(update_fields=["email_verified"])

    return Response({"detail": "Email verified successfully.", **_tokens_for_user(user)})


# =========================================================
# RESEND OTP  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def resend_otp_view(request):
    serializer = OTPResendSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].lower()
    purpose = serializer.validated_data["purpose"]

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"detail": "If that email exists, a code was sent."})

    code = generate_otp(user, purpose)
    send_otp_email(user, code, purpose)
    return Response({"detail": "A new code has been sent."})


# =========================================================
# LOGIN  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].lower()
    password = serializer.validated_data["password"]

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({"detail": "Account is disabled."}, status=status.HTTP_403_FORBIDDEN)

    if hasattr(user, "profile") and not user.profile.email_verified:
        code = generate_otp(user, "verify")
        try:
            send_otp_email(user, code, "verify")
        except Exception:
            pass
        return Response(
            {"detail": "Email not verified. A new code was sent.",
             "needs_verification": True, "email": user.email},
            status=status.HTTP_403_FORBIDDEN,
        )

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return Response({"detail": "Login successful.", **_tokens_for_user(user)})


# =========================================================
# FORGOT PASSWORD  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password_view(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].lower()

    try:
        user = User.objects.get(email__iexact=email)
        code = generate_otp(user, "reset")
        send_otp_email(user, code, "reset")
    except User.DoesNotExist:
        pass

    return Response({"detail": "If that email exists, a reset code was sent."})


# =========================================================
# RESET PASSWORD  (PUBLIC)
# =========================================================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def reset_password_view(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"].lower()
    code = serializer.validated_data["code"]
    new_password = serializer.validated_data["password"]

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)

    otp = OTPCode.objects.filter(
        user=user, code=code, purpose="reset", is_used=False
    ).order_by("-created_at").first()

    if not otp or not otp.is_valid():
        return Response({"detail": "Invalid or expired code."},
                        status=status.HTTP_400_BAD_REQUEST)

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    user.set_password(new_password)
    user.save(update_fields=["password"])

    return Response({"detail": "Password reset successful. You can now log in."})


# =========================================================
# PROFILE  (GET + PATCH — authenticated, keeps JWT)
# =========================================================
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_view(request):
    # Ensure the user has a profile
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        return Response(
            {"detail": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # GET → return current profile
    if request.method == "GET":
        return Response(UserProfileSerializer(profile).data)

    # PATCH → partial update
    serializer = UserProfileSerializer(
        profile,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(
        {
            "detail": "Profile updated successfully.",
            **serializer.data,
        },
        status=status.HTTP_200_OK,
    )