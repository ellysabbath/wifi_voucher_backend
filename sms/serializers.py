from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import SMSGroup, SMSGroupMember, SMSMessage, SMSRecipient

User = get_user_model()


class SMSGroupMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.profile.full_name", read_only=True)
    phone = serializers.CharField(source="user.profile.phone", read_only=True)

    class Meta:
        model = SMSGroupMember
        fields = ["id", "user_id", "email", "full_name", "phone"]


class SMSGroupSerializer(serializers.ModelSerializer):
    members = SMSGroupMemberSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = SMSGroup
        fields = [
            "id", "name", "description", "created_by_email",
            "members", "member_count", "created_at", "updated_at",
        ]

    def get_member_count(self, obj):
        return obj.members.count()


class SMSGroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    user_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)

    def validate_name(self, value):
        if SMSGroup.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Group name already exists.")
        return value.strip()

    def create(self, validated_data):
        user_ids = validated_data.pop("user_ids")
        request = self.context.get("request")
        creator = (
            request.user
            if request and request.user and request.user.is_authenticated
            else User.objects.filter(is_superuser=True).first()
        )
        group = SMSGroup.objects.create(created_by=creator, **validated_data)
        for uid in user_ids:
            SMSGroupMember.objects.create(group=group, user_id=uid)
        return group


class SMSRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSRecipient
        fields = [
            "id", "user", "phone", "email",
            "sms_status", "email_status",
            "sms_error", "email_error",
            "sms_sent_at", "email_sent_at",
        ]


class SMSMessageSerializer(serializers.ModelSerializer):
    sent_by_email = serializers.EmailField(source="sent_by.email", read_only=True)

    class Meta:
        model = SMSMessage
        fields = [
            "id", "message", "subject", "group_name", "status",
            "sent_by_email", "recipient_count",
            "sms_sent_count", "email_sent_count", "failed_count",
            "created_at", "updated_at",
        ]


class SMSMessageDetailSerializer(SMSMessageSerializer):
    recipients = SMSRecipientSerializer(many=True, read_only=True)

    class Meta(SMSMessageSerializer.Meta):
        fields = SMSMessageSerializer.Meta.fields + ["recipients"]


class SendSMSSerializer(serializers.Serializer):
    message = serializers.CharField()
    subject = serializers.CharField(required=False, allow_blank=True)
    mode = serializers.ChoiceField(choices=["all", "group", "selected"])
    group_id = serializers.UUIDField(required=False, allow_null=True)
    user_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=["sms", "email"]),
        allow_empty=False,
    )

    def validate(self, attrs):
        if attrs["mode"] == "group" and not attrs.get("group_id"):
            raise serializers.ValidationError({"group_id": "Required for group mode."})
        if attrs["mode"] == "selected" and not attrs.get("user_ids"):
            raise serializers.ValidationError({"user_ids": "Required for selected mode."})
        return attrs