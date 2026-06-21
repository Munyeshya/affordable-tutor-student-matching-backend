from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole, IsTutor
from catalog.models import Course, Lesson, Subject, TutorSubject
from catalog.serializers import (
    CourseCreateUpdateSerializer,
    CourseModerationSerializer,
    CourseSerializer,
    PublicCourseSerializer,
    LessonSerializer,
    SubjectSerializer,
    TutorSubjectSerializer,
)


class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.filter(is_active=True).order_by("name")
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class TutorSubjectListCreateView(generics.ListCreateAPIView):
    serializer_class = TutorSubjectSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return TutorSubject.objects.filter(tutor=self.request.user).select_related("subject").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tutor=self.request.user)


class TutorSubjectDeleteView(APIView):
    permission_classes = [IsTutor]

    def delete(self, request, pk):
        subject = TutorSubject.objects.get(pk=pk, tutor=request.user)
        subject.delete()
        return Response(status=204)


class CourseListView(generics.ListAPIView):
    serializer_class = PublicCourseSerializer
    permission_classes = []
    authentication_classes = []

    def get_queryset(self):
        queryset = Course.objects.select_related("tutor", "subject").prefetch_related("lessons").filter(status=Course.Status.PUBLISHED)

        query = self.request.query_params.get("q")
        name = self.request.query_params.get("name")
        lesson = self.request.query_params.get("lesson")
        topic = self.request.query_params.get("topic")
        subject = self.request.query_params.get("subject")

        text_query = query or name
        if text_query:
            queryset = queryset.filter(
                Q(title__icontains=text_query)
                | Q(description__icontains=text_query)
                | Q(tutor__first_name__icontains=text_query)
                | Q(tutor__last_name__icontains=text_query)
                | Q(tutor__username__icontains=text_query)
                | Q(tutor__email__icontains=text_query)
            )

        if lesson:
            queryset = queryset.filter(Q(lessons__title__icontains=lesson) | Q(lessons__topic__icontains=lesson))
        if topic:
            queryset = queryset.filter(lessons__topic__icontains=topic)
        if subject:
            queryset = queryset.filter(Q(subject__name__icontains=subject) | Q(title__icontains=subject))

        return queryset.distinct().order_by("-created_at")


class TutorCourseListView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return Course.objects.filter(tutor=self.request.user).select_related("tutor", "subject").prefetch_related("lessons").order_by("-created_at")


class CourseCreateView(generics.CreateAPIView):
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [IsTutor]

    def perform_create(self, serializer):
        serializer.save(tutor=self.request.user)


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseCreateUpdateSerializer
    permission_classes = [IsTutor]
    queryset = Course.objects.all()

    def get_queryset(self):
        return Course.objects.filter(tutor=self.request.user)


class TutorCourseSubmitForReviewView(APIView):
    permission_classes = [IsTutor]

    def patch(self, request, pk):
        course = Course.objects.get(pk=pk, tutor=request.user)
        if course.status not in {Course.Status.DRAFT, Course.Status.REJECTED}:
            return Response({"detail": "Only draft or rejected courses can be submitted."}, status=400)
        course.status = Course.Status.PENDING_REVIEW
        course.save(update_fields=["status", "updated_at"])
        return Response(CourseSerializer(course, context={"request": request}).data, status=200)


class AdminCourseModerationView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        course = Course.objects.select_related("tutor", "subject").prefetch_related("lessons").get(pk=pk)
        serializer = CourseModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course.status = serializer.validated_data["status"]
        course.save(update_fields=["status", "updated_at"])

        return Response(CourseSerializer(course, context={"request": request}).data, status=200)


class PublicCourseDetailView(generics.RetrieveAPIView):
    serializer_class = PublicCourseSerializer
    permission_classes = []
    authentication_classes = []

    def get_queryset(self):
        return Course.objects.select_related("tutor", "subject").prefetch_related("lessons").filter(status=Course.Status.PUBLISHED)


class LessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        return Lesson.objects.filter(course_id=course_id, course__tutor=self.request.user).order_by("order_number")

    def perform_create(self, serializer):
        course_id = self.kwargs["course_id"]
        course = Course.objects.get(pk=course_id, tutor=self.request.user)
        serializer.save(course=course)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return Lesson.objects.filter(course__tutor=self.request.user)
