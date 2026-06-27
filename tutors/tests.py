import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Course, Lesson, Subject, TutorSubject
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class TutorVerificationDocumentTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.client = APIClient()
        self.tutor = User.objects.create_user(
            username="tutor-docs",
            email="tutor-docs@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Docs", hourly_rate=15, teaches_online=True)
        self.subject = Subject.objects.create(name="Mathematics")
        self.admin = User.objects.create_user(
            username="admin-docs",
            email="admin-docs@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def _upload_document(self, doc_type, name):
        self.client.force_authenticate(self.tutor)
        return self.client.post(
            "/api/tutors/documents/",
            {
                "doc_type": doc_type,
                "file": SimpleUploadedFile(name, b"sample file content", content_type="application/pdf"),
            },
            format="multipart",
        )

    def _upload_signed_agreement(self):
        self.client.force_authenticate(self.tutor)
        return self.client.post(
            "/api/tutors/agreement/",
            {
                "signed_name": "Tutor Docs",
                "agreed_to_terms": True,
                "signed_file": SimpleUploadedFile("signed-agreement.pdf", b"signed agreement", content_type="application/pdf"),
            },
            format="multipart",
        )

    def _add_tutor_subject(self, level=TutorSubject.Level.PRIMARY):
        return TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=level)

    def test_tutor_can_upload_required_documents(self):
        id_response = self._upload_document(VerificationDocument.DocType.ID, "national-id.pdf")
        cert_response = self._upload_document(VerificationDocument.DocType.CERTIFICATE, "certificate.pdf")

        self.assertEqual(id_response.status_code, 201)
        self.assertEqual(cert_response.status_code, 201)

        verification = TutorVerification.objects.get(tutor=self.tutor)
        self.assertTrue(verification.has_required_documents())
        self.assertEqual(verification.documents.count(), 2)

    def test_admin_cannot_approve_without_required_documents(self):
        self._upload_document(VerificationDocument.DocType.ID, "national-id.pdf")

        verification = TutorVerification.objects.get(tutor=self.tutor)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/tutors/verifications/{verification.id}/decide/",
            {"status": TutorVerification.Status.APPROVED, "notes": "Looks good"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["missing_documents"], [VerificationDocument.DocType.CERTIFICATE])

    def test_admin_can_approve_after_required_documents_are_uploaded(self):
        self._upload_document(VerificationDocument.DocType.ID, "national-id.pdf")
        self._upload_document(VerificationDocument.DocType.CERTIFICATE, "certificate.pdf")
        self._add_tutor_subject()
        self._upload_signed_agreement()

        verification = TutorVerification.objects.get(tutor=self.tutor)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/tutors/verifications/{verification.id}/decide/",
            {"status": TutorVerification.Status.APPROVED, "notes": "Approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        verification.refresh_from_db()
        self.assertEqual(verification.status, TutorVerification.Status.APPROVED)


class TutorAgreementTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.client = APIClient()
        self.tutor = User.objects.create_user(
            username="tutor-agreement",
            email="tutor-agreement@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Agreement", hourly_rate=15, teaches_online=True)
        self.subject = Subject.objects.create(name="Physics")
        self.admin = User.objects.create_user(
            username="admin-agreement",
            email="admin-agreement@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def _upload_document(self, doc_type, name):
        self.client.force_authenticate(self.tutor)
        return self.client.post(
            "/api/tutors/documents/",
            {
                "doc_type": doc_type,
                "file": SimpleUploadedFile(name, b"sample file content", content_type="application/pdf"),
            },
            format="multipart",
        )

    def _add_tutor_subject(self, level=TutorSubject.Level.PRIMARY):
        return TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=level)

    def test_tutor_can_download_agreement_template(self):
        self.client.force_authenticate(self.tutor)
        response = self.client.get("/api/tutors/agreement/download/")

        self.assertEqual(response.status_code, 200)


class TutorSetupAndSearchTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.client = APIClient()
        self.student = User.objects.create_user(
            username="student-search",
            email="student-search@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.tutor = User.objects.create_user(
            username="search-tutor",
            email="search-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        self.admin = User.objects.create_user(
            username="search-admin",
            email="search-admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        TutorProfile.objects.create(
            user=self.tutor,
            full_name="Search Tutor",
            headline="Math and science coach",
            bio="Specialist in math lessons.",
            hourly_rate=35,
            teaches_online=True,
        )
        self.subject = Subject.objects.create(name="Mathematics")
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.SECONDARY_UPPER)
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
            signed_name="Search Tutor",
            signed_file="tutor_agreements/signed.pdf",
        )
        course = Course.objects.create(
            tutor=self.tutor,
            title="Algebra Mastery",
            description="Learn quadratic equations.",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=45,
            status=Course.Status.PUBLISHED,
        )
        Lesson.objects.create(course=course, title="Quadratic Basics", topic="Quadratic equations", order_number=1)

    def _upload_document(self, doc_type, name):
        self.client.force_authenticate(self.tutor)
        return self.client.post(
            "/api/tutors/documents/",
            {
                "doc_type": doc_type,
                "file": SimpleUploadedFile(name, b"sample file content", content_type="application/pdf"),
            },
            format="multipart",
        )

    def _add_tutor_subject(self, level=TutorSubject.Level.PRIMARY):
        return TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=level)

    def _upload_signed_agreement(self):
        self.client.force_authenticate(self.tutor)
        return self.client.post(
            "/api/tutors/agreement/",
            {
                "signed_name": "Tutor Agreement",
                "agreed_to_terms": True,
                "signed_file": SimpleUploadedFile("signed-agreement.pdf", b"signed agreement", content_type="application/pdf"),
            },
            format="multipart",
        )

    def test_tutor_setup_checklist_shows_missing_steps_for_new_tutor(self):
        new_tutor = User.objects.create_user(
            username="new-tutor",
            email="new-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=new_tutor, full_name="New Tutor", teaches_online=True)

        self.client.force_authenticate(new_tutor)
        response = self.client.get("/api/tutors/setup/checklist/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["marketplace_ready"])
        self.assertIn("documents", response.data["missing_steps"])
        self.assertIn("agreement", response.data["missing_steps"])
        self.assertIn("approval", response.data["missing_steps"])

    def test_public_tutor_search_supports_name_lesson_topic_and_level(self):
        self.client.force_authenticate(self.student)

        by_name = self.client.get("/api/tutors/?name=Search Tutor")
        by_lesson = self.client.get("/api/tutors/?lesson=Quadratic")
        by_topic = self.client.get("/api/tutors/?topic=Quadratic equations")
        by_level = self.client.get("/api/tutors/?level=SECONDARY_UPPER")

        self.assertEqual(by_name.status_code, 200)
        self.assertEqual(by_lesson.status_code, 200)
        self.assertEqual(by_topic.status_code, 200)
        self.assertEqual(by_level.status_code, 200)

        self.assertEqual(by_name.data[0]["full_name"], "Search Tutor")
        self.assertEqual(by_lesson.data[0]["full_name"], "Search Tutor")
        self.assertEqual(by_topic.data[0]["full_name"], "Search Tutor")
        self.assertEqual(by_level.data[0]["full_name"], "Search Tutor")

    def test_tutor_can_upload_signed_agreement(self):
        self.client.force_authenticate(self.tutor)
        response = self.client.post(
            "/api/tutors/agreement/",
            {
                "signed_name": "Tutor Agreement",
                "agreed_to_terms": True,
                "signed_file": SimpleUploadedFile("signed-agreement.pdf", b"signed agreement", content_type="application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        agreement = TutorAgreement.objects.get(tutor=self.tutor)
        self.assertEqual(agreement.status, TutorAgreement.Status.SIGNED)
        self.assertTrue(agreement.agreed_to_terms)
        self.assertTrue(agreement.signed_file)

    def test_admin_cannot_approve_without_signed_agreement(self):
        incomplete_tutor = User.objects.create_user(
            username="incomplete-tutor",
            email="incomplete-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=incomplete_tutor, full_name="Incomplete Tutor", teaches_online=True)
        verification = TutorVerification.objects.create(tutor=incomplete_tutor, status=TutorVerification.Status.APPROVED)
        TutorSubject.objects.create(tutor=incomplete_tutor, subject=self.subject, level=TutorSubject.Level.PRIMARY)
        VerificationDocument.objects.create(
            verification=verification,
            doc_type=VerificationDocument.DocType.ID,
            file="verification_docs/id.pdf",
        )
        VerificationDocument.objects.create(
            verification=verification,
            doc_type=VerificationDocument.DocType.CERTIFICATE,
            file="verification_docs/certificate.pdf",
        )

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/tutors/verifications/{verification.id}/decide/",
            {"status": TutorVerification.Status.APPROVED, "notes": "Looks good"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.data["agreement_required"])

    def test_admin_can_approve_after_signed_agreement_is_uploaded(self):
        self._upload_document(VerificationDocument.DocType.ID, "national-id.pdf")
        self._upload_document(VerificationDocument.DocType.CERTIFICATE, "certificate.pdf")
        self._add_tutor_subject()
        self.client.force_authenticate(self.tutor)
        self.client.post(
            "/api/tutors/agreement/",
            {
                "signed_name": "Tutor Agreement",
                "agreed_to_terms": True,
                "signed_file": SimpleUploadedFile("signed-agreement.pdf", b"signed agreement", content_type="application/pdf"),
            },
            format="multipart",
        )

        verification = TutorVerification.objects.get(tutor=self.tutor)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/tutors/verifications/{verification.id}/decide/",
            {"status": TutorVerification.Status.APPROVED, "notes": "Approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
