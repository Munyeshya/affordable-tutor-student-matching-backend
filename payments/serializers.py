from django.utils import timezone
from rest_framework import serializers

from bookings.models import Booking
from catalog.models import Course
from payments.models import CoursePurchase, LessonProgress, Payment, Payout
from notifications.utils import create_notification
from tutors.models import TutorVerification


class PaymentSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "booking",
            "booking_id",
            "student",
            "student_name",
            "tutor",
            "tutor_name",
            "amount",
            "currency",
            "provider",
            "status",
            "paid_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "tutor", "amount", "currency", "provider", "status", "paid_at", "created_at", "updated_at")


class BookingPaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    provider = serializers.CharField(required=False, default="SIMULATED")
    transaction_reference = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.select_related("student", "tutor").get(pk=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")

        request = self.context["request"]
        if booking.student_id != request.user.id:
            raise serializers.ValidationError("You can only pay for your own booking.")
        if booking.status not in {Booking.Status.CONFIRMED, Booking.Status.COMPLETED}:
            raise serializers.ValidationError("Booking must be confirmed before payment.")

        return value

    def create(self, validated_data):
        booking = Booking.objects.select_related("student", "tutor").get(pk=validated_data["booking_id"])
        payment, _ = Payment.objects.update_or_create(
            booking=booking,
            defaults={
                "student": booking.student,
                "tutor": booking.tutor,
                "amount": booking.total_amount or 0,
                "currency": booking.currency,
                "provider": validated_data.get("provider", "SIMULATED"),
                "status": Payment.Status.PAID,
                "paid_at": timezone.now(),
            },
        )
        create_notification(
            user=booking.tutor,
            actor=booking.student,
            title="Booking payment received",
            body=f"{booking.student.get_full_name() or booking.student.email} paid for booking #{booking.id}.",
            link=f"/api/payments/bookings/",
            kind="BOOKING_PAYMENT",
        )
        return payment


class CoursePurchaseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    tutor_name = serializers.CharField(source="course.tutor.get_full_name", read_only=True)

    class Meta:
        model = CoursePurchase
        fields = (
            "id",
            "student",
            "course",
            "course_title",
            "tutor_name",
            "amount",
            "currency",
            "provider",
            "status",
            "transaction_reference",
            "purchased_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "amount", "currency", "provider", "status", "transaction_reference", "purchased_at", "created_at", "updated_at")


class CoursePurchaseCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    provider = serializers.CharField(required=False, default="SIMULATED")
    transaction_reference = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_course_id(self, value):
        try:
            course = Course.objects.select_related("tutor", "subject").get(pk=value)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found.")

        if course.status != Course.Status.PUBLISHED:
            raise serializers.ValidationError("Course is not published.")

        verification = TutorVerification.objects.filter(tutor=course.tutor).first()
        if not verification or not verification.is_marketplace_ready():
            raise serializers.ValidationError("Course is not available yet.")

        if CoursePurchase.objects.filter(student=self.context["request"].user, course=course, status=CoursePurchase.Status.PAID).exists():
            raise serializers.ValidationError("You have already purchased this course.")

        return value

    def create(self, validated_data):
        course = Course.objects.get(pk=validated_data["course_id"])
        student = self.context["request"].user
        purchase = CoursePurchase.objects.create(
            student=student,
            course=course,
            amount=course.price,
            currency="RWF",
            provider=validated_data.get("provider", "SIMULATED"),
            status=CoursePurchase.Status.PAID,
            transaction_reference=validated_data.get("transaction_reference", ""),
            purchased_at=timezone.now(),
        )
        create_notification(
            user=course.tutor,
            actor=student,
            title="Course purchased",
            body=f"{student.get_full_name() or student.email} purchased {course.title}.",
            link=f"/api/payments/course-purchases/",
            kind="COURSE_PURCHASE",
        )
        return purchase


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)

    class Meta:
        model = LessonProgress
        fields = (
            "id",
            "student",
            "course",
            "lesson",
            "lesson_title",
            "watched_duration",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "course", "lesson", "completed_at", "created_at", "updated_at")


class LessonProgressUpdateSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    watched_duration = serializers.IntegerField(min_value=0)
    is_completed = serializers.BooleanField(required=False, default=False)


class PayoutSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)

    class Meta:
        model = Payout
        fields = ("id", "tutor", "tutor_name", "amount", "status", "paid_at", "created_at", "updated_at")
        read_only_fields = ("id", "tutor", "tutor_name", "status", "paid_at", "created_at", "updated_at")


class PayoutRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
