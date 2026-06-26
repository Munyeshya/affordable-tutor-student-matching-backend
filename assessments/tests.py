from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from assessments.models import LessonAssessment, LessonAssessmentQuestion, StudentAssessmentAttempt
from catalog.models import Course, Lesson, Subject
from notifications.models import Notification
from payments.models import CoursePurchase
from students.models import StudentProfile
from tutors.models import TutorProfile, TutorVerification


class AssessmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student4", email="student4@example.com", password="pass12345", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, full_name="Student Four")
        self.tutor = User.objects.create_user(username="tutor4", email="tutor4@example.com", password="pass12345", role=User.Role.TUTOR)
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor Four", hourly_rate=20, teaches_online=True)
        TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        self.subject = Subject.objects.create(name="Biology")
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

