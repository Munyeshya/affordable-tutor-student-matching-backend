from django.utils import timezone
from rest_framework import serializers

from catalog.models import Course
from payments.models import CoursePurchase, LessonProgress


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

