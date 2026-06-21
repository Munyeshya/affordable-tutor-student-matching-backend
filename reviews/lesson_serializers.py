from rest_framework import serializers

from catalog.models import Lesson
from reviews.models import LessonReview


class LessonReviewSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = LessonReview
        fields = (
            "id",
            "lesson",
            "lesson_title",
            "student",
            "student_name",
            "tutor",
            "tutor_name",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "tutor", "created_at", "updated_at")


class LessonReviewCreateSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_lesson_id(self, value):
        try:
            lesson = Lesson.objects.select_related("course", "course__tutor").get(pk=value)
        except Lesson.DoesNotExist:
            raise serializers.ValidationError("Lesson not found.")

        request = self.context["request"]
        if lesson.course.tutor_id == request.user.id:
            raise serializers.ValidationError("Tutors cannot review their own lessons.")
        if LessonReview.objects.filter(lesson=lesson, student=request.user).exists():
            raise serializers.ValidationError("You have already reviewed this lesson.")

        return value

    def create(self, validated_data):
        lesson = Lesson.objects.select_related("course", "course__tutor").get(pk=validated_data["lesson_id"])
        return LessonReview.objects.create(
            lesson=lesson,
            student=self.context["request"].user,
            tutor=lesson.course.tutor,
            rating=validated_data["rating"],
            comment=validated_data.get("comment", ""),
        )
