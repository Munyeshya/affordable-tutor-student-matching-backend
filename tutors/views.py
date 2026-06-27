from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsTutor
from catalog.models import Course, Lesson, TutorSubject
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, TutorVerificationDecision
from tutors.serializers import (
    TutorProfileSerializer,
    TutorAgreementSerializer,
    TutorAgreementUploadSerializer,
    VerificationDocumentCreateSerializer,
    TutorVerificationActionSerializer,
    TutorVerificationSerializer,
    PublicTutorSerializer,
)
from tutors.utils import build_tutor_setup_status, get_marketplace_ready_tutor_ids

TUTOR_AGREEMENT_TEMPLATE = """Affordable Tutor Agreement

This agreement is a template and should be reviewed by a qualified legal professional before production use.

By signing this agreement, I confirm that:

1. I will provide honest, accurate information and valid qualification documents.
2. I will act with integrity toward students, parents, and the platform.
3. I will not misrepresent my qualifications, experience, or identity.
4. I will deliver tutoring services professionally and respectfully.
5. I will follow all platform rules, policies, and applicable laws.
6. I understand that misconduct, fraud, harassment, or repeated breaches may result in suspension, termination, removal from the platform, and reporting to the relevant authorities where appropriate.
7. I understand that the platform may pursue available legal remedies for material breach, fraud, or other unlawful conduct, subject to applicable law.

Tutor name:
Signature:
Date:
"""


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


class TutorProfileCompletionView(APIView):
    permission_classes = [IsTutor]

    def _get_profile(self, user):
        profile, _ = TutorProfile.objects.get_or_create(user=user, defaults={"full_name": user.get_full_name() or user.email})
        return profile

    def get(self, request):
        profile = self._get_profile(request.user)
        setup = build_tutor_setup_status(request.user)
        return Response(
            {
                "profile": TutorProfileSerializer(profile).data,
                "marketplace_ready": bool(setup["verification"] and setup["verification"].is_marketplace_ready()),
                "completion_percentage": setup["completion_percentage"],
                "missing_steps": setup["missing_steps"],
                "steps": setup["steps"],
                "subject_count": setup["subject_count"],
                "documents_count": setup["documents_count"],
                "agreement_signed": bool(
                    setup["agreement"]
                    and setup["agreement"].status == TutorAgreement.Status.SIGNED
                    and setup["agreement"].agreed_to_terms
                    and setup["agreement"].signed_file
                ),
            }
        )

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = TutorProfileSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        setup = build_tutor_setup_status(request.user)
        return Response(
            {
                "profile": serializer.data,
                "marketplace_ready": bool(setup["verification"] and setup["verification"].is_marketplace_ready()),
                "completion_percentage": setup["completion_percentage"],
                "missing_steps": setup["missing_steps"],
                "steps": setup["steps"],
            }
        )


