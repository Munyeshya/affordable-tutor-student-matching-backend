from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from students.models import StudentProfile


User = get_user_model()


class AuthTests(TestCase):
    def test_register_student_creates_profile(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "email": "student@example.com",
                "password": "StrongPass123!",
                "full_name": "Student One",
                "role": "STUDENT",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="student@example.com").exists())
        user = User.objects.get(email="student@example.com")
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_me_requires_authentication(self):
        client = APIClient()
        response = client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)
