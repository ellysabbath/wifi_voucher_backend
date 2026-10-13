"""
Base64 helpers — used across all file-upload models.
"""
import base64
import binascii
from django.core.exceptions import ValidationError

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def file_to_base64(uploaded_file):
    """Convert an InMemoryUploadedFile to a base64 data string."""
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError("File exceeds 10 MB limit.")
    return base64.b64encode(uploaded_file.read()).decode("utf-8")


def base64_to_bytes(b64_string):
    """Decode a base64 string to raw bytes."""
    if not b64_string:
        return b""
    try:
        return base64.b64decode(b64_string)
    except (binascii.Error, ValueError):
        raise ValidationError("Invalid base64 string.")


def base64_data_url(b64_string, mime="image/jpeg"):
    """Build a data URL from a base64 string (for frontend use)."""
    if not b64_string:
        return None
    return f"data:{mime};base64,{b64_string}"