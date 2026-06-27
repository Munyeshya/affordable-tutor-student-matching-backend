import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from PIL import Image

from accounts.models import User
from catalog.models import Course, CourseModerationDecision, Lesson, Subject, TutorSubject
from students.models import StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class CatalogAccessTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.client = APIClient()
        self.student = User.objects.create_user(username="student-catalog", email="student-catalog@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Catalog")
        self.tutor = User.objects.create_user(username="tutor-catalog", email="tutor-catalog@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Catalog", hourly_rate=25, teaches_online=True)
        self.subject = Subject.objects.create(name="Chemistry")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.SECONDARY_UPPER)

    def _build_test_image(self, name="thumbnail.png"):
        image = Image.new("RGB", (2, 2), color=(255, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_tutor_can_create_draft_course_before_approval(self):
        self.client.force_authenticate(self.tutor)
        response = self.client.post(
            "/api/catalog/courses/create/",
            {
                "title": "Chemistry Basics",
                "description": "Intro",
                "subject": self.subject.id,
                "academic_level": "SECONDARY_UPPER",
                "price": "50.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], Course.Status.DRAFT)
        self.assertEqual(Course.objects.filter(tutor=self.tutor, title="Chemistry Basics").count(), 1)
        self.assertIsNone(response.data["thumbnail_url"])
        self.assertFalse(response.data["has_thumbnail"])

    def test_tutor_can_upload_course_thumbnail_and_lesson_media(self):
        self.client.force_authenticate(self.tutor)
        course_response = self.client.post(
            "/api/catalog/courses/create/",
            {
                "title": "Chemistry Media",
                "description": "Media rich course",
                "subject": self.subject.id,
                "academic_level": "SECONDARY_UPPER",
                "price": "75.00",
                "thumbnail": self._build_test_image(),
            },
            format="multipart",
        )

        self.assertEqual(course_response.status_code, 201, course_response.data)
        self.assertTrue(course_response.data["has_thumbnail"])
        self.assertTrue(course_response.data["thumbnail_url"].endswith(".png"))

        course = Course.objects.get(pk=course_response.data["id"])
        lesson_response = self.client.post(
            f"/api/catalog/courses/{course.id}/lessons/",
            {
                "title": "Video Lesson",
                "topic": "Atoms",
                "description": "Video lesson",
                "order_number": 1,
                "is_preview": True,
                "video_file": SimpleUploadedFile("lesson.mp4", b"fake-video-data", content_type="video/mp4"),
            },
            format="multipart",
        )

        self.assertEqual(lesson_response.status_code, 201, lesson_response.data)
        self.assertTrue(lesson_response.data["has_video_file"])
        self.assertTrue(lesson_response.data["video_file_url"].endswith("lesson.mp4"))

    def test_tutor_can_manage_lessons_inside_their_account(self):
        course = Course.objects.create(
            tutor=self.tutor,
            title="Chemistry Basics",
            description="Intro",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=50,
        )

        self.client.force_authenticate(self.tutor)
        response = self.client.post(
            f"/api/catalog/courses/{course.id}/lessons/",
            {
                "title": "Atoms and Elements",
                "topic": "Atoms",
                "description": "Lesson draft",
                "order_number": 1,
                "is_preview": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Lesson.objects.filter(course=course, title="Atoms and Elements").count(), 1)

    def test_tutor_can_view_their_course_drafts(self):
        Course.objects.create(
            tutor=self.tutor,
            title="Chemistry Draft",
            description="Draft",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=50,
        )

        self.client.force_authenticate(self.tutor)
        response = self.client.get("/api/catalog/my-courses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Chemistry Draft")

    def test_public_course_list_hides_unapproved_tutors(self):
        approved_tutor = User.objects.create_user(username="approved-catalog", email="approved-catalog@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=approved_tutor, full_name="Approved Tutor", hourly_rate=30, teaches_online=True)
        approved_verification = TutorVerification.objects.create(tutor=approved_tutor, status=TutorVerification.Status.APPROVED)
        TutorSubject.objects.create(tutor=approved_tutor, subject=self.subject, level=TutorSubject.Level.SECONDARY_UPPER)
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
            tutor=approved_tutor,
            status=TutorAgreement.Status.SIGNED,
            agreed_to_terms=True,
            signed_name="Approved Tutor",
            signed_file="tutor_agreements/example.pdf",
        )
        Course.objects.create(
            tutor=approved_tutor,
            title="Approved Course",
            description="Visible",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=50,
            status=Course.Status.PUBLISHED,
        )
        Course.objects.create(
            tutor=self.tutor,
            title="Hidden Course",
            description="Hidden",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=50,
            status=Course.Status.PUBLISHED,
        )

        self.client.force_authenticate(self.student)
        response = self.client.get("/api/catalog/courses/")

        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.data]
        self.assertIn("Approved Course", titles)
        self.assertNotIn("Hidden Course", titles)

    def test_admin_rejection_requires_reason_and_writes_course_audit_trail(self):
        admin = User.objects.create_user(
            username="course-admin",
            email="course-admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        course = Course.objects.create(
            tutor=self.tutor,
            title="Moderation Course",
            description="Needs review",
            subject=self.subject,
            academic_level="SECONDARY_UPPER",
            price=50,
            status=Course.Status.PENDING_REVIEW,
        )

        self.client.force_authenticate(admin)
        missing_reason_response = self.client.patch(
            f"/api/catalog/courses/{course.id}/moderate/",
            {"status": Course.Status.REJECTED},
            format="json",
        )

        self.assertEqual(missing_reason_response.status_code, 400)
        self.assertIn("reason", missing_reason_response.data)

        reason = "Course description is too short."
        reject_response = self.client.patch(
            f"/api/catalog/courses/{course.id}/moderate/",
            {"status": Course.Status.REJECTED, "reason": reason},
            format="json",
        )

        self.assertEqual(reject_response.status_code, 200)
        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.REJECTED)
        self.assertEqual(CourseModerationDecision.objects.filter(course=course, status=Course.Status.REJECTED, reason=reason).count(), 1)
        self.assertEqual(reject_response.data["decisions"][0]["reason"], reason)
