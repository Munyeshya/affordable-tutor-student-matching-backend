from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStudent, IsTutor
from reviews.models import Review
from reviews.serializers import ReviewCreateSerializer, ReviewSerializer
from reviews.lesson_serializers import LessonReviewCreateSerializer, LessonReviewSerializer
from reviews.models import LessonReview


class ReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return Review.objects.filter(student=user).select_related("student", "tutor", "booking").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return Review.objects.filter(tutor=user).select_related("student", "tutor", "booking").order_by("-created_at")
        return Review.objects.select_related("student", "tutor", "booking").order_by("-created_at")


class ReviewCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewSerializer(review).data, status=201)


class LessonReviewListView(generics.ListAPIView):
    serializer_class = LessonReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return LessonReview.objects.filter(student=user).select_related("lesson", "tutor", "student").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return LessonReview.objects.filter(tutor=user).select_related("lesson", "tutor", "student").order_by("-created_at")
        return LessonReview.objects.select_related("lesson", "tutor", "student").order_by("-created_at")


class LessonReviewCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = LessonReviewCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(LessonReviewSerializer(review).data, status=201)
