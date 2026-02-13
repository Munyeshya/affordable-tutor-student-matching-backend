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
