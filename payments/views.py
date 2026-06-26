from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole, IsStudent, IsTutor
from bookings.models import Booking
from payments.models import CoursePurchase, LessonProgress, Payment, Payout
from payments.serializers import (
    BookingPaymentCreateSerializer,
    CoursePurchaseCreateSerializer,
    CoursePurchaseSerializer,
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
    PaymentSerializer,
    PayoutRequestSerializer,
    PayoutSerializer,
)
from catalog.models import Lesson
from notifications.utils import create_notification


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return Payment.objects.filter(student=user).select_related("booking", "student", "tutor").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return Payment.objects.filter(tutor=user).select_related("booking", "student", "tutor").order_by("-created_at")
        return Payment.objects.select_related("booking", "student", "tutor").order_by("-created_at")


class BookingPaymentCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = BookingPaymentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PayoutListView(generics.ListAPIView):
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.TUTOR:
            return Payout.objects.filter(tutor=user).order_by("-created_at")
        return Payout.objects.select_related("tutor").order_by("-created_at")


class PayoutRequestView(APIView):
    permission_classes = [IsTutor]

    def post(self, request):
        serializer = PayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payout = Payout.objects.create(
            tutor=request.user,
            amount=serializer.validated_data["amount"],
            status=Payout.Status.REQUESTED,
        )
        create_notification(
            user=request.user,
            actor=request.user,
            title="Payout requested",
            body=f"You requested a payout of {payout.amount}.",
            link="/api/payments/payouts/",
            kind="PAYOUT_REQUESTED",
        )
        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class PayoutDecisionView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        payout = get_object_or_404(Payout, pk=pk)
        status_value = request.data.get("status")
        if status_value not in {Payout.Status.APPROVED, Payout.Status.PAID, Payout.Status.REJECTED}:
            return Response({"detail": "Invalid payout status."}, status=status.HTTP_400_BAD_REQUEST)
        payout.status = status_value
        if status_value == Payout.Status.PAID:
            payout.paid_at = timezone.now()
        payout.save(update_fields=["status", "paid_at", "updated_at"])
        create_notification(
            user=payout.tutor,
            actor=request.user,
            title="Payout updated",
            body=f"Your payout was marked as {status_value.lower()}.",
            link="/api/payments/payouts/",
            kind=f"PAYOUT_{status_value}",
        )
        return Response(PayoutSerializer(payout).data, status=status.HTTP_200_OK)


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
