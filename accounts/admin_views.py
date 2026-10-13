from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserProfileSerializer,
    AdminOTPSerializer,
    AdminUserPreferenceSerializer,
    AdminVerifyUserSerializer,
    AdminActivateUserSerializer,
    AdminSetRoleSerializer,
)
from .models import UserProfile, OTPCode, UserPreference
from .utils import generate_otp, send_otp_email

User = get_user_model()


# =========================================================
# HELPERS
# =========================================================
def _paginate(request, queryset, serializer_class):
    """Simple manual pagination — ?page=1&page_size=20"""
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(200, max(1, int(request.query_params.get("page_size", 20))))
    except (TypeError, ValueError):
        page_size = 20

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = queryset[start:end]

    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "results": serializer_class(items, many=True).data,
    }


# =========================================================
# DASHBOARD STATS
# =========================================================
class AdminDashboardStatsView(APIView):
    """GET /api/admin/accounts/dashboard/stats/"""

    def get(self, request):
        return Response({
            "total_users": User.objects.count(),
            "verified_users": UserProfile.objects.filter(email_verified=True).count(),
            "unverified_users": UserProfile.objects.filter(email_verified=False).count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "staff_users": User.objects.filter(is_staff=True).count(),
            "recent_signups_7d": User.objects.filter(
                date_joined__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        })


# =========================================================
# USERS — LIST + CREATE
# =========================================================
class AdminUserListView(APIView):
    """
    GET  /api/admin/accounts/users/    → list (paginated + filters)
    POST /api/admin/accounts/users/    → create
    """

    def get(self, request):
        qs = User.objects.select_related("profile").all().order_by("-date_joined")

        q = request.query_params.get("q")
        role = request.query_params.get("role")
        verified = request.query_params.get("verified")
        active = request.query_params.get("active")

        if q:
            qs = qs.filter(
                Q(email__icontains=q)
                | Q(profile__full_name__icontains=q)
                | Q(profile__phone__icontains=q)
            )
        if role:
            qs = qs.filter(profile__role=role)
        if verified in {"true", "false"}:
            qs = qs.filter(profile__email_verified=(verified == "true"))
        if active in {"true", "false"}:
            qs = qs.filter(is_active=(active == "true"))

        return Response(_paginate(request, qs, AdminUserListSerializer))

    def post(self, request):
        data = request.data
        email = (data.get("email") or "").lower()
        password = data.get("password")
        full_name = data.get("full_name") or data.get("fullName") or "New User"
        phone = data.get("phone") or ""
        role = data.get("role", "member")
        email_verified = data.get("email_verified", True)

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phone and UserProfile.objects.filter(phone=phone).exists():
            return Response(
                {"detail": "This phone number is already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=data.get("is_active", True),
            is_staff=data.get("is_staff", False),
            is_superuser=data.get("is_superuser", False),
        )
        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            role=role,
            email_verified=bool(email_verified),
        )
        UserPreference.objects.create(user=user)

        return Response(
            AdminUserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# USERS — RETRIEVE / UPDATE / DELETE
# =========================================================
class AdminUserDetailView(APIView):
    """
    GET    /api/admin/accounts/users/<uuid:pk>/
    PUT    /api/admin/accounts/users/<uuid:pk>/
    PATCH  /api/admin/accounts/users/<uuid:pk>/
    DELETE /api/admin/accounts/users/<uuid:pk>/
    """

    def _get_user(self, pk):
        try:
            return User.objects.select_related("profile").get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self._get_user(pk)
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(AdminUserDetailSerializer(user).data)

    def put(self, request, pk):
        user = self._get_user(pk)
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        ser = AdminUserDetailSerializer(user, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def patch(self, request, pk):
        user = self._get_user(pk)
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        ser = AdminUserDetailSerializer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        user = self._get_user(pk)
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        user.delete()
        return Response(
            {"detail": "User deleted."}, status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# USER ACTIONS — one APIView per action
# =========================================================
class AdminUserVerifyView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/verify/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        profile = user.profile
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])
        return Response({"detail": f"{user.email} marked as verified."})


class AdminUserUnverifyView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/unverify/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        profile = user.profile
        profile.email_verified = False
        profile.save(update_fields=["email_verified"])
        return Response({"detail": f"{user.email} marked as unverified."})


class AdminUserActivateView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/activate/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": f"{user.email} activated."})


class AdminUserDeactivateView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/deactivate/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"detail": f"{user.email} deactivated."})


