from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Course, Lesson, Subject, TutorSubject
from students.models import StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class CatalogAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student-catalog", email="student-catalog@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Catalog")
        self.tutor = User.objects.create_user(username="tutor-catalog", email="tutor-catalog@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Catalog", hourly_rate=25, teaches_online=True)
        self.subject = Subject.objects.create(name="Chemistry")
        TutorSubject.objects.create(tutor=self.tutor, subject=self.subject, level=TutorSubject.Level.SECONDARY_UPPER)

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
