from rest_framework import serializers

from catalog.models import TutorSubject
from tutors.models import TutorProfile, TutorVerification, VerificationDocument


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "doc_type", "file", "created_at")
        read_only_fields = fields


class VerificationDocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "doc_type", "file")

    def create(self, validated_data):
        verification = self.context["verification"]
        return VerificationDocument.objects.create(verification=verification, **validated_data)


class TutorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorProfile
        fields = (
            "id",
            "user",
            "full_name",
            "headline",
            "bio",
            "hourly_rate",
            "currency",
            "location",
            "teaches_online",
            "teaches_in_person",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")


class PublicTutorSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = (
            "id",
            "full_name",
            "headline",
            "bio",
            "hourly_rate",
            "currency",
            "location",
            "teaches_online",
            "teaches_in_person",
            "verification_status",
            "subjects",
        )

    def get_verification_status(self, obj):
        verification = getattr(obj.user, "tutor_verification", None)
        return getattr(verification, "status", None)

    def get_subjects(self, obj):
        return list(
            TutorSubject.objects.filter(tutor=obj.user)
            .select_related("subject")
            .values_list("subject__name", flat=True)
            .distinct()
        )


class TutorVerificationSerializer(serializers.ModelSerializer):
    tutor_email = serializers.EmailField(source="tutor.email", read_only=True)
    tutor_name = serializers.SerializerMethodField()
    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = TutorVerification
        fields = (
            "id",
            "tutor",
            "tutor_email",
            "tutor_name",
            "status",
            "reviewed_by",
            "reviewed_at",
            "notes",
            "documents",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_tutor_name(self, obj):
        profile = getattr(obj.tutor, "tutor_profile", None)
        return getattr(profile, "full_name", "")


class TutorVerificationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TutorVerification.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
