from django.urls import path

from tutors.views import (
    TutorAgreementDownloadView,
    TutorAgreementView,
    PendingTutorVerificationListView,
    PublicTutorListView,
    TutorProfileMeView,
    TutorProfileCompletionView,
    TutorSetupChecklistView,
    TutorVerificationDocumentView,
    TutorVerificationDecisionView,
)

urlpatterns = [
    path("", PublicTutorListView.as_view(), name="public-tutor-list"),
    path("me/", TutorProfileMeView.as_view(), name="tutor-me"),
    path("me/completion/", TutorProfileCompletionView.as_view(), name="tutor-me-completion"),
    path("setup/checklist/", TutorSetupChecklistView.as_view(), name="tutor-setup-checklist"),
    path("agreement/", TutorAgreementView.as_view(), name="tutor-agreement"),
    path("agreement/download/", TutorAgreementDownloadView.as_view(), name="tutor-agreement-download"),
    path("documents/", TutorVerificationDocumentView.as_view(), name="tutor-documents"),
    path("verifications/", PendingTutorVerificationListView.as_view(), name="tutor-verification-list"),
    path("verifications/<int:pk>/decide/", TutorVerificationDecisionView.as_view(), name="tutor-verification-decide"),
]
