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


class PublicCourseSerializer(CourseSerializer):
    lessons = serializers.SerializerMethodField()

    def get_lessons(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return LessonSummarySerializer(obj.lessons.filter(is_preview=True), many=True).data

        from payments.models import CoursePurchase
        from accounts.models import User

        user = request.user
        if user.role in {User.Role.TUTOR, User.Role.ADMIN} or CoursePurchase.objects.filter(student=user, course=obj, status=CoursePurchase.Status.PAID).exists():
            return LessonSummarySerializer(obj.lessons.all(), many=True).data

        return LessonSummarySerializer(obj.lessons.filter(is_preview=True), many=True).data


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "title", "description", "subject", "academic_level", "price", "thumbnail", "status")
        read_only_fields = ("id",)


class CourseModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Course.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
