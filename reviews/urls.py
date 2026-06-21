from django.urls import path

from reviews.views import (
    LessonReviewCreateView,
    LessonReviewListView,
    ReviewCreateView,
    ReviewListView,
)

urlpatterns = [
    path("", ReviewListView.as_view(), name="review-list"),
    path("create/", ReviewCreateView.as_view(), name="review-create"),
    path("lesson/", LessonReviewListView.as_view(), name="lesson-review-list"),
    path("lesson/create/", LessonReviewCreateView.as_view(), name="lesson-review-create"),
]
