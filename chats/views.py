from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from bookings.models import Booking
from chats.models import Message
from chats.serializers import MessageCreateSerializer, MessageReadSerializer, MessageSerializer


class BookingMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_booking(self, request, booking_id):
        booking = Booking.objects.select_related("student", "tutor").get(pk=booking_id)
        if request.user.id not in {booking.student_id, booking.tutor_id} and request.user.role != User.Role.ADMIN:
            raise PermissionError("You are not a participant in this booking.")
        return booking

    def get(self, request, booking_id):
        try:
            booking = self._get_booking(request, booking_id)
        except PermissionError:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        messages = Message.objects.filter(booking=booking).select_related("sender", "receiver").order_by("created_at")
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, booking_id):
        try:
            booking = self._get_booking(request, booking_id)
        except PermissionError:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = MessageCreateSerializer(data=request.data, context={"request": request, "booking": booking})
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class MessageMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        booking = Booking.objects.get(pk=booking_id)
        if request.user.id not in {booking.student_id, booking.tutor_id} and request.user.role != User.Role.ADMIN:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        messages = Message.objects.filter(booking=booking)
        serializer = MessageReadSerializer(instance=messages, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Messages marked as read."}, status=status.HTTP_200_OK)


class UnreadMessageCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(receiver=request.user, is_read=False).count()
        return Response({"unread_count": count})

