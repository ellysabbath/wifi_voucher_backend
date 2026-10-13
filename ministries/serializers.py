from rest_framework import serializers

from .models import Ministry


class MinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ministry
        fields = [
            "id",
            "name",
            "description",
            "leader_name",
            "meeting_day",
            "meeting_time",
            "icon",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()

    def validate(self, attrs):
        # Unique name check (case-insensitive) — only if creating or renaming
        name = attrs.get("name")
        if name:
            qs = Ministry.objects.filter(name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A ministry with this name already exists."}
                )
        return attrs