from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_bookings")
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_bookings")
    subject = models.ForeignKey("catalog.Subject", on_delete=models.SET_NULL, null=True, related_name="bookings")

    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)

    mode = models.CharField(max_length=20, default="ONLINE")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="RWF")
    notes = models.TextField(blank=True, default="")

class BookingEvent(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="booking_events")
    action = models.CharField(max_length=30)
    message = models.TextField(blank=True, default="")
