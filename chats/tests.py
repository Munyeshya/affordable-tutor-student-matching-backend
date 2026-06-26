from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from bookings.models import Booking
from catalog.models import Subject
from notifications.models import Notification
from students.models import StudentProfile
from tutors.models import TutorProfile, TutorVerification


class ChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student3", email="student3@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Three")
        self.tutor = User.objects.create_user(username="tutor3", email="tutor3@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Three", hourly_rate=20, teaches_online=True)
        TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Chemistry")
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)
        self.booking = Booking.objects.create(
            student=self.student,
            tutor=self.tutor,
            subject=self.subject,
            start_datetime=start,
            end_datetime=end,
            mode="ONLINE",
            status=Booking.Status.CONFIRMED,
        )

    def test_message_creates_notification_for_receiver(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            f"/api/chats/bookings/{self.booking.id}/messages/",
            {"message": "Hello tutor"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Notification.objects.filter(user=self.tutor, kind="CHAT_MESSAGE").count(), 1)

