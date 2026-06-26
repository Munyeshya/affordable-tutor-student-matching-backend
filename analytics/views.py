from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole
from analytics.serializers import DashboardSummarySerializer
from assessments.models import AssessmentResultConfirmation
from bookings.models import Booking
from catalog.models import Course, Lesson
from payments.models import CoursePurchase, Payment
from reviews.models import LessonReview, Review
from students.models import ParentProfile, StudentProfile
from tutors.models import TutorProfile, TutorVerification


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = {
            "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
            "total_tutors": User.objects.filter(role=User.Role.TUTOR).count(),
            "total_parents": User.objects.filter(role=User.Role.PARENT).count(),
            "total_admins": User.objects.filter(role=User.Role.ADMIN).count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "new_registrations": User.objects.filter(date_joined__date=timezone.now().date()).count(),
            "verified_tutors": TutorVerification.objects.filter(status=TutorVerification.Status.APPROVED).count(),
        }

        tutoring = {
            "total_bookings": Booking.objects.count(),
            "pending_bookings": Booking.objects.filter(status=Booking.Status.PENDING).count(),
            "confirmed_bookings": Booking.objects.filter(status=Booking.Status.CONFIRMED).count(),
            "completed_bookings": Booking.objects.filter(status=Booking.Status.COMPLETED).count(),
            "cancelled_bookings": Booking.objects.filter(status=Booking.Status.CANCELLED).count(),
        }

        educational_impact_qs = AssessmentResultConfirmation.objects.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED)
        educational_impact = {
            "students_helped": educational_impact_qs.values("student").distinct().count(),
            "average_improvement": educational_impact_qs.aggregate(avg=Avg("improvement_percentage"))["avg"] or 0,
            "highest_improvement": educational_impact_qs.aggregate(max=Max("improvement_percentage"))["max"] or 0,
            "confirmed_improvements": educational_impact_qs.count(),
            "rejected_improvements": AssessmentResultConfirmation.objects.filter(student_confirmation_status=AssessmentResultConfirmation.Status.REJECTED).count(),
            "verified_learning_outcomes": educational_impact_qs.count(),
            "most_effective_subjects": list(
                educational_impact_qs.values("lesson__course__subject__name")
                .annotate(avg_improvement=Avg("improvement_percentage"), count=Count("id"))
                .order_by("-avg_improvement")[:5]
            ),
            "most_effective_tutors": list(
                educational_impact_qs.values("lesson__course__tutor__id", "lesson__course__tutor__email")
                .annotate(avg_improvement=Avg("improvement_percentage"), count=Count("id"))
                .order_by("-avg_improvement")[:5]
            ),
        }

        courses = {
            "total_courses": Course.objects.count(),
            "published_courses": Course.objects.filter(status=Course.Status.PUBLISHED).count(),
            "pending_courses": Course.objects.filter(status=Course.Status.PENDING_REVIEW).count(),
            "rejected_courses": Course.objects.filter(status=Course.Status.REJECTED).count(),
            "total_lessons": Lesson.objects.count(),
            "total_lesson_views": Lesson.objects.aggregate(total=Count("progress_entries"))["total"] or 0,
            "course_purchases": CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID).count(),
            "most_purchased_courses": list(
                CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
                .values("course__id", "course__title")
                .annotate(count=Count("id"), revenue=Sum("amount"))
                .order_by("-count")[:5]
            ),
            "most_viewed_lessons": list(
                Lesson.objects.annotate(progress_count=Count("progress_entries")).values("id", "title", "topic", "progress_count").order_by("-progress_count")[:5]
            ),
        }

        revenue = {
            "platform_revenue": CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
            "tutor_revenue": CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
            .values("course__tutor__id", "course__tutor__email")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:10],
            "monthly_revenue": list(
                CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
                .annotate(month=TruncMonth("purchased_at"))
                .values("month")
                .annotate(total=Sum("amount"))
                .order_by("month")
            ),
            "revenue_by_subject": list(
                CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
                .values("course__subject__name")
                .annotate(total=Sum("amount"), purchases=Count("id"))
                .order_by("-total")
            ),
        }

        employment_impact = {
            "tutors_earning_income": User.objects.filter(role=User.Role.TUTOR, payments_received__status=Payment.Status.PAID).distinct().count(),
            "new_tutors_registered": User.objects.filter(role=User.Role.TUTOR).count(),
            "verified_tutors": TutorVerification.objects.filter(status=TutorVerification.Status.APPROVED).count(),
            "tutors_receiving_bookings": Booking.objects.values("tutor").distinct().count(),
            "tutors_selling_courses": Course.objects.values("tutor").distinct().count(),
            "income_generated_through_platform": CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
            "estimated_unemployed_youth_supported": TutorProfile.objects.count(),
        }

        payload = {
            "users": users,
            "tutoring": tutoring,
            "educational_impact": educational_impact,
            "courses": courses,
            "revenue": revenue,
            "employment_impact": employment_impact,
        }
        return Response(DashboardSummarySerializer(payload).data)
