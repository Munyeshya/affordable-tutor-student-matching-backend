from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class LessonAssessment(TimeStampedModel):
    class AttemptType(models.TextChoices):
        PRE_TEST = "PRE_TEST", "Pre-test"
        POST_TEST = "POST_TEST", "Post-test"

    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="assessments")
    attempt_type = models.CharField(max_length=20, choices=AttemptType.choices)
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True, default="")
    marks = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class LessonAssessmentQuestion(TimeStampedModel):
    assessment = models.ForeignKey(LessonAssessment, on_delete=models.CASCADE, related_name="questions")
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True, default="")
    option_d = models.CharField(max_length=255, blank=True, default="")
    correct_answer = models.CharField(max_length=1)
    marks = models.PositiveIntegerField(default=1)
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_number", "created_at"]
        unique_together = ("assessment", "order_number")


class StudentAssessmentAttempt(TimeStampedModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_attempts")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="assessment_attempts")
    assessment = models.ForeignKey(LessonAssessment, on_delete=models.CASCADE, related_name="attempts")
    attempt_type = models.CharField(max_length=20, choices=LessonAssessment.AttemptType.choices)
    score = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "assessment")


class StudentAssessmentAnswer(TimeStampedModel):
    attempt = models.ForeignKey(StudentAssessmentAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(LessonAssessmentQuestion, on_delete=models.CASCADE, related_name="answers")
    selected_answer = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.PositiveIntegerField(default=0)


class AssessmentResultConfirmation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_confirmations")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="assessment_confirmations")
    pre_test_attempt = models.OneToOneField(
        StudentAssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="pre_test_confirmation",
    )
    post_test_attempt = models.OneToOneField(
        StudentAssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="post_test_confirmation",
    )
    pre_test_score = models.PositiveIntegerField(default=0)
    post_test_score = models.PositiveIntegerField(default=0)
    improvement_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    student_confirmation_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    student_comment = models.TextField(blank=True, default="")
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "lesson")

