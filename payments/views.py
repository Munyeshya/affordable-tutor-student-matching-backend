from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole, IsMarketplaceReadyTutor, IsStudent, IsTutor
from bookings.models import Booking
from payments.models import CoursePurchase, LessonProgress, Payment, Payout, PayoutDecision
from payments.serializers import (
    BookingPaymentCreateSerializer,
    CoursePurchaseCreateSerializer,
    CoursePurchaseSerializer,
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
    PayoutDecisionActionSerializer,
    PayoutDecisionSerializer,
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
    permission_classes = [IsMarketplaceReadyTutor]

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
        serializer = PayoutDecisionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_value = serializer.validated_data["status"]
        payout.status = status_value
        if status_value == Payout.Status.PAID:
            payout.paid_at = timezone.now()
        payout.save(update_fields=["status", "paid_at", "updated_at"])
        PayoutDecision.objects.create(
            payout=payout,
            admin=request.user,
            status=status_value,
            reason=serializer.validated_data["reason"],
        )
        create_notification(
            user=payout.tutor,
            actor=request.user,
            title="Payout updated",
            body=f"Your payout was marked as {status_value.lower()}.",
            link="/api/payments/payouts/",
            kind=f"PAYOUT_{status_value}",
        )
        return Response(PayoutSerializer(payout).data, status=status.HTTP_200_OK)


class PayoutDecisionHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        payout = get_object_or_404(Payout.objects.select_related("tutor").prefetch_related("decisions__admin"), pk=pk)
        if request.user.role == User.Role.TUTOR and payout.tutor_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.user.role != User.Role.TUTOR and request.user.role != User.Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(PayoutDecisionSerializer(payout.decisions.select_related("admin").all(), many=True).data)


class TutorEarningsSummaryView(APIView):
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = request.user
        payment_qs = Payment.objects.filter(tutor=tutor, status=Payment.Status.PAID)
        course_purchase_qs = CoursePurchase.objects.filter(course__tutor=tutor, status=CoursePurchase.Status.PAID)
        payout_qs = Payout.objects.filter(tutor=tutor)

        booking_revenue = payment_qs.aggregate(total=Sum("amount"))["total"] or 0
        course_revenue = course_purchase_qs.aggregate(total=Sum("amount"))["total"] or 0
        paid_payouts = payout_qs.filter(status=Payout.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
        pending_payouts = payout_qs.filter(status=Payout.Status.REQUESTED).aggregate(total=Sum("amount"))["total"] or 0
        approved_payouts = payout_qs.filter(status=Payout.Status.APPROVED).aggregate(total=Sum("amount"))["total"] or 0

        total_earnings = booking_revenue + course_revenue
        available_balance = total_earnings - paid_payouts

        return Response(
            {
                "booking_revenue": booking_revenue,
                "course_revenue": course_revenue,
                "total_earnings": total_earnings,
                "paid_payouts": paid_payouts,
                "pending_payouts": pending_payouts,
                "approved_payouts": approved_payouts,
                "available_balance": available_balance,
                "paid_bookings_count": payment_qs.count(),
                "paid_course_purchases_count": course_purchase_qs.count(),
                "payouts_count": payout_qs.count(),
                "recent_payouts": list(
                    payout_qs.select_related("tutor").values("id", "amount", "status", "paid_at", "created_at").order_by("-created_at")[:10]
                ),
                "recent_payments": list(
                    payment_qs.select_related("booking").values("id", "booking_id", "amount", "currency", "status", "paid_at", "created_at").order_by("-created_at")[:10]
                ),
            }
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
