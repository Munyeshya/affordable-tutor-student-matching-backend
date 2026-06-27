from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from assessments.models import AssessmentResultConfirmation, LessonAssessment, LessonAssessmentQuestion, StudentAssessmentAttempt
from catalog.models import Course, Lesson, Subject, TutorSubject
from notifications.models import Notification
from payments.models import CoursePurchase
from students.models import StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class AssessmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student4", email="student4@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Four")
        self.tutor = User.objects.create_user(username="tutor4", email="tutor4@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Four", hourly_rate=20, teaches_online=True)
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Biology")
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
            signed_name="Tutor Four",
            signed_file="tutor_agreements/signed.pdf",
        )
        self.course = Course.objects.create(
            tutor=self.tutor,
            title="Biology 101",
            description="Intro",
            subject=self.subject,
            price=100,
            status=Course.Status.PUBLISHED,
        )
        self.lesson = Lesson.objects.create(course=self.course, title="Cells", topic="Cell biology", order_number=1)
        CoursePurchase.objects.create(student=self.student, course=self.course, amount=100, status=CoursePurchase.Status.PAID, purchased_at=timezone.now())
        self.pre = LessonAssessment.objects.create(lesson=self.lesson, attempt_type=LessonAssessment.AttemptType.PRE_TEST, title="Pre", marks=1)
        self.post = LessonAssessment.objects.create(lesson=self.lesson, attempt_type=LessonAssessment.AttemptType.POST_TEST, title="Post", marks=1)
        self.pre_q = LessonAssessmentQuestion.objects.create(
            assessment=self.pre,
            question="Q1",
            option_a="A",
            option_b="B",
            correct_answer="A",
            marks=1,
            order_number=1,
        )
        self.post_q = LessonAssessmentQuestion.objects.create(
            assessment=self.post,
            question="Q2",
            option_a="A",
            option_b="B",
            correct_answer="A",
            marks=1,
            order_number=1,
        )
        self.client.force_authenticate(self.student)

    def test_assessment_confirmation_creates_notification_for_tutor(self):
        pre_attempt = self.client.post(
            "/api/assessments/attempts/create/",
            {"assessment_id": self.pre.id, "answers": [{"question_id": self.pre_q.id, "selected_answer": "A"}]},
            format="json",
        )
        post_attempt = self.client.post(
            "/api/assessments/attempts/create/",
            {"assessment_id": self.post.id, "answers": [{"question_id": self.post_q.id, "selected_answer": "A"}]},
            format="json",
        )
        self.assertEqual(pre_attempt.status_code, 201)
        self.assertEqual(post_attempt.status_code, 201)

        response = self.client.post(
            "/api/assessments/confirmations/create/",
            {
                "lesson_id": self.lesson.id,
                "pre_test_attempt_id": StudentAssessmentAttempt.objects.get(assessment=self.pre).id,
                "post_test_attempt_id": StudentAssessmentAttempt.objects.get(assessment=self.post).id,
                "student_confirmation_status": "CONFIRMED",
                "student_comment": "Better now",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Notification.objects.filter(user=self.tutor, kind="ASSESSMENT_CONFIRMATION").count(), 1)

    def test_tutor_can_view_learning_impact_summary(self):
        self.client.post(
            "/api/assessments/attempts/create/",
            {"assessment_id": self.pre.id, "answers": [{"question_id": self.pre_q.id, "selected_answer": "A"}]},
            format="json",
        )
        self.client.post(
            "/api/assessments/attempts/create/",
            {"assessment_id": self.post.id, "answers": [{"question_id": self.post_q.id, "selected_answer": "A"}]},
            format="json",
        )
        self.client.post(
            "/api/assessments/confirmations/create/",
            {
                "lesson_id": self.lesson.id,
                "pre_test_attempt_id": StudentAssessmentAttempt.objects.get(assessment=self.pre).id,
                "post_test_attempt_id": StudentAssessmentAttempt.objects.get(assessment=self.post).id,
                "student_confirmation_status": AssessmentResultConfirmation.Status.CONFIRMED,
                "student_comment": "Confirmed",
            },
            format="json",
        )

        self.client.force_authenticate(self.tutor)
        response = self.client.get("/api/assessments/impact/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["confirmed_confirmations"], 1)
        self.assertEqual(response.data["total_confirmations"], 1)
        self.assertEqual(response.data["average_improvement"], 0)
        self.assertEqual(response.data["top_lessons"][0]["lesson__title"], "Cells")

    def test_students_cannot_view_learning_impact_summary(self):
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/assessments/impact/")

        self.assertEqual(response.status_code, 403)
