import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str, default_country: str = "255") -> str:
    if not phone:
        return ""
    p = str(phone).strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        return p
    if p.startswith("00"):
        return "+" + p[2:]
    if p.startswith("0"):
        return "+" + default_country + p[1:]
    if p.startswith(default_country):
        return "+" + p
    return "+" + default_country + p


def send_sms(phone: str, message: str) -> dict:
    """
    Send a single SMS via Africa's Talking REST API.
    Returns {"success": bool, "error": str|None, "raw": dict|None}
    """
    if not settings.AT_API_KEY:
        return {"success": False, "error": "AT_API_KEY not configured", "raw": None}

    normalized = _normalize_phone(phone)
    if not normalized:
        return {"success": False, "error": "Invalid phone", "raw": None}

    headers = {
        "apiKey": settings.AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "username": settings.AT_USERNAME,
        "to": normalized,
        "message": message,
    }
    if settings.AT_SENDER_ID:
        data["from"] = settings.AT_SENDER_ID

    try:
        resp = requests.post(
            settings.AT_BASE_URL, headers=headers, data=data, timeout=30
        )
        payload = resp.json() if resp.content else {}
        logger.info("AT response %s: %s", resp.status_code, payload)

        if resp.status_code not in (200, 201):
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}: {payload}",
                "raw": payload,
            }

        recipients = payload.get("SMSMessageData", {}).get("Recipients", [])
        if not recipients:
            return {"success": False, "error": f"No recipients: {payload}", "raw": payload}

        first = recipients[0]
        code = str(first.get("statusCode", ""))
        status = first.get("status", "")
        ok = code in {"100", "101", "102"} or status == "Success"

        return {
            "success": ok,
            "error": None if ok else f"{code} {status}",
            "raw": payload,
        }
    except requests.RequestException as e:
        logger.exception("AT network error")
        return {"success": False, "error": f"Network error: {e}", "raw": None}
    except Exception as e:
        logger.exception("AT unexpected error")
        return {"success": False, "error": f"Unexpected error: {e}", "raw": None}