class AdminUserSetRoleView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/set-role/
       Body: { "role": "elder", "is_staff": true }
    """

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        ser = AdminSetRoleSerializer(data=request.data, context={"user": user})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": f"Role for {user.email} updated."})


class AdminUserResendOTPView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/resend-otp/
       Body: { "purpose": "verify" | "reset" }
    """

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        purpose = request.data.get("purpose", "verify")
        if purpose not in {"verify", "reset"}:
            return Response(
                {"detail": "purpose must be 'verify' or 'reset'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = generate_otp(user, purpose)
        try:
            send_otp_email(user, code, purpose)
        except Exception as e:
            return Response(
                {"detail": f"OTP regenerated but email failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"detail": f"New {purpose} OTP sent to {user.email}."})


class AdminUserResetPasswordView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/reset-password/
       Body (optional): { "new_password": "..." }
    """

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        new_password = request.data.get("new_password")
        if not new_password:
            import secrets, string
            alphabet = string.ascii_letters + string.digits
            new_password = "".join(secrets.choice(alphabet) for _ in range(10))

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({
            "detail": f"Password reset for {user.email}.",
            "new_password": new_password,
        })


class AdminUserMakeSuperuserView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/make-superuser/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])
        return Response({"detail": f"{user.email} is now a superuser."})


class AdminUserRemoveSuperuserView(APIView):
    """POST /api/admin/accounts/users/<uuid:pk>/remove-superuser/"""

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        user.is_superuser = False
        user.save(update_fields=["is_superuser"])
        return Response({"detail": f"{user.email} superuser status removed."})


# =========================================================
# PROFILES — CRUD
# =========================================================
class AdminProfileListView(APIView):
    """GET / POST /api/admin/accounts/profiles/"""

    def get(self, request):
        qs = UserProfile.objects.select_related("user").all().order_by("-created_at")

        q = request.query_params.get("q")
        role = request.query_params.get("role")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(user__email__icontains=q)
            )
        if role:
            qs = qs.filter(role=role)

        return Response(_paginate(request, qs, AdminUserProfileSerializer))

    def post(self, request):
        ser = AdminUserProfileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class AdminProfileDetailView(APIView):
    """GET / PUT / PATCH / DELETE /api/admin/accounts/profiles/<uuid:pk>/"""

    def _get(self, pk):
        try:
            return UserProfile.objects.get(pk=pk)
        except UserProfile.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Profile not found."}, status=404)
        return Response(AdminUserProfileSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Profile not found."}, status=404)
        ser = AdminUserProfileSerializer(obj, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Profile not found."}, status=404)
        ser = AdminUserProfileSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Profile not found."}, status=404)
        obj.delete()
        return Response(
            {"detail": "Profile deleted."}, status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# OTPs — LIST / DETAIL / DELETE / PURGE
# =========================================================
class AdminOTPListView(APIView):
    """GET / POST /api/admin/accounts/otps/"""

    def get(self, request):
        qs = OTPCode.objects.select_related("user").all().order_by("-created_at")

        email = request.query_params.get("email")
        purpose = request.query_params.get("purpose")
        is_used = request.query_params.get("is_used")

        if email:
            qs = qs.filter(user__email__icontains=email)
        if purpose:
            qs = qs.filter(purpose=purpose)
        if is_used in {"true", "false"}:
            qs = qs.filter(is_used=(is_used == "true"))

        return Response(_paginate(request, qs, AdminOTPSerializer))

    def post(self, request):
        ser = AdminOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class AdminOTPDetailView(APIView):
    """GET / DELETE /api/admin/accounts/otps/<uuid:pk>/"""

    def _get(self, pk):
        try:
            return OTPCode.objects.get(pk=pk)
        except OTPCode.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "OTP not found."}, status=404)
        return Response(AdminOTPSerializer(obj).data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "OTP not found."}, status=404)
        obj.delete()
        return Response(
            {"detail": "OTP deleted."}, status=status.HTTP_204_NO_CONTENT
        )


class AdminOTPPurgeExpiredView(APIView):
    """POST /api/admin/accounts/otps/purge-expired/"""

    def post(self, request):
        deleted, _ = OTPCode.objects.filter(expires_at__lt=timezone.now()).delete()
        return Response({"detail": f"{deleted} expired OTP(s) removed."})


class AdminOTPPurgeUsedView(APIView):
    """POST /api/admin/accounts/otps/purge-used/"""

    def post(self, request):
        deleted, _ = OTPCode.objects.filter(is_used=True).delete()
        return Response({"detail": f"{deleted} used OTP(s) removed."})


# =========================================================
# PREFERENCES — LIST / DETAIL
# =========================================================
class AdminPreferenceListView(APIView):
    """GET / POST /api/admin/accounts/preferences/"""

    def get(self, request):
        qs = UserPreference.objects.select_related("user").all().order_by("-created_at")
        return Response(_paginate(request, qs, AdminUserPreferenceSerializer))

    def post(self, request):
        ser = AdminUserPreferenceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class AdminPreferenceDetailView(APIView):
    """GET / PUT / PATCH / DELETE /api/admin/accounts/preferences/<uuid:pk>/"""

    def _get(self, pk):
        try:
            return UserPreference.objects.get(pk=pk)
        except UserPreference.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Preference not found."}, status=404)
        return Response(AdminUserPreferenceSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Preference not found."}, status=404)
        ser = AdminUserPreferenceSerializer(obj, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Preference not found."}, status=404)
        ser = AdminUserPreferenceSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Preference not found."}, status=404)
        obj.delete()
        return Response(
            {"detail": "Preference deleted."}, status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# BULK OPS
# =========================================================
class AdminBulkVerifyView(APIView):
    """POST /api/admin/accounts/bulk/verify/   Body: { "user_ids": [...] }"""

    def post(self, request):
        ids = request.data.get("user_ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "user_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = UserProfile.objects.filter(user_id__in=ids).update(
            email_verified=True
        )
        return Response({"detail": f"{updated} user(s) verified."})


class AdminBulkActivateView(APIView):
    """POST /api/admin/accounts/bulk/activate/
       Body: { "user_ids": [...], "is_active": true }
    """

    def post(self, request):
        ids = request.data.get("user_ids", [])
        is_active = bool(request.data.get("is_active", True))
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "user_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = User.objects.filter(id__in=ids).update(is_active=is_active)
        return Response({
            "detail": f"{updated} user(s) "
                      f"{'activated' if is_active else 'deactivated'}."
        })