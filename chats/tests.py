from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from bookings.models import Booking
from catalog.models import Subject, TutorSubject
from notifications.models import Notification
from students.models import StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class ChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student3", email="student3@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Three")
        self.tutor = User.objects.create_user(username="tutor3", email="tutor3@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Three", hourly_rate=20, teaches_online=True)
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Chemistry")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.SECONDARY_LOWER)
        VerificationDocument.objects.create(verification=verification, doc_type=VerificationDocument.DocType.ID, file="verification_docs/id.pdf")
        VerificationDocument.objects.create(
            verification=verification,
            doc_type=VerificationDocument.DocType.CERTIFICATE,
            file="verification_docs/certificate.pdf",
        )
        TutorAgreement.objects.create(
            tutor=self.tutor,
            status=TutorAgreement.Status.SIGNED,
            agreed_to_terms=True,
            signed_name="Tutor Three",
            signed_file="tutor_agreements/signed.pdf",
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

    def test_chat_threads_show_latest_message_and_unread_count(self):
        self.client.force_authenticate(self.student)
        self.client.post(
            f"/api/chats/bookings/{self.booking.id}/messages/",
            {"message": "First message"},
            format="json",
        )
        self.client.force_authenticate(self.tutor)
        self.client.post(
            f"/api/chats/bookings/{self.booking.id}/messages/",
            {"message": "Reply message"},
            format="json",
        )

        self.client.force_authenticate(self.student)
        response = self.client.get("/api/chats/threads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["booking_id"], self.booking.id)
        self.assertEqual(response.data[0]["last_message"], "Reply message")
        self.assertEqual(response.data[0]["unread_count"], 1)