class TutorDashboardView(APIView):
    permission_classes = [IsTutor]

    def _get_profile(self, user):
        profile, _ = TutorProfile.objects.get_or_create(user=user, defaults={"full_name": user.get_full_name() or user.email})
        return profile

    def get(self, request):
        setup = build_tutor_setup_status(request.user)
        courses = Course.objects.filter(tutor=request.user)
        lessons = Lesson.objects.filter(course__tutor=request.user)

        course_stats = {
            "total_courses": courses.count(),
            "draft_courses": courses.filter(status=Course.Status.DRAFT).count(),
            "pending_courses": courses.filter(status=Course.Status.PENDING_REVIEW).count(),
            "published_courses": courses.filter(status=Course.Status.PUBLISHED).count(),
            "rejected_courses": courses.filter(status=Course.Status.REJECTED).count(),
        }

        lesson_stats = {
            "total_lessons": lessons.count(),
            "preview_lessons": lessons.filter(is_preview=True).count(),
        }

        latest_courses = list(
            courses.select_related("subject")
            .order_by("-updated_at")[:5]
            .values("id", "title", "status", "subject__name", "updated_at")
        )

        return Response(
            {
                "profile": TutorProfileSerializer(self._get_profile(request.user)).data,
                "marketplace_ready": bool(setup["verification"] and setup["verification"].is_marketplace_ready()),
                "completion_percentage": setup["completion_percentage"],
                "missing_steps": setup["missing_steps"],
                "course_stats": course_stats,
                "lesson_stats": lesson_stats,
                "latest_courses": latest_courses,
            }
        )


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

        if verification.status != TutorVerification.Status.PENDING:
            verification.status = TutorVerification.Status.PENDING
            verification.reviewed_by = None
            verification.reviewed_at = None
            verification.notes = ""
            verification.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])

        from tutors.serializers import VerificationDocumentSerializer

        return Response(VerificationDocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class TutorAgreementView(APIView):
    permission_classes = [IsTutor]
    parser_classes = [MultiPartParser, FormParser]

    def _get_agreement(self, user):
        agreement, _ = TutorAgreement.objects.get_or_create(tutor=user)
        return agreement

    def get(self, request):
        agreement = self._get_agreement(request.user)
        return Response(TutorAgreementSerializer(agreement).data)

    def post(self, request):
        agreement = self._get_agreement(request.user)
        serializer = TutorAgreementUploadSerializer(instance=agreement, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        agreement = serializer.save(status=TutorAgreement.Status.SIGNED, signed_at=timezone.now())
        return Response(TutorAgreementSerializer(agreement).data, status=status.HTTP_201_CREATED)


class TutorAgreementDownloadView(APIView):
    permission_classes = [IsTutor]

    def get(self, request):
        response = HttpResponse(TUTOR_AGREEMENT_TEMPLATE, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="tutor-agreement-template.txt"'
        return response


class TutorSetupChecklistView(APIView):
    permission_classes = [IsTutor]

    def get(self, request):
        setup = build_tutor_setup_status(request.user)

        return Response(
            {
                "marketplace_ready": bool(setup["verification"] and setup["verification"].is_marketplace_ready()),
                "verification_status": getattr(setup["verification"], "status", None),
                "profile_exists": bool(setup["profile"]),
                "subjects_count": setup["subject_count"],
                "documents_count": setup["documents_count"],
                "agreement_signed": bool(setup["agreement"] and setup["agreement"].status == TutorAgreement.Status.SIGNED),
                "completion_percentage": setup["completion_percentage"],
                "steps": setup["steps"],
                "missing_steps": setup["missing_steps"],
            }
        )


class PendingTutorVerificationListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = TutorVerificationSerializer

    def get_queryset(self):
        queryset = TutorVerification.objects.select_related("tutor", "reviewed_by", "tutor__tutor_profile").prefetch_related("documents", "decisions__admin")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by("-created_at")


class PublicTutorListView(generics.ListAPIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = PublicTutorSerializer

    def get_queryset(self):
        ready_ids = get_marketplace_ready_tutor_ids()
        queryset = TutorProfile.objects.select_related("user", "user__tutor_verification").filter(user_id__in=ready_ids).distinct()

        subject = self.request.query_params.get("subject")
        location = self.request.query_params.get("location")
        mode = self.request.query_params.get("mode")
        min_rate = self.request.query_params.get("min_rate")
        max_rate = self.request.query_params.get("max_rate")
        level = self.request.query_params.get("level")
        lesson = self.request.query_params.get("lesson")
        topic = self.request.query_params.get("topic")

        text_query = self.request.query_params.get("q") or self.request.query_params.get("name")
        if text_query:
            queryset = queryset.filter(
                Q(full_name__icontains=text_query)
                | Q(headline__icontains=text_query)
                | Q(bio__icontains=text_query)
                | Q(user__username__icontains=text_query)
                | Q(user__email__icontains=text_query)
                | Q(user__courses__title__icontains=text_query)
                | Q(user__courses__description__icontains=text_query)
                | Q(user__courses__lessons__title__icontains=text_query)
                | Q(user__courses__lessons__topic__icontains=text_query)
                | Q(user__tutor_subjects__subject__name__icontains=text_query)
                | Q(user__tutor_subjects__level__icontains=text_query)
            )

        if subject:
            queryset = queryset.filter(Q(user__tutor_subjects__subject__name__icontains=subject) | Q(user__courses__subject__name__icontains=subject))
        if location:
            queryset = queryset.filter(location__icontains=location)
        if mode == "ONLINE":
            queryset = queryset.filter(teaches_online=True)
        if mode == "IN_PERSON":
            queryset = queryset.filter(teaches_in_person=True)
        if level:
            queryset = queryset.filter(user__tutor_subjects__level=level)
        if lesson:
            queryset = queryset.filter(Q(user__courses__lessons__title__icontains=lesson) | Q(user__courses__lessons__topic__icontains=lesson))
        if topic:
            queryset = queryset.filter(Q(user__courses__lessons__topic__icontains=topic) | Q(user__courses__title__icontains=topic))
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
        reason = serializer.validated_data["reason"]

        if serializer.validated_data["status"] == TutorVerification.Status.APPROVED and not verification.has_required_documents():
            return Response(
                {
                    "detail": "Tutor must upload both a national ID and a qualification certificate before approval.",
                    "missing_documents": verification.missing_required_document_types(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        tutor_subjects = verification.tutor.tutor_subjects.select_related("subject")
        if serializer.validated_data["status"] == TutorVerification.Status.APPROVED and not tutor_subjects.exists():
            return Response(
                {
                    "detail": "Tutor must choose at least one subject and level before approval.",
                    "subjects_required": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invalid_levels = [item.level for item in tutor_subjects if item.level not in TutorSubject.Level.values]
        if serializer.validated_data["status"] == TutorVerification.Status.APPROVED and invalid_levels:
            return Response(
                {
                    "detail": "Tutor subjects must use one of the supported levels.",
                    "invalid_levels": invalid_levels,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        agreement = TutorAgreement.objects.filter(tutor=verification.tutor).first()
        if serializer.validated_data["status"] == TutorVerification.Status.APPROVED and (
            not agreement or agreement.status != TutorAgreement.Status.SIGNED or not agreement.agreed_to_terms or not agreement.signed_file
        ):
            return Response(
                {
                    "detail": "Tutor must sign and upload the agreement before approval.",
                    "agreement_required": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification.status = serializer.validated_data["status"]
        verification.notes = reason
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "notes", "reviewed_by", "reviewed_at", "updated_at"])

        TutorVerificationDecision.objects.create(
            verification=verification,
            admin=request.user,
            status=verification.status,
            reason=reason,
        )

        return Response(TutorVerificationSerializer(verification).data, status=status.HTTP_200_OK)
