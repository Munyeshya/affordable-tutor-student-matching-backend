from django.contrib import admin
from .models import TutorAgreement, TutorProfile, TutorVerification, TutorVerificationDecision, VerificationDocument



class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "hourly_rate", "location", "teaches_online", "teaches_in_person")
    search_fields = ("full_name", "user__email", "user__username", "location")


@admin.register(TutorVerification)
class TutorVerificationAdmin(admin.ModelAdmin):
    list_display = ("tutor", "status", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("tutor__email", "tutor__username", "notes")
    inlines = [VerificationDocumentInline]


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("verification", "doc_type", "created_at")
    list_filter = ("doc_type",)


@admin.register(TutorAgreement)
class TutorAgreementAdmin(admin.ModelAdmin):
    list_display = ("tutor", "status", "agreed_to_terms", "signed_name", "signed_at")
    list_filter = ("status", "agreed_to_terms")
    search_fields = ("tutor__email", "tutor__username", "signed_name")


@admin.register(TutorVerificationDecision)
class TutorVerificationDecisionAdmin(admin.ModelAdmin):
    list_display = ("verification", "admin", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("verification__tutor__email", "verification__tutor__username", "admin__email", "reason")
