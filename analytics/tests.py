import shutil
import tempfile

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Subject, TutorSubject
from students.models import StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin-dashboard",
            email="admin-dashboard@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.student = User.objects.create_user(
            username="student-dashboard",
            email="student-dashboard@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=self.student, full_name="Student Dashboard")

        self.ready_tutor = User.objects.create_user(
            username="ready-tutor",
            email="ready-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=self.ready_tutor, full_name="Ready Tutor", teaches_online=True, hourly_rate=40)
        ready_verification = TutorVerification.objects.create(tutor=self.ready_tutor, status=TutorVerification.Status.APPROVED)
        subject = Subject.objects.create(name="English")
        TutorSubject.objects.create(tutor=self.ready_tutor, subject=subject, level=TutorSubject.Level.PRIMARY)
        VerificationDocument.objects.create(
            verification=ready_verification,
            doc_type=VerificationDocument.DocType.ID,
            file="verification_docs/id.pdf",
        )
        VerificationDocument.objects.create(
            verification=ready_verification,
            doc_type=VerificationDocument.DocType.CERTIFICATE,
            file="verification_docs/certificate.pdf",
        )
        TutorAgreement.objects.create(
            tutor=self.ready_tutor,
            status=TutorAgreement.Status.SIGNED,
            agreed_to_terms=True,
            signed_name="Ready Tutor",
            signed_file="tutor_agreements/signed.pdf",
        )

        self.pending_tutor = User.objects.create_user(
            username="pending-tutor",
            email="pending-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=self.pending_tutor, full_name="Pending Tutor", teaches_online=True, hourly_rate=30)
        TutorVerification.objects.create(tutor=self.pending_tutor, status=TutorVerification.Status.PENDING)

    def test_dashboard_includes_tutor_pipeline_counts(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/analytics/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("tutor_pipeline", response.data)
        self.assertEqual(response.data["tutor_pipeline"]["marketplace_ready_tutors"], 1)
        self.assertEqual(response.data["tutor_pipeline"]["pending_verifications"], 1)
        self.assertEqual(response.data["users"]["total_tutors"], 2)
