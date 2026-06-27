from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from availability.models import AvailabilitySlot
from students.models import StudentProfile
from catalog.models import Subject, TutorSubject
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class AvailabilityAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student-availability", email="student-availability@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Availability")
        self.approved_tutor = User.objects.create_user(username="approved-availability", email="approved-availability@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.approved_tutor, full_name="Approved Tutor", hourly_rate=20, teaches_online=True)
        approved_verification = TutorVerification.objects.create(tutor=self.approved_tutor, status=TutorVerification.Status.APPROVED)
        approved_subject = Subject.objects.create(name="Biology")
        TutorSubject.objects.create(tutor=self.approved_tutor, subject=approved_subject, level=TutorSubject.Level.UNIVERSITY)
        VerificationDocument.objects.create(
            verification=approved_verification,
            doc_type=VerificationDocument.DocType.ID,
            file="verification_docs/id.pdf",
        )
        VerificationDocument.objects.create(
            verification=approved_verification,
            doc_type=VerificationDocument.DocType.CERTIFICATE,
            file="verification_docs/certificate.pdf",
        )
        TutorAgreement.objects.create(
            tutor=self.approved_tutor,
            status=TutorAgreement.Status.SIGNED,
            agreed_to_terms=True,
            signed_name="Approved Tutor",
            signed_file="tutor_agreements/example.pdf",
        )

        self.unapproved_tutor = User.objects.create_user(username="unapproved-availability", email="unapproved-availability@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.unapproved_tutor, full_name="Hidden Tutor", hourly_rate=20, teaches_online=True)
        TutorVerification.objects.create(tutor=self.unapproved_tutor, status=TutorVerification.Status.PENDING)

        start = timezone.now() + timedelta(days=1)
        AvailabilitySlot.objects.create(tutor=self.approved_tutor, start_datetime=start, end_datetime=start + timedelta(hours=1), mode=AvailabilitySlot.Mode.ONLINE)
        AvailabilitySlot.objects.create(tutor=self.unapproved_tutor, start_datetime=start, end_datetime=start + timedelta(hours=1), mode=AvailabilitySlot.Mode.ONLINE)

    def test_public_availability_hides_unapproved_tutors(self):
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/availability/?tutor=%s" % self.unapproved_tutor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_public_availability_shows_approved_tutors(self):
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/availability/?tutor=%s" % self.approved_tutor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
