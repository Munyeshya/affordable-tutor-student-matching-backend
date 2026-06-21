from django.urls import path

from payments.views import (
    CoursePurchaseCreateView,
    CoursePurchaseListView,
    StudentLessonProgressListView,
    StudentLessonProgressUpdateView,
)

urlpatterns = [
    path("course-purchases/", CoursePurchaseListView.as_view(), name="course-purchase-list"),
    path("course-purchases/create/", CoursePurchaseCreateView.as_view(), name="course-purchase-create"),
    path("lesson-progress/", StudentLessonProgressListView.as_view(), name="lesson-progress-list"),
    path("lesson-progress/update/", StudentLessonProgressUpdateView.as_view(), name="lesson-progress-update"),
]

