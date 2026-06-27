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

class VerificationDocument(TimeStampedModel):
    class DocType(models.TextChoices):
        ID = "ID", "National ID"
        CERTIFICATE = "CERTIFICATE", "Certificate"
        OTHER = "OTHER", "Other"

    verification = models.ForeignKey(TutorVerification, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.OTHER)
    file = models.FileField(upload_to="verification_docs/%Y/%m/")
