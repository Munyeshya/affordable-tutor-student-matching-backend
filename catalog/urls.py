from django.urls import path

from catalog.views import (
    CourseCreateView,
    CourseDetailView,
    CourseListView,
    LessonDetailView,
    LessonListCreateView,
    SubjectListView,
    TutorSubjectDeleteView,
    TutorSubjectListCreateView,
    TutorCourseListView,
)

urlpatterns = [
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("tutor-subjects/", TutorSubjectListCreateView.as_view(), name="tutor-subject-list-create"),
    path("tutor-subjects/<int:pk>/", TutorSubjectDeleteView.as_view(), name="tutor-subject-delete"),
    path("my-courses/", TutorCourseListView.as_view(), name="tutor-course-list"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/create/", CourseCreateView.as_view(), name="course-create"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:course_id>/lessons/", LessonListCreateView.as_view(), name="lesson-list-create"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
]
