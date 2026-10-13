from django.urls import path

from . import admin_views as v

app_name = "accounts-admin"

urlpatterns = [
    # ---------- Dashboard ----------
    path("dashboard/stats/", v.AdminDashboardStatsView.as_view(), name="dashboard-stats"),

    # ---------- Users ----------
    path("users/", v.AdminUserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", v.AdminUserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/verify/", v.AdminUserVerifyView.as_view(), name="user-verify"),
    path("users/<uuid:pk>/unverify/", v.AdminUserUnverifyView.as_view(), name="user-unverify"),
    path("users/<uuid:pk>/activate/", v.AdminUserActivateView.as_view(), name="user-activate"),
    path("users/<uuid:pk>/deactivate/", v.AdminUserDeactivateView.as_view(), name="user-deactivate"),
    path("users/<uuid:pk>/set-role/", v.AdminUserSetRoleView.as_view(), name="user-set-role"),
    path("users/<uuid:pk>/resend-otp/", v.AdminUserResendOTPView.as_view(), name="user-resend-otp"),
    path("users/<uuid:pk>/reset-password/", v.AdminUserResetPasswordView.as_view(), name="user-reset-password"),
    path("users/<uuid:pk>/make-superuser/", v.AdminUserMakeSuperuserView.as_view(), name="user-make-superuser"),
    path("users/<uuid:pk>/remove-superuser/", v.AdminUserRemoveSuperuserView.as_view(), name="user-remove-superuser"),

    # ---------- Profiles ----------
    path("profiles/", v.AdminProfileListView.as_view(), name="profile-list"),
    path("profiles/<uuid:pk>/", v.AdminProfileDetailView.as_view(), name="profile-detail"),

    # ---------- OTPs ----------
    path("otps/", v.AdminOTPListView.as_view(), name="otp-list"),
    path("otps/<uuid:pk>/", v.AdminOTPDetailView.as_view(), name="otp-detail"),
    path("otps/purge-expired/", v.AdminOTPPurgeExpiredView.as_view(), name="otp-purge-expired"),
    path("otps/purge-used/", v.AdminOTPPurgeUsedView.as_view(), name="otp-purge-used"),

    # ---------- Preferences ----------
    path("preferences/", v.AdminPreferenceListView.as_view(), name="preference-list"),
    path("preferences/<uuid:pk>/", v.AdminPreferenceDetailView.as_view(), name="preference-detail"),

    # ---------- Bulk ----------
    path("bulk/verify/", v.AdminBulkVerifyView.as_view(), name="bulk-verify"),
    path("bulk/activate/", v.AdminBulkActivateView.as_view(), name="bulk-activate"),
]