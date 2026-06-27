from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class TutorProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_profile")
    full_name = models.CharField(max_length=120)
    headline = models.CharField(max_length=180, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="RWF")
    location = models.CharField(max_length=120, blank=True, default="")
    teaches_online = models.BooleanField(default=True)
    teaches_in_person = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

class TutorVerification(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    tutor = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_verification")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verifications_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def uploaded_required_document_types(self):
        return set(
            self.documents.filter(doc_type__in=[VerificationDocument.DocType.ID, VerificationDocument.DocType.CERTIFICATE]).values_list(
                "doc_type", flat=True
            )
        )

    def missing_required_document_types(self):
        uploaded = self.uploaded_required_document_types()
        required = [VerificationDocument.DocType.ID, VerificationDocument.DocType.CERTIFICATE]
        return [doc_type for doc_type in required if doc_type not in uploaded]

    def has_required_documents(self):
        return not self.missing_required_document_types()

    def has_signed_agreement(self):
        try:
            agreement = self.tutor.tutor_agreement
        except TutorAgreement.DoesNotExist:
            return False
        return bool(
            agreement
            and agreement.status == TutorAgreement.Status.SIGNED
            and agreement.agreed_to_terms
            and agreement.signed_file
        )

    def has_subject_levels(self):
        return self.tutor.tutor_subjects.exists()

    def is_marketplace_ready(self):
        return self.status == self.Status.APPROVED and self.has_required_documents() and self.has_signed_agreement() and self.has_subject_levels()


class TutorVerificationDecision(TimeStampedModel):
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    verification = models.ForeignKey(TutorVerification, on_delete=models.CASCADE, related_name="decisions")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_verification_decisions")
    status = models.CharField(max_length=20, choices=Status.choices)
    reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]


class VerificationDocument(TimeStampedModel):
    class DocType(models.TextChoices):
        ID = "ID", "National ID"
        CERTIFICATE = "CERTIFICATE", "Certificate"
        OTHER = "OTHER", "Other"

    verification = models.ForeignKey(TutorVerification, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.OTHER)
    file = models.FileField(upload_to="verification_docs/%Y/%m/")


class TutorAgreement(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SIGNED = "SIGNED", "Signed"

    tutor = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_agreement")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    template_version = models.CharField(max_length=20, default="v1")
    agreed_to_terms = models.BooleanField(default=False)
    signed_name = models.CharField(max_length=120, blank=True, default="")
    signed_file = models.FileField(upload_to="tutor_agreements/%Y/%m/", null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
