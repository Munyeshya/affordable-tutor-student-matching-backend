from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from notifications.models import Notification


class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="notify-user",
            email="notify-user@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.other = User.objects.create_user(
            username="notify-other",
            email="notify-other@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        Notification.objects.create(user=self.user, title="Unread one", body="Body", actor=self.other, kind="A")
        Notification.objects.create(user=self.user, title="Unread two", body="Body", actor=self.other, kind="B")
        read_notification = Notification.objects.create(user=self.user, title="Read one", body="Body", actor=self.other, kind="C", is_read=True)
        read_notification.read_at = read_notification.created_at
        read_notification.save(update_fields=["read_at"])

    def test_unread_filter_returns_only_unread_notifications(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/notifications/?unread=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item["is_read"] is False for item in response.data))

    def test_mark_all_read_updates_only_unread_notifications(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/notifications/read-all/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)
