from django.utils import timezone

from notifications.models import Notification


def create_notification(*, user, title, body, actor=None, link="", kind=""):
    return Notification.objects.create(
        user=user,
        title=title,
        body=body,
        actor=actor,
        link=link,
        kind=kind,
    )


def mark_notification_read(notification):
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at", "updated_at"])

