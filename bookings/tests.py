from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from availability.models import AvailabilitySlot
from catalog.models import Subject, TutorSubject
from notifications.models import Notification
from students.models import StudentProfile
from tutors.models import TutorProfile, TutorVerification


class BookingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student1", email="student1@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student One")
        self.tutor = User.objects.create_user(username="tutor1", email="tutor1@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor One", hourly_rate=10, teaches_online=True, teaches_in_person=False)
        TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Mathematics")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level="Basic")
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=1)
        AvailabilitySlot.objects.create(
            tutor=self.tutor,
            start_datetime=self.start,
            end_datetime=self.end,
            mode=AvailabilitySlot.Mode.ONLINE,
        )

    def test_booking_creates_notification_for_tutor(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/bookings/create/",
            {
                "tutor_id": self.tutor.id,
                "subject_id": self.subject.id,
                "start_datetime": self.start.isoformat(),
                "end_datetime": self.end.isoformat(),
                "mode": "ONLINE",
                "notes": "Need help",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Notification.objects.filter(user=self.tutor, kind="BOOKING_CREATED").count(), 1)
