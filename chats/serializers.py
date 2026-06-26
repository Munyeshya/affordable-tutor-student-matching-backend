from django.utils import timezone
from rest_framework import serializers

from chats.models import Message
from notifications.utils import create_notification


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    receiver_name = serializers.CharField(source="receiver.get_full_name", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "booking",
            "sender",
            "sender_name",
            "receiver",
            "receiver_name",
            "message",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "booking", "sender", "receiver", "is_read", "read_at", "created_at", "updated_at")


class MessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField()

    def create(self, validated_data):
        booking = self.context["booking"]
        sender = self.context["request"].user
        receiver = booking.tutor if sender.id == booking.student_id else booking.student
        message = Message.objects.create(booking=booking, sender=sender, receiver=receiver, message=validated_data["message"])
        create_notification(
            user=receiver,
            actor=sender,
            title="New message",
            body=validated_data["message"][:120],
            link=f"/api/chats/bookings/{booking.id}/messages/",
            kind="CHAT_MESSAGE",
        )
        return message


class MessageReadSerializer(serializers.Serializer):
    message_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def update(self, instance, validated_data):
        ids = validated_data["message_ids"]
        messages = instance.filter(id__in=ids, receiver=self.context["request"].user, is_read=False)
        messages.update(is_read=True, read_at=timezone.now())
        return messages
