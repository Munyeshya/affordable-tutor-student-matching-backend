from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from availability.models import AvailabilitySlot
from bookings.models import Booking
from catalog.models import Subject, TutorSubject
from students.models import ParentProfile, ParentStudentLink, StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


class ParentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username="parent-user",
            email="parent-user@example.com",
            password="pass12345",
            role=User.Role.PARENT,
        )
        self.student = User.objects.create_user(
            username="linked-student",
            email="linked-student@example.com",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.tutor = User.objects.create_user(
            username="parent-tutor",
            email="parent-tutor@example.com",
            password="pass12345",
            role=User.Role.TUTOR,
        )
        ParentProfile.objects.create(user=self.parent, full_name="Parent User")
        StudentProfile.objects.create(user=self.student, full_name="Linked Student", level="Primary")
        TutorProfile.objects.create(user=self.tutor, full_name="Tutor User", teaches_online=True, hourly_rate=15)
        verification = TutorVerification.objects.create(tutor=self.tutor, status=TutorVerification.Status.APPROVED)
        subject = Subject.objects.create(name="Mathematics")
        TutorSubject.objects.create(tutor=self.tutor, subject=subject, level=TutorSubject.Level.PRIMARY)
        VerificationDocument.objects.create(verification=verification, doc_type=VerificationDocument.DocType.ID, file="verification_docs/id.pdf")
        VerificationDocument.objects.create(
            verification=verification,
            doc_type=VerificationDocument.DocType.CERTIFICATE,
            file="verification_docs/certificate.pdf",
        )
        TutorAgreement.objects.create(
            tutor=self.tutor,
            status=TutorAgreement.Status.SIGNED,
            agreed_to_terms=True,
            signed_name="Tutor User",
            signed_file="tutor_agreements/signed.pdf",
        )
        self.subject = subject
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=1)
        AvailabilitySlot.objects.create(
            tutor=self.tutor,
            start_datetime=self.start,
            end_datetime=self.end,
            mode=AvailabilitySlot.Mode.ONLINE,
        )
        ParentStudentLink.objects.create(parent=self.parent, student=self.student, label="Child")

    def test_parent_can_create_booking_for_linked_student(self):
        self.client.force_authenticate(self.parent)
        response = self.client.post(
            "/api/bookings/create/",
            {
                "student_id": self.student.id,
                "tutor_id": self.tutor.id,
                "subject_id": self.subject.id,
                "start_datetime": self.start.isoformat(),
                "end_datetime": self.end.isoformat(),
                "mode": "ONLINE",
                "notes": "Parent booking",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Booking.objects.filter(student=self.student, tutor=self.tutor).count(), 1)

    def test_parent_dashboard_lists_linked_student(self):
        self.client.force_authenticate(self.parent)
        response = self.client.get("/api/parents/dashboard/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["linked_students"], 1)
        self.assertEqual(response.data["linked_students"][0]["student"]["full_name"], "Linked Student")
