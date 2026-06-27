import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
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

    def test_tutor_can_download_agreement_template(self):
        self.client.force_authenticate(self.tutor)
        response = self.client.get("/api/tutors/agreement/download/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tutor Agreement", response.content.decode())

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
        self._upload_document(VerificationDocument.DocType.ID, "national-id.pdf")
        self._upload_document(VerificationDocument.DocType.CERTIFICATE, "certificate.pdf")

        verification = TutorVerification.objects.get(tutor=self.tutor)
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
