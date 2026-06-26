from django.contrib import admin

from assessments.models import (
    AssessmentResultConfirmation,
    LessonAssessment,
    LessonAssessmentQuestion,
    StudentAssessmentAnswer,
    StudentAssessmentAttempt,
)

admin.site.register(LessonAssessment)
admin.site.register(LessonAssessmentQuestion)
admin.site.register(StudentAssessmentAttempt)
admin.site.register(StudentAssessmentAnswer)
admin.site.register(AssessmentResultConfirmation)

