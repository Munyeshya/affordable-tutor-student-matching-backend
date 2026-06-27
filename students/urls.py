from django.urls import path

from students.views import ParentDashboardView, ParentProfileView, ParentStudentLinkListCreateView

urlpatterns = [
    path("me/", ParentProfileView.as_view(), name="parent-profile"),
    path("students/", ParentStudentLinkListCreateView.as_view(), name="parent-student-links"),
    path("dashboard/", ParentDashboardView.as_view(), name="parent-dashboard"),
]
