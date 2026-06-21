from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="payment")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_made")
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_received")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="RWF")
    provider = models.CharField(max_length=40, default="SIMULATED")  # later MTN/AIRTEL/Stripe
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

class TutorWalletLedger(TimeStampedModel):
    class Type(models.TextChoices):
        CREDIT_EARNING = "CREDIT_EARNING", "Credit: Earning"
        DEBIT_FEE = "DEBIT_FEE", "Debit: Fee"
        DEBIT_PAYOUT = "DEBIT_PAYOUT", "Debit: Payout"

    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_ledger")
    booking = models.ForeignKey("bookings.Booking", on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    entry_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")

class Payout(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        REJECTED = "REJECTED", "Rejected"

    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class CoursePurchase(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_purchases")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="purchases")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="RWF")
    provider = models.CharField(max_length=40, default="SIMULATED")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    transaction_reference = models.CharField(max_length=120, blank=True, default="", db_index=True)
    purchased_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "course")


class LessonProgress(TimeStampedModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="progress_entries")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="progress_entries")
    watched_duration = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "lesson")
