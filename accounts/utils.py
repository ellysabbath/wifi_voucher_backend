import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.html import strip_tags

from .models import OTPCode


# =========================================================
# OTP generation
# =========================================================
def generate_otp(user, purpose):
    """Create a fresh 6-digit OTP valid for 10 minutes."""
    # Invalidate old OTPs for this user+purpose
    OTPCode.objects.filter(
        user=user, purpose=purpose, is_used=False
    ).update(is_used=True)

    code = f"{random.randint(0, 999999):06d}"
    OTPCode.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return code


# =========================================================
# Email payload builder
# =========================================================
def _build_otp_email(user, code, purpose):
    """Return (subject, html_message)."""
    if purpose == "verify":
        subject = "Verify your Bahi SDA account"
        heading = "Email Verification"
        intro = "Use the code below to verify your email address."
    else:
        subject = "Reset your Bahi SDA password"
        heading = "Password Reset"
        intro = "Use the code below to reset your password."

    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:24px;
                border:1px solid #e5e7eb;border-radius:12px;">
      <h2 style="color:#1e40af;margin-top:0;">{heading}</h2>
      <p style="color:#374151;">Hello,</p>
      <p style="color:#374151;">{intro}</p>
      <div style="background:#f3f4f6;padding:16px;border-radius:8px;
                  text-align:center;font-size:32px;font-weight:bold;
                  letter-spacing:8px;color:#111827;margin:20px 0;">
        {code}
      </div>
      <p style="color:#6b7280;font-size:13px;">
        This code expires in 10 minutes. If you didn't request this, ignore this email.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:12px;text-align:center;">
        © 2026 Bahi SDA Church Management System
      </p>
    </div>
    """
    return subject, html_message


# =========================================================
# SMS payload builder
# =========================================================
def _build_otp_sms(code, purpose):
    if purpose == "verify":
        return (
            f"Bahi SDA Church: Your verification code is {code}. "
            f"It expires in 10 minutes."
        )
    return (
        f"Bahi SDA Church: Your password reset code is {code}. "
        f"It expires in 10 minutes."
    )


# =========================================================
# Main entry point — sends email + SMS (both optional-safe)
# =========================================================
def send_otp(user, code, purpose):
    """
    Send the OTP to the user's email AND phone.

    - Email: always attempted.
    - SMS:   attempted if a phone number is on the user's profile
             and AT_API_KEY is configured in settings.

    Never raises unless email fails hard — because in the OTP flow,
    one failing channel shouldn't kill the whole request.
    Returns a dict: {"email": bool, "sms": bool, "errors": [...]}
    """
    result = {"email": False, "sms": False, "errors": []}

    # ----- Email -----
    try:
        subject, html_message = _build_otp_email(user, code, purpose)
        send_mail(
            subject=subject,
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        result["email"] = True
    except Exception as e:
        result["errors"].append(f"email: {e}")

    # ----- SMS -----
    phone = None
    try:
        profile = getattr(user, "profile", None)
        if profile:
            phone = (profile.phone or "").strip()
    except Exception:
        phone = None

    if phone:
        try:
            # Import locally so missing `requests` doesn't crash the whole module
            from sms.africastalking_client import send_sms  # noqa: WPS433

            sms_result = send_sms(phone, _build_otp_sms(code, purpose))
            if sms_result.get("success"):
                result["sms"] = True
            else:
                result["errors"].append(f"sms: {sms_result.get('error')}")
        except Exception as e:
            result["errors"].append(f"sms: {e}")

    return result


# =========================================================
# Back-compat shim — keep old import name working
# =========================================================
def send_otp_email(user, code, purpose):
    """Deprecated alias for `send_otp`. Kept for existing views."""
    return send_otp(user, code, purpose)