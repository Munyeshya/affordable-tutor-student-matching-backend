from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsTutor
from bookings.models import Booking, BookingEvent, Dispute, DisputeDecision
from bookings.serializers import (
    BookingActionSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    DisputeActionSerializer,
    DisputeCreateSerializer,
    DisputeSerializer,
)
from availability.models import AvailabilitySlot
from students.models import ParentStudentLink
from tutors.models import TutorVerification
from notifications.utils import create_notification


class BookingListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return Booking.objects.filter(student=user).select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")
        if user.role == User.Role.PARENT:
            student_ids = ParentStudentLink.objects.filter(parent=user).values_list("student_id", flat=True)
            return Booking.objects.filter(student_id__in=student_ids).select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return Booking.objects.filter(tutor=user).select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")
        return Booking.objects.select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")


class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class BookingActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_for_update(), pk=pk)
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        message = serializer.validated_data.get("message", "")
        user = request.user

        if action in {"ACCEPT", "REJECT", "COMPLETE"} and user.role != User.Role.TUTOR:
            return Response({"detail": "Only tutors can perform this action."}, status=status.HTTP_403_FORBIDDEN)
        verification = TutorVerification.objects.filter(tutor=user).first()
        if action in {"ACCEPT", "REJECT", "COMPLETE"} and not verification:
            return Response({"detail": "Tutor verification is required."}, status=status.HTTP_403_FORBIDDEN)
        if action in {"ACCEPT", "REJECT", "COMPLETE"} and not verification.is_marketplace_ready():
            return Response({"detail": "Tutor must complete verification before managing bookings."}, status=status.HTTP_403_FORBIDDEN)
        if action == "CANCEL" and user.role not in {User.Role.STUDENT, User.Role.TUTOR, User.Role.PARENT}:
            return Response({"detail": "Only students, tutors, or parents can cancel."}, status=status.HTTP_403_FORBIDDEN)

        if action in {"ACCEPT", "REJECT", "COMPLETE"} and booking.tutor_id != user.id:
            return Response({"detail": "You can only update your own bookings."}, status=status.HTTP_403_FORBIDDEN)
        if action == "CANCEL" and user.id not in {booking.student_id, booking.tutor_id}:
            if user.role != User.Role.PARENT or not ParentStudentLink.objects.filter(parent=user, student_id=booking.student_id).exists():
                return Response({"detail": "You can only cancel your own booking."}, status=status.HTTP_403_FORBIDDEN)

        if action == "ACCEPT":
            if booking.status != Booking.Status.PENDING:
                return Response({"detail": "Only pending bookings can be accepted."}, status=400)
            booking.status = Booking.Status.CONFIRMED
        elif action == "REJECT":
            if booking.status != Booking.Status.PENDING:
                return Response({"detail": "Only pending bookings can be rejected."}, status=400)
            booking.status = Booking.Status.CANCELLED
        elif action == "CANCEL":
            if booking.status in {Booking.Status.COMPLETED, Booking.Status.CANCELLED}:
                return Response({"detail": "This booking cannot be cancelled."}, status=400)
            booking.status = Booking.Status.CANCELLED
        elif action == "COMPLETE":
            if booking.status != Booking.Status.CONFIRMED:
                return Response({"detail": "Only confirmed bookings can be completed."}, status=400)
            booking.status = Booking.Status.COMPLETED

        booking.save(update_fields=["status", "updated_at"])

        if action in {"REJECT", "CANCEL"}:
            AvailabilitySlot.objects.filter(
                tutor=booking.tutor,
                start_datetime=booking.start_datetime,
                end_datetime=booking.end_datetime,
                mode=booking.mode,
                is_booked=True,
            ).update(is_booked=False)

        BookingEvent.objects.create(booking=booking, actor=user, action=action, message=message)
        other_user = booking.tutor if user.id == booking.student_id else booking.student
        create_notification(
            user=other_user,
            actor=user,
            title=f"Booking {action.lower()}",
            body=message or f"Your booking was {action.lower()} by {user.get_full_name() or user.email}.",
            link=f"/api/bookings/{booking.id}/",
            kind=f"BOOKING_{action}",
        )

        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)


class DisputeListView(generics.ListAPIView):
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Dispute.objects.select_related("booking", "reported_by", "reported_against").prefetch_related("decisions__admin")
        if user.role == User.Role.ADMIN:
            return queryset.order_by("-created_at")
        return queryset.filter(Q(reported_by=user) | Q(reported_against=user)).order_by("-created_at")


class DisputeCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DisputeCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        dispute = serializer.save()
        create_notification(
            user=dispute.reported_against,
            actor=request.user,
            title="New dispute reported",
            body=f"A dispute was reported for booking #{dispute.booking_id}.",
            link="/api/bookings/disputes/",
            kind="DISPUTE_REPORTED",
        )
        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


class DisputeDecisionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        if request.user.role != User.Role.ADMIN:
            return Response({"detail": "Only admins can review disputes."}, status=status.HTTP_403_FORBIDDEN)

        dispute = get_object_or_404(Dispute.objects.select_for_update().prefetch_related("decisions__admin"), pk=pk)
        serializer = DisputeActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        status_value = serializer.validated_data["status"]
        comment = serializer.validated_data.get("comment", "")

        dispute.status = status_value
        dispute.admin_comment = comment
        if status_value in {Dispute.Status.RESOLVED, Dispute.Status.REJECTED}:
            dispute.resolved_at = timezone.now()
        dispute.save(update_fields=["status", "admin_comment", "resolved_at", "updated_at"])

        DisputeDecision.objects.create(
            dispute=dispute,
            admin=request.user,
            status=status_value,
            comment=comment,
        )

        create_notification(
            user=dispute.reported_by,
            actor=request.user,
            title="Dispute updated",
            body=f"Your dispute for booking #{dispute.booking_id} was marked as {status_value.lower()}.",
            link="/api/bookings/disputes/",
            kind=f"DISPUTE_{status_value}",
        )

        return Response(DisputeSerializer(dispute).data, status=status.HTTP_200_OK)
