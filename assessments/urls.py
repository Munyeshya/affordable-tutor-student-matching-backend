from django.urls import path

from assessments.views import (
    AssessmentResultConfirmationCreateView,
    AssessmentResultConfirmationListView,
    LessonAssessmentCreateView,
    LessonAssessmentListView,
    LessonAssessmentQuestionCreateView,
    LessonAssessmentQuestionListView,
    LearningImpactSummaryView,
    StudentAssessmentAttemptCreateView,
    StudentAssessmentAttemptListView,
)

urlpatterns = [
    path("assessments/", LessonAssessmentListView.as_view(), name="assessment-list"),
    path("assessments/create/", LessonAssessmentCreateView.as_view(), name="assessment-create"),
    path("assessments/questions/create/", LessonAssessmentQuestionCreateView.as_view(), name="assessment-question-create"),
    path("assessments/<int:assessment_id>/questions/", LessonAssessmentQuestionListView.as_view(), name="assessment-question-list"),
    path("attempts/", StudentAssessmentAttemptListView.as_view(), name="assessment-attempt-list"),
    path("attempts/create/", StudentAssessmentAttemptCreateView.as_view(), name="assessment-attempt-create"),
    path("confirmations/", AssessmentResultConfirmationListView.as_view(), name="assessment-confirmation-list"),
    path("confirmations/create/", AssessmentResultConfirmationCreateView.as_view(), name="assessment-confirmation-create"),
    path("impact/", LearningImpactSummaryView.as_view(), name="learning-impact-summary"),
]
