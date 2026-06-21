from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsTutor
from tutors.models import TutorProfile, TutorVerification
from tutors.serializers import (
    TutorProfileSerializer,
    VerificationDocumentCreateSerializer,
    TutorVerificationActionSerializer,
    TutorVerificationSerializer,
    PublicTutorSerializer,
)


class TutorProfileMeView(APIView):
    permission_classes = [IsTutor]

    def get(self, request):
        profile = getattr(request.user, "tutor_profile", None)
        if not profile:
            profile = TutorProfile.objects.create(user=request.user, full_name=request.user.get_full_name() or request.user.email)
        return Response(TutorProfileSerializer(profile).data)

    def patch(self, request):
        profile = getattr(request.user, "tutor_profile", None)
        if not profile:
            profile = TutorProfile.objects.create(user=request.user, full_name=request.user.get_full_name() or request.user.email)
        serializer = TutorProfileSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TutorVerificationDocumentView(APIView):
    permission_classes = [IsTutor]
    parser_classes = [MultiPartParser, FormParser]

    def _get_verification(self, user):
        verification, _ = TutorVerification.objects.get_or_create(tutor=user)
        return verification

    def get(self, request):
        verification = self._get_verification(request.user)
        documents = verification.documents.order_by("-created_at")
        from tutors.serializers import VerificationDocumentSerializer

        return Response(VerificationDocumentSerializer(documents, many=True).data)

    def post(self, request):
        verification = self._get_verification(request.user)
        serializer = VerificationDocumentCreateSerializer(
            data=request.data,
            context={"verification": verification},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        from tutors.serializers import VerificationDocumentSerializer

        return Response(VerificationDocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class PendingTutorVerificationListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = TutorVerificationSerializer

    def get_queryset(self):
        queryset = TutorVerification.objects.select_related("tutor", "reviewed_by", "tutor__tutor_profile").prefetch_related("documents")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by("-created_at")


class PublicTutorListView(generics.ListAPIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = PublicTutorSerializer

    def get_queryset(self):
        queryset = (
            TutorProfile.objects.select_related("user", "user__tutor_verification")
            .filter(user__tutor_verification__status=TutorVerification.Status.APPROVED)
            .distinct()
        )

        subject = self.request.query_params.get("subject")
        location = self.request.query_params.get("location")
        mode = self.request.query_params.get("mode")
        min_rate = self.request.query_params.get("min_rate")
        max_rate = self.request.query_params.get("max_rate")

        if subject:
            queryset = queryset.filter(user__tutor_subjects__subject__name__icontains=subject)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if mode == "ONLINE":
            queryset = queryset.filter(teaches_online=True)
        if mode == "IN_PERSON":
            queryset = queryset.filter(teaches_in_person=True)
        if min_rate:
            queryset = queryset.filter(hourly_rate__gte=min_rate)
        if max_rate:
            queryset = queryset.filter(hourly_rate__lte=max_rate)

        return queryset.order_by("full_name")


class TutorVerificationDecisionView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        verification = TutorVerification.objects.select_related("tutor").get(pk=pk)
        serializer = TutorVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification.status = serializer.validated_data["status"]
        verification.notes = serializer.validated_data.get("notes", "")
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "notes", "reviewed_by", "reviewed_at", "updated_at"])

        return Response(TutorVerificationSerializer(verification).data, status=status.HTTP_200_OK)
