from django.urls import path

from availability.views import PublicTutorAvailabilityView, TutorAvailabilityDeleteView, TutorAvailabilityListCreateView

urlpatterns = [
    path("", PublicTutorAvailabilityView.as_view(), name="availability-public-list"),
    path("me/", TutorAvailabilityListCreateView.as_view(), name="availability-me"),
    path("<int:pk>/", TutorAvailabilityDeleteView.as_view(), name="availability-delete"),
]

