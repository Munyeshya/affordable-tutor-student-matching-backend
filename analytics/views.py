from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole
from analytics.serializers import DashboardSummarySerializer
from assessments.models import AssessmentResultConfirmation
from bookings.models import Booking, Dispute
from catalog.models import Course, Lesson
from notifications.models import Notification
from payments.models import CoursePurchase, Payment
from reviews.models import LessonReview, Review
from students.models import ParentProfile, ParentStudentLink, StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification
from tutors.utils import get_marketplace_ready_tutor_ids


def build_dashboard_payload():
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

    tutor_pipeline = {
        "total_tutor_profiles": TutorProfile.objects.count(),
        "pending_verifications": TutorVerification.objects.filter(status=TutorVerification.Status.PENDING).count(),
        "approved_verifications": TutorVerification.objects.filter(status=TutorVerification.Status.APPROVED).count(),
        "rejected_verifications": TutorVerification.objects.filter(status=TutorVerification.Status.REJECTED).count(),
        "marketplace_ready_tutors": len(get_marketplace_ready_tutor_ids()),
        "tutors_with_subjects": TutorProfile.objects.filter(user__tutor_subjects__isnull=False).distinct().count(),
        "tutors_with_signed_agreements": TutorAgreement.objects.filter(
            status=TutorAgreement.Status.SIGNED, agreed_to_terms=True, signed_file__isnull=False
        ).count(),
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
        "parent_accounts": ParentProfile.objects.count(),
        "linked_students": ParentStudentLink.objects.values("student").distinct().count(),
    }

    trends = {
        "monthly_users": list(
            User.objects.annotate(month=TruncMonth("date_joined"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        ),
        "monthly_bookings": list(
            Booking.objects.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        ),
        "monthly_revenue": list(
            CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
            .annotate(month=TruncMonth("purchased_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        ),
        "monthly_confirmed_learning": list(
            educational_impact_qs.annotate(month=TruncMonth("confirmed_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        ),
    }

    leaderboards = {
        "top_tutors_by_bookings": list(
            Booking.objects.values("tutor__id", "tutor__email", "tutor__tutor_profile__full_name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        ),
        "top_students_by_bookings": list(
            Booking.objects.values("student__id", "student__email", "student__student_profile__full_name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        ),
        "top_subjects_by_bookings": list(
            Booking.objects.values("subject__id", "subject__name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        ),
        "top_courses_by_purchases": list(
            CoursePurchase.objects.filter(status=CoursePurchase.Status.PAID)
            .values("course__id", "course__title")
            .annotate(total=Count("id"), revenue=Sum("amount"))
            .order_by("-total")[:10]
        ),
    }

    platform_health = {
        "pending_verifications": TutorVerification.objects.filter(status=TutorVerification.Status.PENDING).count(),
        "pending_course_reviews": Course.objects.filter(status=Course.Status.PENDING_REVIEW).count(),
        "open_bookings": Booking.objects.filter(status=Booking.Status.PENDING).count(),
        "open_disputes": Dispute.objects.filter(status__in=["OPEN", "UNDER_REVIEW"]).count(),
        "unread_notifications": Notification.objects.filter(is_read=False).count(),
    }

    return {
        "users": users,
        "tutoring": tutoring,
        "tutor_pipeline": tutor_pipeline,
        "educational_impact": educational_impact,
        "courses": courses,
        "revenue": revenue,
        "employment_impact": employment_impact,
        "trends": trends,
        "leaderboards": leaderboards,
        "platform_health": platform_health,
    }


def format_value(value):
    if isinstance(value, dict):
        return "; ".join(f"{key.replace('_', ' ').title()}: {format_value(inner_value)}" for key, inner_value in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(format_value(item) for item in value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def render_printable_report_html(title, subtitle, payload):
    sections = []
    for section_name, section_data in payload.items():
        rows = []
        for key, value in section_data.items():
            rows.append(f"<tr><th>{key.replace('_', ' ').title()}</th><td>{format_value(value)}</td></tr>")
        sections.append(
            f"""
            <section class="card">
              <h2>{section_name.replace('_', ' ').title()}</h2>
              <table>{''.join(rows)}</table>
            </section>
            """
        )

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>Admin Printable Report</title>
      <style>
        @page {{
          size: A4 portrait;
          margin: 12mm;
        }}
        body {{
          font-family: Arial, sans-serif;
          color: #111;
          background: #fff;
          margin: 0;
          padding: 0;
        }}
        .page {{
          max-width: 180mm;
          margin: 0 auto;
        }}
        h1 {{
          font-size: 22px;
          margin: 0 0 8mm 0;
        }}
        .meta {{
          font-size: 11px;
          margin-bottom: 6mm;
        }}
        .card {{
          border: 1px solid #bbb;
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 10px;
          page-break-inside: avoid;
        }}
        .card h2 {{
          font-size: 16px;
          margin: 0 0 8px 0;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 11px;
        }}
        th, td {{
          text-align: left;
          vertical-align: top;
          padding: 4px 6px;
          border-top: 1px solid #e0e0e0;
        }}
        th {{
          width: 42%;
          font-weight: 600;
        }}
      </style>
    </head>
    <body>
      <div class="page">
        <h1>{title}</h1>
        <div class="meta">{subtitle}</div>
        {''.join(sections)}
      </div>
    </body>
    </html>
    """


def build_student_report_payload(user):
    profile = getattr(user, "student_profile", None)
    bookings = Booking.objects.filter(student=user)
    confirmations = AssessmentResultConfirmation.objects.filter(student=user)
    purchases = CoursePurchase.objects.filter(student=user, status=CoursePurchase.Status.PAID)

    return {
        "profile": {
            "full_name": getattr(profile, "full_name", user.get_full_name() or user.email),
            "level": getattr(profile, "level", ""),
            "location": getattr(profile, "location", ""),
            "budget_min": getattr(profile, "budget_min", None),
            "budget_max": getattr(profile, "budget_max", None),
        },
        "study_summary": {
            "total_bookings": bookings.count(),
            "confirmed_bookings": bookings.filter(status=Booking.Status.CONFIRMED).count(),
            "completed_bookings": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "course_purchases": purchases.count(),
            "total_spent": purchases.aggregate(total=Sum("amount"))["total"] or 0,
        },
        "learning_summary": {
            "confirmed_outcomes": confirmations.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED).count(),
            "average_improvement": confirmations.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED).aggregate(
                avg=Avg("improvement_percentage")
            )["avg"]
            or 0,
            "latest_confirmations": list(
                confirmations.order_by("-created_at").values("lesson__title", "improvement_percentage", "student_confirmation_status")[:5]
            ),
        },
        "recent_activity": {
            "recent_bookings": list(bookings.order_by("-created_at").values("id", "status", "subject__name", "tutor__email")[:5]),
            "unread_notifications": Notification.objects.filter(user=user, is_read=False).count(),
        },
    }


def build_tutor_report_payload(user):
    profile = getattr(user, "tutor_profile", None)
    verification = getattr(user, "tutor_verification", None)
    agreement = getattr(user, "tutor_agreement", None)
    bookings = Booking.objects.filter(tutor=user)
    course_qs = Course.objects.filter(tutor=user)
    lesson_qs = Lesson.objects.filter(course__tutor=user)
    paid_payments = Payment.objects.filter(tutor=user, status=Payment.Status.PAID)
    reviews = Review.objects.filter(tutor=user)

    return {
        "profile": {
            "full_name": getattr(profile, "full_name", user.get_full_name() or user.email),
            "hourly_rate": getattr(profile, "hourly_rate", None),
            "location": getattr(profile, "location", ""),
            "teaches_online": getattr(profile, "teaches_online", False),
            "teaches_in_person": getattr(profile, "teaches_in_person", False),
        },
        "verification": {
            "status": getattr(verification, "status", None),
            "required_documents": 2,
            "agreement_signed": bool(
                agreement and agreement.status == TutorAgreement.Status.SIGNED and agreement.agreed_to_terms and agreement.signed_file
            ),
            "subject_count": user.tutor_subjects.count(),
            "marketplace_ready": bool(verification and verification.is_marketplace_ready()),
        },
        "work_summary": {
            "total_bookings": bookings.count(),
            "confirmed_bookings": bookings.filter(status=Booking.Status.CONFIRMED).count(),
            "completed_bookings": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "cancelled_bookings": bookings.filter(status=Booking.Status.CANCELLED).count(),
            "active_courses": course_qs.filter(status=Course.Status.PUBLISHED).count(),
            "total_lessons": lesson_qs.count(),
        },
        "earnings": {
            "booking_revenue": paid_payments.aggregate(total=Sum("amount"))["total"] or 0,
            "course_revenue": CoursePurchase.objects.filter(course__tutor=user, status=CoursePurchase.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
            "total_earnings": (
                paid_payments.aggregate(total=Sum("amount"))["total"] or 0
            )
            + (CoursePurchase.objects.filter(course__tutor=user, status=CoursePurchase.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0),
            "reviews_received": reviews.count(),
            "average_rating": reviews.aggregate(avg=Avg("rating"))["avg"] or 0,
        },
        "recent_activity": {
            "recent_bookings": list(bookings.order_by("-created_at").values("id", "status", "student__email", "subject__name")[:5]),
            "recent_courses": list(course_qs.order_by("-created_at").values("id", "title", "status", "price")[:5]),
        },
    }


def build_parent_report_payload(user):
    profile = getattr(user, "parent_profile", None)
    links = ParentStudentLink.objects.filter(parent=user).select_related("student", "student__student_profile")
    student_ids = links.values_list("student_id", flat=True)
    bookings = Booking.objects.filter(student_id__in=student_ids)
    confirmations = AssessmentResultConfirmation.objects.filter(student_id__in=student_ids)

    return {
        "profile": {
            "full_name": getattr(profile, "full_name", user.get_full_name() or user.email),
            "location": getattr(profile, "location", ""),
            "phone_number": getattr(profile, "phone_number", ""),
        },
        "linked_students": {
            "total_linked_students": links.count(),
            "primary_links": links.filter(is_primary=True).count(),
            "student_names": list(links.values_list("student__student_profile__full_name", flat=True)),
        },
        "support_summary": {
            "total_bookings": bookings.count(),
            "confirmed_bookings": bookings.filter(status=Booking.Status.CONFIRMED).count(),
            "completed_bookings": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "confirmed_learning_outcomes": confirmations.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED).count(),
            "average_improvement": confirmations.filter(student_confirmation_status=AssessmentResultConfirmation.Status.CONFIRMED).aggregate(avg=Avg("improvement_percentage"))["avg"]
            or 0,
        },
        "recent_activity": {
            "recent_bookings": list(bookings.order_by("-created_at").values("id", "status", "student__email", "tutor__email")[:5]),
            "recent_confirmations": list(confirmations.order_by("-created_at").values("lesson__title", "improvement_percentage")[:5]),
        },
    }


def build_user_report_payload(user):
    if user.role == User.Role.STUDENT:
        return "Student Report", "Printable student summary", build_student_report_payload(user)
    if user.role == User.Role.TUTOR:
        return "Tutor Report", "Printable tutor summary", build_tutor_report_payload(user)
    if user.role == User.Role.PARENT:
        return "Parent Report", "Printable parent summary", build_parent_report_payload(user)
    return "Admin Report", "Affordable Tutor-Student Matching Platform", build_dashboard_payload()


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = build_dashboard_payload()
        return Response(DashboardSummarySerializer(payload).data)


class AdminPrintableReportView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = build_dashboard_payload()
        html = render_printable_report_html("Admin Printable Report", "Affordable Tutor-Student Matching Platform", payload)
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="admin-printable-report.html"'
        return response


class MyPrintableReportView(APIView):
    def get(self, request):
        title, subtitle, payload = build_user_report_payload(request.user)
        html = render_printable_report_html(title, subtitle, payload)
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        filename = f"{request.user.role.lower()}-report.html"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
