from django.db import transaction
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTutor
from availability.models import AvailabilitySlot
from availability.serializers import AvailabilitySlotSerializer
from tutors.utils import get_marketplace_ready_tutor_ids


class TutorAvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(tutor=self.request.user).order_by("-start_datetime")

    def perform_create(self, serializer):
        serializer.save(tutor=self.request.user)


class TutorAvailabilityDeleteView(APIView):
    permission_classes = [IsTutor]

    def delete(self, request, pk):
        slot = AvailabilitySlot.objects.get(pk=pk, tutor=request.user)
        if slot.is_booked:
            return Response({"detail": "Booked slots cannot be deleted."}, status=400)
        slot.delete()
        return Response(status=204)


class PublicTutorAvailabilityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AvailabilitySlotSerializer

    def get_queryset(self):
        tutor_id = self.request.query_params.get("tutor")
        ready_ids = get_marketplace_ready_tutor_ids()
        queryset = AvailabilitySlot.objects.filter(is_booked=False, tutor_id__in=ready_ids)
        if tutor_id:
            queryset = queryset.filter(tutor_id=tutor_id)
        return queryset.order_by("start_datetime")
