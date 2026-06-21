from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class Review(TimeStampedModel):
    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="review")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written")
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")

    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")


class LessonReview(TimeStampedModel):
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="reviews")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_reviews_written")
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_reviews_received")

    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("lesson", "student")
