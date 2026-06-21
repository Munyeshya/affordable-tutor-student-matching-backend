from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStudent
from catalog.models import Course, Lesson
from payments.models import CoursePurchase, LessonProgress
from payments.serializers import (
    CoursePurchaseCreateSerializer,
    CoursePurchaseSerializer,
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
)


class CoursePurchaseListView(generics.ListAPIView):
    serializer_class = CoursePurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return CoursePurchase.objects.filter(student=user).select_related("student", "course", "course__tutor").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return CoursePurchase.objects.filter(course__tutor=user).select_related("student", "course", "course__tutor").order_by("-created_at")
        return CoursePurchase.objects.select_related("student", "course", "course__tutor").order_by("-created_at")


class CoursePurchaseCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = CoursePurchaseCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()
        return Response(CoursePurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


class StudentLessonProgressListView(generics.ListAPIView):
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return LessonProgress.objects.filter(student=user).select_related("course", "lesson").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return LessonProgress.objects.filter(course__tutor=user).select_related("course", "lesson").order_by("-created_at")
        return LessonProgress.objects.select_related("course", "lesson").order_by("-created_at")


class StudentLessonProgressUpdateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = LessonProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=serializer.validated_data["lesson_id"])
        course = lesson.course

        if not CoursePurchase.objects.filter(student=request.user, course=course, status=CoursePurchase.Status.PAID).exists():
            return Response({"detail": "You must purchase the course before tracking progress."}, status=status.HTTP_403_FORBIDDEN)

        progress, _ = LessonProgress.objects.get_or_create(student=request.user, course=course, lesson=lesson)
        progress.watched_duration = serializer.validated_data["watched_duration"]
        progress.is_completed = serializer.validated_data.get("is_completed", False)
        if progress.is_completed and progress.completed_at is None:
            progress.completed_at = timezone.now()
        progress.save()

        return Response(LessonProgressSerializer(progress).data, status=status.HTTP_200_OK)

