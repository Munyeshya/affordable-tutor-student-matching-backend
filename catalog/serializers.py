from rest_framework import serializers

from catalog.models import Course, CourseModerationDecision, Lesson, Subject, TutorSubject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class TutorSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = TutorSubject
        fields = (
            "id",
            "tutor",
            "subject",
            "subject_name",
            "level",
            "level_display",
            "experience_years",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_level(self, value):
        if not value:
            raise serializers.ValidationError("Please choose the level you want to teach.")
        return value


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
        read_only_fields = ("id", "course", "created_at", "updated_at")


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
        read_only_fields = ("id", "status")

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)

        if user and user.is_authenticated and user.role == "TUTOR" and subject:
            if not TutorSubject.objects.filter(tutor=user, subject=subject).exists():
                raise serializers.ValidationError({"subject": "You can only create courses for subjects you teach."})

        return attrs


class CourseModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Course.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)

    def validate(self, attrs):
        reason = (attrs.get("reason") or attrs.get("notes") or "").strip()
        if attrs["status"] == Course.Status.REJECTED and not reason:
            raise serializers.ValidationError({"reason": "A rejection reason is required."})
        attrs["reason"] = reason
        attrs.pop("notes", None)
        return attrs


class CourseModerationDecisionSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source="admin.email", read_only=True)
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseModerationDecision
        fields = ("id", "status", "reason", "admin", "admin_email", "admin_name", "created_at")
        read_only_fields = fields

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() or obj.admin.username
