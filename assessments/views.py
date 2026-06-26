from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStudent, IsTutor
from assessments.models import (
    AssessmentResultConfirmation,
    LessonAssessment,
    LessonAssessmentQuestion,
    StudentAssessmentAttempt,
)
from assessments.serializers import (
    AssessmentResultConfirmationCreateSerializer,
    AssessmentResultConfirmationSerializer,
    LessonAssessmentCreateSerializer,
    LessonAssessmentQuestionCreateSerializer,
    LessonAssessmentQuestionSerializer,
    LessonAssessmentSerializer,
    StudentAssessmentAttemptCreateSerializer,
    StudentAssessmentAttemptSerializer,
)


class LessonAssessmentListView(generics.ListAPIView):
    serializer_class = LessonAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = LessonAssessment.objects.select_related("lesson", "lesson__course").prefetch_related("questions")
        if user.role == User.Role.TUTOR:
            return queryset.filter(lesson__course__tutor=user).order_by("-created_at")
        return queryset.filter(lesson__course__status="PUBLISHED").order_by("-created_at")


class LessonAssessmentCreateView(generics.CreateAPIView):
    serializer_class = LessonAssessmentCreateSerializer
    permission_classes = [IsTutor]


class LessonAssessmentQuestionCreateView(generics.CreateAPIView):
    serializer_class = LessonAssessmentQuestionCreateSerializer
    permission_classes = [IsTutor]


class LessonAssessmentQuestionListView(generics.ListAPIView):
    serializer_class = LessonAssessmentQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        assessment_id = self.kwargs["assessment_id"]
        assessment = LessonAssessment.objects.get(pk=assessment_id)
        user = self.request.user
        if user.role == User.Role.TUTOR and assessment.lesson.course.tutor_id != user.id:
            return LessonAssessmentQuestion.objects.none()
        return LessonAssessmentQuestion.objects.filter(assessment=assessment).order_by("order_number")


class StudentAssessmentAttemptListView(generics.ListAPIView):
    serializer_class = StudentAssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StudentAssessmentAttempt.objects.select_related("student", "lesson", "assessment", "assessment__lesson")
        if user.role == User.Role.STUDENT:
            return queryset.filter(student=user).order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return queryset.filter(lesson__course__tutor=user).order_by("-created_at")
        return queryset.order_by("-created_at")


class StudentAssessmentAttemptCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = StudentAssessmentAttemptCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()
        return Response(StudentAssessmentAttemptSerializer(attempt).data, status=201)


class AssessmentResultConfirmationCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = AssessmentResultConfirmationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        confirmation = serializer.save()
        return Response(AssessmentResultConfirmationSerializer(confirmation).data, status=201)


class AssessmentResultConfirmationListView(generics.ListAPIView):
    serializer_class = AssessmentResultConfirmationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = AssessmentResultConfirmation.objects.select_related(
            "student", "lesson", "pre_test_attempt", "post_test_attempt"
        )
        if user.role == User.Role.STUDENT:
            return queryset.filter(student=user).order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return queryset.filter(lesson__course__tutor=user).order_by("-created_at")
        return queryset.order_by("-created_at")

