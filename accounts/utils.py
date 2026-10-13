import random
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from .models import OTPCode


def generate_otp(user, purpose):
    """Create a fresh 6-digit OTP valid for 10 minutes."""
    # Invalidate old OTPs for this user+purpose
    OTPCode.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    code = f"{random.randint(0, 999999):06d}"
    OTPCode.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return code


def send_otp_email(user, code, purpose):
    """Send OTP via Gmail SMTP."""
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

    send_mail(
        subject=subject,
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )