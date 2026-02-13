from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TUTOR = "TUTOR", "Tutor"
        ADMIN = "ADMIN", "Admin"

    # Use email login
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # keep username for admin display

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
