from rest_framework import serializers

from accounts.models import User
from students.models import ParentProfile, ParentStudentLink, StudentProfile


class StudentProfileSummarySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "full_name",
            "email",
            "username",
            "level",
            "location",
            "budget_min",
            "budget_max",
            "prefers_online",
            "prefers_in_person",
        )
        read_only_fields = fields


class ParentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentProfile
        fields = ("id", "full_name", "location", "phone_number", "notes")
        read_only_fields = ("id",)


class ParentStudentLinkSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source="student.email", read_only=True)
    student_name = serializers.CharField(source="student.student_profile.full_name", read_only=True)

    class Meta:
        model = ParentStudentLink
        fields = ("id", "student", "student_email", "student_name", "label", "is_primary", "created_at")
        read_only_fields = ("id", "student", "student_email", "student_name", "created_at")


class ParentStudentLinkCreateSerializer(serializers.Serializer):
    student_email = serializers.EmailField()
    label = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    is_primary = serializers.BooleanField(required=False, default=False)

    def validate_student_email(self, value):
        try:
            student = User.objects.select_related("student_profile").get(email=value.lower().strip(), role=User.Role.STUDENT)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Student account not found.") from exc

        if not hasattr(student, "student_profile"):
            raise serializers.ValidationError("Student profile is required before linking.")

        self.context["student"] = student
        return value.lower().strip()

    def validate(self, attrs):
        parent = self.context["request"].user
        student = self.context.get("student")
        if not student:
            raise serializers.ValidationError({"student_email": "Student account not found."})

        if ParentStudentLink.objects.filter(parent=parent, student=student).exists():
            raise serializers.ValidationError({"student_email": "This student is already linked to your account."})

        attrs["student"] = student
        return attrs

    def create(self, validated_data):
        parent = self.context["request"].user
        return ParentStudentLink.objects.create(
            parent=parent,
            student=validated_data["student"],
            label=validated_data.get("label", ""),
            is_primary=validated_data.get("is_primary", False),
        )
