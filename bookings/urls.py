from django.urls import path

from bookings.views import BookingActionView, BookingCreateView, BookingListView, DisputeCreateView, DisputeDecisionView, DisputeListView

urlpatterns = [
    path("", BookingListView.as_view(), name="booking-list"),
    path("create/", BookingCreateView.as_view(), name="booking-create"),
    path("<int:pk>/action/", BookingActionView.as_view(), name="booking-action"),
    path("disputes/", DisputeListView.as_view(), name="dispute-list"),
    path("disputes/create/", DisputeCreateView.as_view(), name="dispute-create"),
    path("disputes/<int:pk>/decide/", DisputeDecisionView.as_view(), name="dispute-decide"),
]
