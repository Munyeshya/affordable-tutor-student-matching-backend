from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from bookings.models import Booking
from catalog.models import Course, Subject
from notifications.models import Notification
from students.models import StudentProfile
from catalog.models import TutorSubject
from payments.models import Payout, PayoutDecision
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class PaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student2", email="student2@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Two")
        self.tutor = User.objects.create_user(username="tutor2", email="tutor2@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Two", hourly_rate=20, teaches_online=True)
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Physics")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.UNIVERSITY)
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
            signed_name="Tutor Two",
            signed_file="tutor_agreements/signed.pdf",
        )
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


class PayoutAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tutor = User.objects.create_user(username="tutor-payout", email="tutor-payout@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Payout", hourly_rate=20, teaches_online=True)
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Economics")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.UNIVERSITY)
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
            signed_name="Tutor Payout",
            signed_file="tutor_agreements/signed.pdf",
        )
        self.admin = User.objects.create_user(
            username="admin-payout",
            email="admin-payout@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.payout = Payout.objects.create(tutor=self.tutor, amount=250, status=Payout.Status.REQUESTED)

    def test_admin_rejection_requires_reason_and_writes_history(self):
        self.client.force_authenticate(self.admin)
        missing_reason_response = self.client.patch(
            f"/api/payments/payouts/{self.payout.id}/decide/",
            {"status": Payout.Status.REJECTED},
            format="json",
        )

        self.assertEqual(missing_reason_response.status_code, 400)
        self.assertIn("reason", missing_reason_response.data)

        reason = "Bank details need to be confirmed."
        reject_response = self.client.patch(
            f"/api/payments/payouts/{self.payout.id}/decide/",
            {"status": Payout.Status.REJECTED, "reason": reason},
            format="json",
        )

        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(PayoutDecision.objects.filter(payout=self.payout, status=Payout.Status.REJECTED, reason=reason).count(), 1)
        self.assertEqual(reject_response.data["decisions"][0]["reason"], reason)

    def test_tutor_can_view_payout_decision_history(self):
        PayoutDecision.objects.create(
            payout=self.payout,
            admin=self.admin,
            status=Payout.Status.APPROVED,
            reason="Approved after review.",
        )

        self.client.force_authenticate(self.tutor)
        response = self.client.get(f"/api/payments/payouts/{self.payout.id}/history/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["reason"], "Approved after review.")
