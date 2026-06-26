from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from assessments.models import (
    AssessmentResultConfirmation,
    LessonAssessment,
    LessonAssessmentQuestion,
    StudentAssessmentAnswer,
    StudentAssessmentAttempt,
)
from catalog.models import Lesson
from payments.models import CoursePurchase


class LessonAssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAssessmentQuestion
        fields = (
            "id",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answer",
            "marks",
            "order_number",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LessonAssessmentSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    questions = LessonAssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = LessonAssessment
        fields = (
            "id",
            "lesson",
            "lesson_title",
            "attempt_type",
            "title",
            "instructions",
            "marks",
            "questions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "questions")


class LessonAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAssessment
        fields = ("id", "lesson", "attempt_type", "title", "instructions", "marks")
        read_only_fields = ("id",)

    def validate_lesson(self, value):
        request = self.context["request"]
        if request.user.role != User.Role.TUTOR or value.course.tutor_id != request.user.id:
            raise serializers.ValidationError("You can only create assessments for your own lessons.")
        return value


class LessonAssessmentQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAssessmentQuestion
        fields = (
            "id",
            "assessment",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answer",
            "marks",
            "order_number",
        )
        read_only_fields = ("id",)

    def validate_assessment(self, value):
        request = self.context["request"]
        if request.user.role != User.Role.TUTOR or value.lesson.course.tutor_id != request.user.id:
            raise serializers.ValidationError("You can only add questions to your own assessments.")
        return value


class StudentAssessmentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAssessmentAnswer
        fields = ("id", "question", "selected_answer", "is_correct", "marks_awarded", "created_at")
        read_only_fields = ("id", "is_correct", "marks_awarded", "created_at")


class StudentAssessmentAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAssessmentAnswerSerializer(many=True, read_only=True)
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)

    class Meta:
        model = StudentAssessmentAttempt
        fields = (
            "id",
            "student",
            "lesson",
            "assessment",
            "assessment_title",
            "attempt_type",
            "score",
            "total_marks",
            "percentage",
            "submitted_at",
            "answers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "score", "total_marks", "percentage", "submitted_at", "answers", "created_at", "updated_at")


class StudentAssessmentAttemptCreateSerializer(serializers.Serializer):
    assessment_id = serializers.IntegerField()
    answers = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_assessment_id(self, value):
        try:
            assessment = LessonAssessment.objects.select_related("lesson", "lesson__course").get(pk=value)
        except LessonAssessment.DoesNotExist:
            raise serializers.ValidationError("Assessment not found.")

        request = self.context["request"]
        if request.user.role != User.Role.STUDENT:
            raise serializers.ValidationError("Only students can submit attempts.")
        if not CoursePurchase.objects.filter(student=request.user, course=assessment.lesson.course, status=CoursePurchase.Status.PAID).exists():
            raise serializers.ValidationError("You must purchase the course before taking its assessments.")

        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        assessment = LessonAssessment.objects.select_related("lesson", "lesson__course").prefetch_related("questions").get(pk=validated_data["assessment_id"])

        if assessment.attempts.filter(student=request.user).exists():
            raise serializers.ValidationError("You have already submitted this assessment.")

        attempt = StudentAssessmentAttempt.objects.create(
            student=request.user,
            lesson=assessment.lesson,
            assessment=assessment,
            attempt_type=assessment.attempt_type,
            submitted_at=timezone.now(),
        )

        total_marks = 0
        score = 0
        question_map = {str(q.id): q for q in assessment.questions.all()}

        for answer_item in validated_data["answers"]:
            question_id = str(answer_item.get("question_id"))
            selected_answer = answer_item.get("selected_answer")
            question = question_map.get(question_id)
            if not question:
                continue

            is_correct = selected_answer == question.correct_answer
            marks_awarded = question.marks if is_correct else 0
            total_marks += question.marks
            score += marks_awarded
            StudentAssessmentAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct,
                marks_awarded=marks_awarded,
            )

        percentage = (score / total_marks * 100) if total_marks else 0
        attempt.score = score
        attempt.total_marks = total_marks
        attempt.percentage = percentage
        attempt.save(update_fields=["score", "total_marks", "percentage", "updated_at"])
        return attempt


class AssessmentResultConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResultConfirmation
        fields = (
            "id",
            "student",
            "lesson",
            "pre_test_attempt",
            "post_test_attempt",
            "pre_test_score",
            "post_test_score",
            "improvement_percentage",
            "student_confirmation_status",
            "student_comment",
            "confirmed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "pre_test_score", "post_test_score", "improvement_percentage", "confirmed_at", "created_at", "updated_at")


class AssessmentResultConfirmationCreateSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    pre_test_attempt_id = serializers.IntegerField()
    post_test_attempt_id = serializers.IntegerField()
    student_confirmation_status = serializers.ChoiceField(choices=AssessmentResultConfirmation.Status.choices)
    student_comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        request = self.context["request"]
        try:
            lesson = Lesson.objects.get(pk=attrs["lesson_id"])
            pre_attempt = StudentAssessmentAttempt.objects.get(pk=attrs["pre_test_attempt_id"], student=request.user, lesson=lesson)
            post_attempt = StudentAssessmentAttempt.objects.get(pk=attrs["post_test_attempt_id"], student=request.user, lesson=lesson)
        except (Lesson.DoesNotExist, StudentAssessmentAttempt.DoesNotExist):
            raise serializers.ValidationError("Lesson or assessment attempts not found.")

        if pre_attempt.attempt_type != LessonAssessment.AttemptType.PRE_TEST:
            raise serializers.ValidationError({"pre_test_attempt_id": "Must be a pre-test attempt."})
        if post_attempt.attempt_type != LessonAssessment.AttemptType.POST_TEST:
            raise serializers.ValidationError({"post_test_attempt_id": "Must be a post-test attempt."})

        attrs["lesson"] = lesson
        attrs["pre_attempt"] = pre_attempt
        attrs["post_attempt"] = post_attempt
        return attrs

    def create(self, validated_data):
        pre_attempt = validated_data["pre_attempt"]
        post_attempt = validated_data["post_attempt"]
        improvement = post_attempt.percentage - pre_attempt.percentage

        return AssessmentResultConfirmation.objects.create(
            student=self.context["request"].user,
            lesson=validated_data["lesson"],
            pre_test_attempt=pre_attempt,
            post_test_attempt=post_attempt,
            pre_test_score=pre_attempt.percentage,
            post_test_score=post_attempt.percentage,
            improvement_percentage=improvement,
            student_confirmation_status=validated_data["student_confirmation_status"],
            student_comment=validated_data.get("student_comment", ""),
            confirmed_at=timezone.now() if validated_data["student_confirmation_status"] == AssessmentResultConfirmation.Status.CONFIRMED else None,
        )
