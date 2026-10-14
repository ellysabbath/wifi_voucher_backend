from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .africastalking_client import send_sms
from .models import SMSGroup, SMSGroupMember, SMSMessage, SMSRecipient
from .serializers import (
    SMSGroupSerializer,
    SMSGroupCreateSerializer,
    SMSMessageSerializer,
    SMSMessageDetailSerializer,
    SendSMSSerializer,
)

User = get_user_model()


def _paginate(request, queryset, serializer_class):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(200, max(1, int(request.query_params.get("page_size", 50))))
    except (TypeError, ValueError):
        page_size = 50
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "results": serializer_class(queryset[start:end], many=True).data,
    }


def _resolve_sender(request):
    if request.user and request.user.is_authenticated:
        return request.user
    return (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
        or User.objects.first()
    )


# =========================================================
# GROUPS
# =========================================================
class SMSGroupListView(APIView):
    def get(self, request):
        qs = SMSGroup.objects.prefetch_related(
            "members", "members__user", "members__user__profile"
        ).order_by("name")
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return Response(_paginate(request, qs, SMSGroupSerializer))

    def post(self, request):
        ser = SMSGroupCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        group = ser.save()
        return Response(SMSGroupSerializer(group).data, status=status.HTTP_201_CREATED)


class SMSGroupDetailView(APIView):
    def _get(self, pk):
        try:
            return SMSGroup.objects.prefetch_related(
                "members", "members__user", "members__user__profile"
            ).get(pk=pk)
        except SMSGroup.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Group not found."}, status=404)
        return Response(SMSGroupSerializer(obj).data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Group not found."}, status=404)
        obj.delete()
        return Response({"detail": "Group deleted."}, status=status.HTTP_204_NO_CONTENT)


# =========================================================
# MESSAGES
# =========================================================
class SMSMessageListView(APIView):
    def get(self, request):
        qs = SMSMessage.objects.select_related("sent_by").order_by("-created_at")
        return Response(_paginate(request, qs, SMSMessageSerializer))


class SMSMessageDetailView(APIView):
    def get(self, request, pk):
        try:
            obj = SMSMessage.objects.prefetch_related("recipients").get(pk=pk)
        except SMSMessage.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        return Response(SMSMessageDetailSerializer(obj).data)


# =========================================================
# SEND
# =========================================================
class SendSMSView(APIView):
    def post(self, request):
        ser = SendSMSSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        mode = data["mode"]
        channels = set(data["channels"])
        message_text = data["message"]
        subject = data.get("subject") or "Church Notice"

        users_qs = User.objects.select_related("profile").filter(is_active=True)

        if mode == "all":
            recipients = list(users_qs)
            group_label = "All Users"
        elif mode == "group":
            group = SMSGroup.objects.filter(id=data["group_id"]).first()
            if not group:
                return Response({"detail": "Group not found."}, status=404)
            ids = list(
                SMSGroupMember.objects.filter(group=group).values_list(
                    "user_id", flat=True
                )
            )
            recipients = list(users_qs.filter(id__in=ids))
            group_label = group.name
        else:
            recipients = list(users_qs.filter(id__in=data["user_ids"]))
            group_label = "Selected Users"

        if not recipients:
            return Response({"detail": "No recipients."}, status=400)

        campaign = SMSMessage.objects.create(
            message=message_text,
            subject=subject,
            group_name=group_label,
            status="pending",
            sent_by=_resolve_sender(request),
            recipient_count=len(recipients),
        )

        sms_ok = email_ok = failed = 0

        for user in recipients:
            profile = getattr(user, "profile", None)
            phone = (profile.phone if profile else "") or ""
            email = user.email or ""

            rec = SMSRecipient.objects.create(
                sms_message=campaign, user=user, phone=phone, email=email
            )

            # ----- SMS -----
            if "sms" in channels:
                if not phone:
                    rec.sms_status = "failed"
                    rec.sms_error = "No phone number"
                    failed += 1
                else:
                    result = send_sms(phone, message_text)
                    if result.get("success"):
                        rec.sms_status = "sent"
                        rec.sms_sent_at = timezone.now()
                        sms_ok += 1
                    else:
                        rec.sms_status = "failed"
                        rec.sms_error = result.get("error", "Unknown")
                        failed += 1

            # ----- Email -----
            if "email" in channels:
                if not email:
                    rec.email_status = "failed"
                    rec.email_error = "No email"
                    if "sms" not in channels:
                        failed += 1
                else:
                    try:
                        sent = send_mail(
                            subject=subject,
                            message=message_text,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        if sent > 0:
                            rec.email_status = "sent"
                            rec.email_sent_at = timezone.now()
                            email_ok += 1
                        else:
                            rec.email_status = "failed"
                            rec.email_error = "send_mail returned 0"
                            if "sms" not in channels:
                                failed += 1
                    except Exception as e:
                        rec.email_status = "failed"
                        rec.email_error = str(e)
                        if "sms" not in channels:
                            failed += 1

            rec.save()

        total_attempts = len(recipients) * len(channels)
        total_success = sms_ok + email_ok
        if total_success == total_attempts:
            campaign.status = "sent"
        elif total_success == 0:
            campaign.status = "failed"
        else:
            campaign.status = "partial"

        campaign.sms_sent_count = sms_ok
        campaign.email_sent_count = email_ok
        campaign.failed_count = failed
        campaign.save()

        return Response(
            {
                "detail": "Campaign dispatched.",
                "campaign": SMSMessageSerializer(campaign).data,
            },
            status=status.HTTP_201_CREATED,
        )