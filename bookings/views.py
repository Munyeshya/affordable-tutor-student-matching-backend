from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStudent, IsTutor
from bookings.models import Booking, BookingEvent
from bookings.serializers import BookingActionSerializer, BookingCreateSerializer, BookingSerializer
from availability.models import AvailabilitySlot


class BookingListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return Booking.objects.filter(student=user).select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")
        if user.role == User.Role.TUTOR:
            return Booking.objects.filter(tutor=user).select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")
        return Booking.objects.select_related("student", "tutor", "subject").prefetch_related("events").order_by("-created_at")


class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [IsStudent]


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
        if action == "CANCEL" and user.role not in {User.Role.STUDENT, User.Role.TUTOR}:
            return Response({"detail": "Only students or tutors can cancel."}, status=status.HTTP_403_FORBIDDEN)

        if action in {"ACCEPT", "REJECT", "COMPLETE"} and booking.tutor_id != user.id:
            return Response({"detail": "You can only update your own bookings."}, status=status.HTTP_403_FORBIDDEN)
        if action == "CANCEL" and user.id not in {booking.student_id, booking.tutor_id}:
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

        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)
