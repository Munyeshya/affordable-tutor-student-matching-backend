from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class StudentProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=120)
    level = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=120, blank=True, default="")
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prefers_online = models.BooleanField(default=True)
    prefers_in_person = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class ParentProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_profile")
    full_name = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True, default="")
    phone_number = models.CharField(max_length=30, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return self.full_name
