from django.urls import path

from analytics.views import AdminDashboardView, AdminPrintableReportView, MyPrintableReportView

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("report/", AdminPrintableReportView.as_view(), name="admin-printable-report"),
    path("my-report/", MyPrintableReportView.as_view(), name="my-printable-report"),
]
