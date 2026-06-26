from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "body",
            "link",
            "kind",
            "is_read",
            "read_at",
            "actor",
            "actor_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

