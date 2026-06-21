from rest_framework import serializers

from catalog.models import Course, Lesson, Subject, TutorSubject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class TutorSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = TutorSubject
        fields = ("id", "tutor", "subject", "subject_name", "level", "experience_years", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "course",
            "title",
            "topic",
            "description",
            "video_file",
            "video_url",
            "duration",
            "order_number",
            "is_preview",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LessonSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ("id", "title", "topic", "duration", "order_number", "is_preview")


class CourseSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    lessons = LessonSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "tutor",
            "tutor_name",
            "title",
            "description",
            "subject",
            "subject_name",
            "academic_level",
            "price",
            "thumbnail",
            "status",
            "lessons",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tutor", "status", "created_at", "updated_at", "lessons")


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "title", "description", "subject", "academic_level", "price", "thumbnail", "status")
        read_only_fields = ("id",)

