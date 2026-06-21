from django.urls import path

from bookings.views import BookingActionView, BookingCreateView, BookingListView

urlpatterns = [
    path("", BookingListView.as_view(), name="booking-list"),
    path("create/", BookingCreateView.as_view(), name="booking-create"),
    path("<int:pk>/action/", BookingActionView.as_view(), name="booking-action"),
]

