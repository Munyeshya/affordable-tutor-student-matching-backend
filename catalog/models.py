from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class Subject(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class TutorSubject(TimeStampedModel):
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="tutors")
    level = models.CharField(max_length=120, blank=True, default="")
    experience_years = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("tutor", "subject", "level")


class Course(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        PUBLISHED = "PUBLISHED", "Published"
        REJECTED = "REJECTED", "Rejected"

    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, default="")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="courses")
    academic_level = models.CharField(max_length=120, blank=True, default="", db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    thumbnail = models.ImageField(upload_to="course_thumbnails/%Y/%m/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    def __str__(self):
        return self.title


class Lesson(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200, db_index=True)
    topic = models.CharField(max_length=200, blank=True, default="", db_index=True)
    description = models.TextField(blank=True, default="")
    video_file = models.FileField(upload_to="lesson_videos/%Y/%m/", null=True, blank=True)
    video_url = models.URLField(blank=True, default="")
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in minutes")
    order_number = models.PositiveIntegerField(default=1, db_index=True)
    is_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ["course", "order_number", "created_at"]
        unique_together = ("course", "order_number")

    def __str__(self):
        return f"{self.course.title} - {self.title}"
