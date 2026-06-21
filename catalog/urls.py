from django.urls import path

from catalog.views import (
    AdminCourseModerationView,
    CourseCreateView,
    CourseDetailView,
    CourseListView,
    PublicCourseDetailView,
    LessonDetailView,
    LessonListCreateView,
    SubjectListView,
    TutorSubjectDeleteView,
    TutorSubjectListCreateView,
    TutorCourseListView,
    TutorCourseSubmitForReviewView,
)

urlpatterns = [
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("tutor-subjects/", TutorSubjectListCreateView.as_view(), name="tutor-subject-list-create"),
    path("tutor-subjects/<int:pk>/", TutorSubjectDeleteView.as_view(), name="tutor-subject-delete"),
    path("my-courses/", TutorCourseListView.as_view(), name="tutor-course-list"),
    path("courses/<int:pk>/submit/", TutorCourseSubmitForReviewView.as_view(), name="course-submit"),
    path("courses/<int:pk>/moderate/", AdminCourseModerationView.as_view(), name="course-moderate"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/public/", PublicCourseDetailView.as_view(), name="public-course-detail"),
    path("courses/create/", CourseCreateView.as_view(), name="course-create"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:course_id>/lessons/", LessonListCreateView.as_view(), name="lesson-list-create"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
]
