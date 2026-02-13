from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class AvailabilitySlot(TimeStampedModel):
    class Mode(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        IN_PERSON = "IN_PERSON", "In Person"

    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_slots")
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.ONLINE)
    is_booked = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["tutor", "start_datetime"]),
        ]
