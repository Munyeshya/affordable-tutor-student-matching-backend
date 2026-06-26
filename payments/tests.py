from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from bookings.models import Booking
from catalog.models import Course, Subject
from notifications.models import Notification
from students.models import StudentProfile
from tutors.models import TutorProfile, TutorVerification


class PaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student2", email="student2@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Two")
        self.tutor = User.objects.create_user(username="tutor2", email="tutor2@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Two", hourly_rate=20, teaches_online=True)
        TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Physics")
        self.course = Course.objects.create(
            tutor=self.tutor,
            title="Physics Basics",
            description="Intro",
            subject=self.subject,
            price=100,
            status=Course.Status.PUBLISHED,
        )
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
            hourly_rate=20,
            total_amount=20,
        )

    def test_booking_payment_creates_notification_for_tutor(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/payments/bookings/pay/", {"booking_id": self.booking.id}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Notification.objects.filter(user=self.tutor, kind="BOOKING_PAYMENT").count(), 1)
