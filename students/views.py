from django.db.models import Avg
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsParent
from assessments.models import AssessmentResultConfirmation
from bookings.models import Booking
from students.models import ParentProfile, ParentStudentLink, StudentProfile
from students.serializers import (
    ParentProfileSerializer,
    ParentStudentLinkCreateSerializer,
    ParentStudentLinkSerializer,
    StudentProfileSummarySerializer,
)


class ParentProfileView(APIView):
    permission_classes = [IsParent]

    def _get_profile(self, user):
        profile, _ = ParentProfile.objects.get_or_create(user=user, defaults={"full_name": user.get_full_name() or user.email})
        return profile

    def get(self, request):
        return Response(ParentProfileSerializer(self._get_profile(request.user)).data)

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = ParentProfileSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ParentStudentLinkListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsParent]

    def get_queryset(self):
        return ParentStudentLink.objects.select_related("student", "student__student_profile").filter(parent=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ParentStudentLinkCreateSerializer
        return ParentStudentLinkSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = serializer.save()
        return Response(ParentStudentLinkSerializer(link).data, status=status.HTTP_201_CREATED)


class ParentDashboardView(APIView):
    permission_classes = [IsParent]

    def _get_profile(self, user):
        profile, _ = ParentProfile.objects.get_or_create(user=user, defaults={"full_name": user.get_full_name() or user.email})
        return profile

    def get(self, request):
        links = ParentStudentLink.objects.select_related("student", "student__student_profile").filter(parent=request.user)
        student_ids = [link.student_id for link in links]

        bookings = Booking.objects.select_related("student", "tutor", "subject").filter(student_id__in=student_ids)
        confirmations = AssessmentResultConfirmation.objects.select_related("student", "lesson", "lesson__course").filter(student_id__in=student_ids)

        student_payload = []
        for link in links:
            student = link.student.student_profile
            student_bookings = bookings.filter(student_id=link.student_id)
            student_confirmations = confirmations.filter(student_id=link.student_id)
            student_payload.append(
                {
                    "link": ParentStudentLinkSerializer(link).data,
                    "student": StudentProfileSummarySerializer(student).data,
                    "booking_stats": {
                        "total_bookings": student_bookings.count(),
                        "confirmed_bookings": student_bookings.filter(status=Booking.Status.CONFIRMED).count(),
                        "completed_bookings": student_bookings.filter(status=Booking.Status.COMPLETED).count(),
                        "pending_bookings": student_bookings.filter(status=Booking.Status.PENDING).count(),
                    },
                    "learning_stats": {
                        "confirmed_results": student_confirmations.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED).count(),
                        "average_improvement": student_confirmations.filter(
                            student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED
                        ).aggregate(avg=Avg("improvement_percentage"))["avg"] or 0,
                    },
                    "recent_bookings": list(
                        student_bookings.order_by("-created_at").values(
                            "id",
                            "status",
                            "start_datetime",
                            "end_datetime",
                            "mode",
                            "subject__name",
                            "tutor__email",
                        )[:5]
                    ),
                }
            )

        return Response(
            {
                "profile": ParentProfileSerializer(self._get_profile(request.user)).data,
                "linked_students": student_payload,
                "summary": {
                    "linked_students": len(student_payload),
                    "total_bookings": bookings.count(),
                    "confirmed_learning_outcomes": confirmations.filter(
                        student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED
                    ).count(),
                },
            }
        )
