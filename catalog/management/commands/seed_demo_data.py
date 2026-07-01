from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from availability.models import AvailabilitySlot
from bookings.models import Booking, BookingEvent
from catalog.models import Course, CourseModerationDecision, Lesson, Subject, TutorSubject
from notifications.models import Notification
from payments.models import CoursePurchase, Payment, Payout, PayoutDecision, TutorWalletLedger, LessonProgress
from reviews.models import LessonReview, Review
from students.models import ParentProfile, ParentStudentLink, StudentProfile
from tutors.models import TutorAgreement, TutorProfile, TutorVerification, VerificationDocument


DEMO_PASSWORD = "Password123!"
NOW = timezone.now()


class Command(BaseCommand):
    help = "Seed demo data for frontend development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-media",
            action="store_true",
            help="Remove and recreate seeded uploaded files before writing demo file fields.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self.ensure_admin()
        student = self.ensure_student()
        parent = self.ensure_parent()

        subjects = self.ensure_subjects()
        tutors = self.ensure_tutors(admin)

        self.ensure_parent_student_link(parent, student)

        self.ensure_tutor_subjects(tutors, subjects)
        courses = self.ensure_courses(tutors, subjects, admin)
        lessons = self.ensure_lessons(courses)
        bookings = self.ensure_booking_flow(student, tutors[0], subjects[0], lessons[0], admin)
        self.ensure_notifications(student, tutors[0], admin)
        self.ensure_financial_records(student, tutors[0], courses[0], bookings[0], admin)
        self.ensure_availability(tutors)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: users={User.objects.count()}, subjects={Subject.objects.count()}, tutors={TutorProfile.objects.count()}, courses={Course.objects.count()}, lessons={Lesson.objects.count()}"
            )
        )

    def ensure_admin(self):
        user = User.objects.filter(email="admin@isomo.rw").first()
        if user is None:
            return User.objects.create_superuser(
                username="isomoadmin",
                email="admin@isomo.rw",
                password=DEMO_PASSWORD,
                first_name="Isomo",
                last_name="Admin",
            )

        user.username = user.username or "isomoadmin"
        user.first_name = "Isomo"
        user.last_name = "Admin"
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def ensure_student(self):
        user = User.objects.filter(email="student@isomo.rw").first()
        if user is None:
            user = User.objects.create_user(
                username="studentisomo",
                email="student@isomo.rw",
                password=DEMO_PASSWORD,
                role=User.Role.STUDENT,
                first_name="Aline",
                last_name="M.",
            )
        else:
            user.username = "studentisomo"
            user.first_name = "Aline"
            user.last_name = "M."
            user.role = User.Role.STUDENT
            user.set_password(DEMO_PASSWORD)
            user.save()

        profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": "Aline M.",
                "level": "Secondary upper level",
                "location": "Kigali",
                "budget_min": Decimal("5000.00"),
                "budget_max": Decimal("15000.00"),
                "prefers_online": True,
                "prefers_in_person": False,
            },
        )
        profile.full_name = "Aline M."
        profile.level = "Secondary upper level"
        profile.location = "Kigali"
        profile.budget_min = Decimal("5000.00")
        profile.budget_max = Decimal("15000.00")
        profile.prefers_online = True
        profile.prefers_in_person = False
        profile.save()
        return user

    def ensure_parent(self):
        user = User.objects.filter(email="parent@isomo.rw").first()
        if user is None:
            user = User.objects.create_user(
                username="parentisomo",
                email="parent@isomo.rw",
                password=DEMO_PASSWORD,
                role=User.Role.PARENT,
                first_name="Beatrice",
                last_name="N.",
            )
        else:
            user.username = "parentisomo"
            user.first_name = "Beatrice"
            user.last_name = "N."
            user.role = User.Role.PARENT
            user.set_password(DEMO_PASSWORD)
            user.save()

        profile, _ = ParentProfile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": "Beatrice N.",
                "location": "Kigali",
                "phone_number": "+250700000001",
                "notes": "Prefers trusted tutors for after-school support.",
            },
        )
        profile.full_name = "Beatrice N."
        profile.location = "Kigali"
        profile.phone_number = "+250700000001"
        profile.notes = "Prefers trusted tutors for after-school support."
        profile.save()
        return user

    def ensure_tutors(self, admin):
        tutor_specs = [
            {
                "email": "maths@isomo.rw",
                "username": "maths_tutor",
                "full_name": "Nicolas U.",
                "headline": "Mathematics tutor for secondary students",
                "bio": "I help learners build strong foundations in algebra, geometry, and exam preparation.",
                "hourly_rate": Decimal("3500.00"),
                "location": "Kigali",
                "online": True,
                "in_person": False,
                "verification": TutorVerification.Status.APPROVED,
            },
            {
                "email": "english@isomo.rw",
                "username": "english_tutor",
                "full_name": "Claire K.",
                "headline": "English and communication tutor",
                "bio": "Focused on grammar, writing, speaking, and confidence-building for exams.",
                "hourly_rate": Decimal("3000.00"),
                "location": "Kigali",
                "online": True,
                "in_person": True,
                "verification": TutorVerification.Status.APPROVED,
            },
            {
                "email": "computer@isomo.rw",
                "username": "computer_tutor",
                "full_name": "Emmanuel T.",
                "headline": "Computer literacy and digital skills tutor",
                "bio": "Practical lessons for productivity tools, basic programming, and coursework support.",
                "hourly_rate": Decimal("4500.00"),
                "location": "Kigali",
                "online": True,
                "in_person": False,
                "verification": TutorVerification.Status.PENDING,
            },
        ]

        tutors = []
        for spec in tutor_specs:
            user = User.objects.filter(email=spec["email"]).first()
            if user is None:
                user = User.objects.create_user(
                    username=spec["username"],
                    email=spec["email"],
                    password=DEMO_PASSWORD,
                    role=User.Role.TUTOR,
                    first_name=spec["full_name"].split(" ", 1)[0],
                    last_name=spec["full_name"].split(" ", 1)[-1],
                )
            else:
                user.username = spec["username"]
                user.first_name = spec["full_name"].split(" ", 1)[0]
                user.last_name = spec["full_name"].split(" ", 1)[-1]
                user.role = User.Role.TUTOR
                user.set_password(DEMO_PASSWORD)
                user.save()

            profile, _ = TutorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": spec["full_name"],
                    "headline": spec["headline"],
                    "bio": spec["bio"],
                    "hourly_rate": spec["hourly_rate"],
                    "currency": "RWF",
                    "location": spec["location"],
                    "teaches_online": spec["online"],
                    "teaches_in_person": spec["in_person"],
                },
            )
            profile.full_name = spec["full_name"]
            profile.headline = spec["headline"]
            profile.bio = spec["bio"]
            profile.hourly_rate = spec["hourly_rate"]
            profile.currency = "RWF"
            profile.location = spec["location"]
            profile.teaches_online = spec["online"]
            profile.teaches_in_person = spec["in_person"]
            profile.save()

            verification, _ = TutorVerification.objects.get_or_create(
                tutor=user,
                defaults={
                    "status": spec["verification"],
                    "reviewed_by": admin if spec["verification"] == TutorVerification.Status.APPROVED else None,
                    "reviewed_at": NOW - timedelta(days=2) if spec["verification"] == TutorVerification.Status.APPROVED else None,
                    "notes": "Seeded demo verification.",
                },
            )
            verification.status = spec["verification"]
            verification.reviewed_by = admin if spec["verification"] == TutorVerification.Status.APPROVED else None
            verification.reviewed_at = NOW - timedelta(days=2) if spec["verification"] == TutorVerification.Status.APPROVED else None
            verification.notes = "Seeded demo verification."
            verification.save()

            if spec["verification"] == TutorVerification.Status.APPROVED:
                self.ensure_verification_document(verification, VerificationDocument.DocType.ID, "id.txt", b"Demo ID document for Isomo.")
                self.ensure_verification_document(verification, VerificationDocument.DocType.CERTIFICATE, "certificate.txt", b"Demo certificate for Isomo.")
                agreement, _ = TutorAgreement.objects.get_or_create(
                    tutor=user,
                    defaults={
                        "status": TutorAgreement.Status.SIGNED,
                        "template_version": "v1",
                        "agreed_to_terms": True,
                        "signed_name": spec["full_name"],
                        "signed_at": NOW - timedelta(days=2),
                        "notes": "Seeded signed agreement.",
                    },
                )
                agreement.status = TutorAgreement.Status.SIGNED
                agreement.template_version = "v1"
                agreement.agreed_to_terms = True
                agreement.signed_name = spec["full_name"]
                agreement.signed_at = NOW - timedelta(days=2)
                agreement.notes = "Seeded signed agreement."
                agreement.save()

            tutors.append(user)

        return tutors

    def ensure_verification_document(self, verification, doc_type, filename, content):
        document = VerificationDocument.objects.filter(verification=verification, doc_type=doc_type).first()
        if document is None:
            document = VerificationDocument(verification=verification, doc_type=doc_type)
        if not document.file:
            document.file.save(filename, ContentFile(content), save=False)
        document.save()
        return document

    def ensure_parent_student_link(self, parent, student):
        link, _ = ParentStudentLink.objects.get_or_create(
            parent=parent,
            student=student,
            defaults={"label": "Main guardian", "is_primary": True},
        )
        link.label = "Main guardian"
        link.is_primary = True
        link.save()
        return link

    def ensure_subjects(self):
        subject_names = ["Mathematics", "English", "Computer", "Physics", "Biology"]
        subjects = []
        for name in subject_names:
            subject, _ = Subject.objects.get_or_create(name=name, defaults={"is_active": True})
            subject.is_active = True
            subject.save()
            subjects.append(subject)
        return subjects

    def ensure_tutor_subjects(self, tutors, subjects):
        subject_map = {subject.name: subject for subject in subjects}
        tutor_subject_specs = [
            (tutors[0], subject_map["Mathematics"], TutorSubject.Level.PRIMARY, 5),
            (tutors[0], subject_map["Mathematics"], TutorSubject.Level.SECONDARY_LOWER, 7),
            (tutors[1], subject_map["English"], TutorSubject.Level.SECONDARY_UPPER, 6),
            (tutors[1], subject_map["English"], TutorSubject.Level.UNIVERSITY, 4),
            (tutors[2], subject_map["Computer"], TutorSubject.Level.PRIMARY, 3),
            (tutors[2], subject_map["Computer"], TutorSubject.Level.UNIVERSITY, 5),
        ]
        for tutor, subject, level, years in tutor_subject_specs:
            tutor_subject, _ = TutorSubject.objects.get_or_create(
                tutor=tutor,
                subject=subject,
                level=level,
                defaults={"experience_years": years},
            )
            tutor_subject.experience_years = years
            tutor_subject.save()

    def ensure_courses(self, tutors, subjects, admin):
        subject_map = {subject.name: subject for subject in subjects}
        course_specs = [
            {
                "tutor": tutors[0],
                "title": "Algebra Basics",
                "description": "A practical start to algebra, equations, and problem solving.",
                "subject": subject_map["Mathematics"],
                "level": "Secondary lower level",
                "price": Decimal("12000.00"),
                "status": Course.Status.PUBLISHED,
            },
            {
                "tutor": tutors[1],
                "title": "English Writing Essentials",
                "description": "Improve writing structure, vocabulary, and exam responses.",
                "subject": subject_map["English"],
                "level": "Secondary upper level",
                "price": Decimal("10000.00"),
                "status": Course.Status.PUBLISHED,
            },
            {
                "tutor": tutors[2],
                "title": "Computer Skills for Beginners",
                "description": "Learn files, tools, internet basics, and digital confidence.",
                "subject": subject_map["Computer"],
                "level": "University",
                "price": Decimal("15000.00"),
                "status": Course.Status.PENDING_REVIEW,
            },
        ]

        courses = []
        for spec in course_specs:
            course, _ = Course.objects.get_or_create(
                tutor=spec["tutor"],
                title=spec["title"],
                defaults={
                    "description": spec["description"],
                    "subject": spec["subject"],
                    "academic_level": spec["level"],
                    "price": spec["price"],
                    "status": spec["status"],
                },
            )
            course.description = spec["description"]
            course.subject = spec["subject"]
            course.academic_level = spec["level"]
            course.price = spec["price"]
            course.status = spec["status"]
            course.save()
            courses.append(course)

            if course.status == Course.Status.PUBLISHED:
                decision, _ = CourseModerationDecision.objects.get_or_create(
                    course=course,
                    admin=admin,
                    status=CourseModerationDecision.Status.PUBLISHED,
                    defaults={"reason": "Seeded approval for demo content."},
                )
                decision.reason = "Seeded approval for demo content."
                decision.save()

        return courses

    def ensure_lessons(self, courses):
        lesson_specs = [
            (courses[0], "Working with equations", "Algebra", 1, True),
            (courses[0], "Word problems", "Algebra", 2, False),
            (courses[1], "Building clear paragraphs", "Writing", 1, True),
            (courses[1], "Editing and proofreading", "Writing", 2, False),
            (courses[2], "Using common computer tools", "Digital literacy", 1, True),
            (courses[2], "Files and folders", "Digital literacy", 2, False),
        ]
        lessons = []
        for course, title, topic, order_number, is_preview in lesson_specs:
            lesson, _ = Lesson.objects.get_or_create(
                course=course,
                order_number=order_number,
                defaults={
                    "title": title,
                    "topic": topic,
                    "description": f"Demo lesson: {title}.",
                    "duration": 30,
                    "is_preview": is_preview,
                },
            )
            lesson.title = title
            lesson.topic = topic
            lesson.description = f"Demo lesson: {title}."
            lesson.duration = 30
            lesson.is_preview = is_preview
            lesson.save()
            lessons.append(lesson)
        return lessons

    def ensure_booking_flow(self, student, tutor, subject, lesson, admin):
        start = NOW + timedelta(days=2, hours=2)
        end = start + timedelta(hours=1)

        booking, _ = Booking.objects.get_or_create(
            student=student,
            tutor=tutor,
            subject=subject,
            start_datetime=start,
            defaults={
                "end_datetime": end,
                "mode": "ONLINE",
                "status": Booking.Status.COMPLETED,
                "hourly_rate": Decimal("3500.00"),
                "total_amount": Decimal("3500.00"),
                "currency": "RWF",
                "notes": "Seeded demo booking.",
            },
        )
        booking.end_datetime = end
        booking.mode = "ONLINE"
        booking.status = Booking.Status.COMPLETED
        booking.hourly_rate = Decimal("3500.00")
        booking.total_amount = Decimal("3500.00")
        booking.currency = "RWF"
        booking.notes = "Seeded demo booking."
        booking.save()

        BookingEvent.objects.get_or_create(
            booking=booking,
            action="BOOKED",
            defaults={"actor": student, "message": "Student booked a demo lesson."},
        )
        BookingEvent.objects.get_or_create(
            booking=booking,
            action="COMPLETED",
            defaults={"actor": tutor, "message": "Lesson marked as completed."},
        )

        review, _ = Review.objects.get_or_create(
            booking=booking,
            defaults={
                "student": student,
                "tutor": tutor,
                "rating": 5,
                "comment": "Clear explanation and affordable pricing.",
            },
        )
        review.student = student
        review.tutor = tutor
        review.rating = 5
        review.comment = "Clear explanation and affordable pricing."
        review.save()

        lesson_review, _ = LessonReview.objects.get_or_create(
            lesson=lesson,
            student=student,
            defaults={
                "tutor": tutor,
                "rating": 5,
                "comment": "Helpful lesson with a good pace.",
            },
        )
        lesson_review.tutor = tutor
        lesson_review.rating = 5
        lesson_review.comment = "Helpful lesson with a good pace."
        lesson_review.save()

        return booking, review, lesson_review

    def ensure_notifications(self, student, tutor, admin):
        notifications = [
            (student, tutor, "Tutor approved", "Your tutor profile is ready for matching.", "tutor_status", "/tutors"),
            (tutor, admin, "New booking", "A student has requested a lesson.", "booking", "/tutor/dashboard"),
        ]
        for user, actor, title, body, kind, link in notifications:
            note, _ = Notification.objects.get_or_create(
                user=user,
                title=title,
                defaults={
                    "body": body,
                    "link": link,
                    "kind": kind,
                    "is_read": False,
                    "actor": actor,
                },
            )
            note.body = body
            note.link = link
            note.kind = kind
            note.actor = actor
            note.is_read = False
            note.read_at = None
            note.save()

    def ensure_financial_records(self, student, tutor, course, booking, admin):
        payment, _ = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                "student": student,
                "tutor": tutor,
                "amount": Decimal("3500.00"),
                "currency": "RWF",
                "provider": "SIMULATED",
                "status": Payment.Status.PAID,
                "paid_at": NOW - timedelta(days=1),
            },
        )
        payment.student = student
        payment.tutor = tutor
        payment.amount = Decimal("3500.00")
        payment.currency = "RWF"
        payment.provider = "SIMULATED"
        payment.status = Payment.Status.PAID
        payment.paid_at = NOW - timedelta(days=1)
        payment.save()

        TutorWalletLedger.objects.get_or_create(
            tutor=tutor,
            booking=booking,
            entry_type=TutorWalletLedger.Type.CREDIT_EARNING,
            defaults={"amount": Decimal("2975.00"), "note": "Earning from completed lesson."},
        )

        payout, _ = Payout.objects.get_or_create(
            tutor=tutor,
            amount=Decimal("2500.00"),
            defaults={"status": Payout.Status.APPROVED, "paid_at": None},
        )
        payout.status = Payout.Status.APPROVED
        payout.save()

        PayoutDecision.objects.get_or_create(
            payout=payout,
            admin=admin,
            status=PayoutDecision.Status.APPROVED,
            defaults={"reason": "Seeded approval for demo payout."},
        )

        CoursePurchase.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                "amount": course.price,
                "currency": "RWF",
                "provider": "SIMULATED",
                "status": CoursePurchase.Status.PAID,
                "transaction_reference": "DEMO-COURSE-001",
                "purchased_at": NOW - timedelta(days=3),
            },
        )

        LessonProgress.objects.get_or_create(
            student=student,
            lesson=course.lessons.order_by("order_number").first(),
            defaults={
                "course": course,
                "watched_duration": 25,
                "is_completed": True,
                "completed_at": NOW - timedelta(days=2),
            },
        )

    def ensure_availability(self, tutors):
        for index, tutor in enumerate(tutors):
            for offset in range(2):
                start = NOW + timedelta(days=index + offset + 1, hours=9)
                end = start + timedelta(hours=1)
                slot, _ = AvailabilitySlot.objects.get_or_create(
                    tutor=tutor,
                    start_datetime=start,
                    end_datetime=end,
                    defaults={
                        "mode": AvailabilitySlot.Mode.ONLINE if offset % 2 == 0 else AvailabilitySlot.Mode.IN_PERSON,
                        "is_booked": False,
                    },
                )
                slot.mode = AvailabilitySlot.Mode.ONLINE if offset % 2 == 0 else AvailabilitySlot.Mode.IN_PERSON
                slot.is_booked = False
                slot.save()
