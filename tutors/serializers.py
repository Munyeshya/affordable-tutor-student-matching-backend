from rest_framework import serializers

from catalog.models import TutorSubject
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, TutorVerificationDecision, VerificationDocument


class VerificationDocumentSerializer(serializers.ModelSerializer):
    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = VerificationDocument
        fields = ("id", "doc_type", "doc_type_display", "file", "created_at")
        read_only_fields = fields


class VerificationDocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "doc_type", "file")

    def validate(self, attrs):
        verification = self.context["verification"]
        doc_type = attrs["doc_type"]

        if doc_type in {VerificationDocument.DocType.ID, VerificationDocument.DocType.CERTIFICATE} and verification.documents.filter(
            doc_type=doc_type
        ).exists():
            raise serializers.ValidationError({"doc_type": f"{doc_type} document has already been uploaded."})

        return attrs

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
    subject_levels = serializers.SerializerMethodField()

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
            "subject_levels",
        )

    def get_verification_status(self, obj):
        verification = TutorVerification.objects.filter(tutor=obj.user).first()
        return getattr(verification, "status", None)

    def get_subjects(self, obj):
        return list(
            TutorSubject.objects.filter(tutor=obj.user)
            .select_related("subject")
            .values_list("subject__name", flat=True)
            .distinct()
        )

    def get_subject_levels(self, obj):
        return [
            {
                "subject": item["subject__name"],
                "level": item["level"],
            }
            for item in TutorSubject.objects.filter(tutor=obj.user).select_related("subject").values("subject__name", "level").order_by("subject__name", "level")
        ]


class TutorVerificationSerializer(serializers.ModelSerializer):
    tutor_email = serializers.EmailField(source="tutor.email", read_only=True)
    tutor_name = serializers.SerializerMethodField()
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    decisions = serializers.SerializerMethodField()
    has_required_documents = serializers.SerializerMethodField()
    missing_required_documents = serializers.SerializerMethodField()

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
            "has_required_documents",
            "missing_required_documents",
            "documents",
            "decisions",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_tutor_name(self, obj):
        profile = getattr(obj.tutor, "tutor_profile", None)
        return getattr(profile, "full_name", "")

    def get_has_required_documents(self, obj):
        return obj.has_required_documents()

    def get_missing_required_documents(self, obj):
        return obj.missing_required_document_types()

    def get_decisions(self, obj):
        return TutorVerificationDecisionSerializer(obj.decisions.select_related("admin").all(), many=True).data


class TutorVerificationDecisionSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source="admin.email", read_only=True)
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = TutorVerificationDecision
        fields = (
            "id",
            "status",
            "reason",
            "admin",
            "admin_email",
            "admin_name",
            "created_at",
        )
        read_only_fields = fields

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() or obj.admin.username


class TutorVerificationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TutorVerification.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)

    def validate(self, attrs):
        reason = (attrs.get("reason") or attrs.get("notes") or "").strip()
        if attrs["status"] == TutorVerification.Status.REJECTED and not reason:
            raise serializers.ValidationError({"reason": "A rejection reason is required."})
        attrs["reason"] = reason
        attrs.pop("notes", None)
        return attrs


class TutorAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorAgreement
        fields = (
            "id",
            "tutor",
            "status",
            "template_version",
            "agreed_to_terms",
            "signed_name",
            "signed_file",
            "signed_at",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tutor", "status", "template_version", "signed_at", "created_at", "updated_at")


class TutorAgreementUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorAgreement
        fields = ("signed_name", "signed_file", "agreed_to_terms")

    def validate_agreed_to_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("You must agree to the terms before uploading the signed agreement.")
        return value
