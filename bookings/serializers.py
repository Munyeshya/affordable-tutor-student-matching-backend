from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from availability.models import AvailabilitySlot
from bookings.models import Booking, BookingEvent, Dispute, DisputeDecision
from catalog.models import Subject
from catalog.models import TutorSubject
from notifications.utils import create_notification
from tutors.models import TutorVerification


class BookingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingEvent
        fields = ("id", "action", "message", "created_at", "actor")
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    events = BookingEventSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "student",
            "tutor",
            "subject",
            "start_datetime",
            "end_datetime",
            "mode",
            "status",
            "hourly_rate",
            "total_amount",
            "currency",
            "notes",
            "events",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "status", "hourly_rate", "total_amount", "currency", "created_at", "updated_at", "events")


class BookingCreateSerializer(serializers.Serializer):
    tutor_id = serializers.IntegerField()
    subject_id = serializers.IntegerField()
    availability_slot_id = serializers.IntegerField(required=False, allow_null=True)
    start_datetime = serializers.DateTimeField(required=False)
    end_datetime = serializers.DateTimeField(required=False)
    mode = serializers.ChoiceField(choices=("ONLINE", "IN_PERSON"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        request = self.context["request"]
        tutor_id = attrs["tutor_id"]
        subject_id = attrs["subject_id"]

        try:
            tutor = User.objects.get(pk=tutor_id, role=User.Role.TUTOR)
        except User.DoesNotExist:
            raise serializers.ValidationError({"tutor_id": "Tutor not found."})

        verification = TutorVerification.objects.filter(tutor=tutor).first()
        if not verification or not verification.is_marketplace_ready():
            raise serializers.ValidationError({"tutor_id": "Tutor must be approved before booking."})

        try:
            subject = Subject.objects.get(pk=subject_id, is_active=True)
        except Subject.DoesNotExist:
            raise serializers.ValidationError({"subject_id": "Subject not found."})

        if not TutorSubject.objects.filter(tutor=tutor, subject=subject).exists():
            raise serializers.ValidationError({"subject_id": "Tutor does not teach this subject."})

        if attrs["mode"] == "ONLINE":
            profile = getattr(tutor, "tutor_profile", None)
            if profile and not profile.teaches_online:
                raise serializers.ValidationError({"mode": "Tutor does not offer online sessions."})
        if attrs["mode"] == "IN_PERSON":
            profile = getattr(tutor, "tutor_profile", None)
            if profile and not profile.teaches_in_person:
                raise serializers.ValidationError({"mode": "Tutor does not offer in-person sessions."})

        slot = None
        if attrs.get("availability_slot_id"):
            try:
                slot = AvailabilitySlot.objects.get(pk=attrs["availability_slot_id"], tutor=tutor, is_booked=False)
            except AvailabilitySlot.DoesNotExist:
                raise serializers.ValidationError({"availability_slot_id": "Available slot not found."})

            if slot.mode != attrs["mode"]:
                raise serializers.ValidationError({"availability_slot_id": "Slot mode does not match booking mode."})

            attrs["start_datetime"] = slot.start_datetime
            attrs["end_datetime"] = slot.end_datetime
        else:
            if not attrs.get("start_datetime") or not attrs.get("end_datetime"):
                raise serializers.ValidationError("start_datetime and end_datetime are required when no slot is provided.")

        if attrs["start_datetime"] >= attrs["end_datetime"]:
            raise serializers.ValidationError({"end_datetime": "End time must be after start time."})

        if attrs["start_datetime"] < timezone.now():
            raise serializers.ValidationError({"start_datetime": "Cannot book a past session."})

        if AvailabilitySlot.objects.filter(
            tutor=tutor,
            is_booked=False,
            start_datetime__lte=attrs["start_datetime"],
            end_datetime__gte=attrs["end_datetime"],
        ).exists() is False and slot is None:
            raise serializers.ValidationError({"availability_slot_id": "No matching availability slot found for this time range."})

        if Booking.objects.filter(
            tutor=tutor,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lt=attrs["end_datetime"],
            end_datetime__gt=attrs["start_datetime"],
        ).exists():
            raise serializers.ValidationError("Tutor already has a conflicting booking.")

        attrs["tutor"] = tutor
        attrs["subject"] = subject
        attrs["slot"] = slot
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        student = self.context["request"].user
        slot = validated_data.pop("slot", None)
        tutor = validated_data.pop("tutor")
        subject = validated_data.pop("subject")

        hourly_rate = getattr(getattr(tutor, "tutor_profile", None), "hourly_rate", None)
        start_datetime = validated_data["start_datetime"]
        end_datetime = validated_data["end_datetime"]
        hours = Decimal(str(max((end_datetime - start_datetime).total_seconds() / 3600, 0)))
        total_amount = (hourly_rate * hours) if hourly_rate is not None else None

        booking = Booking.objects.create(
            student=student,
            tutor=tutor,
            subject=subject,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            mode=validated_data["mode"],
            notes=validated_data.get("notes", ""),
            hourly_rate=hourly_rate,
            total_amount=total_amount,
            currency=getattr(getattr(tutor, "tutor_profile", None), "currency", "RWF"),
        )

        BookingEvent.objects.create(booking=booking, actor=student, action="CREATED", message="Booking created.")
        create_notification(
            user=tutor,
            actor=student,
            title="New booking request",
            body=f"{student.get_full_name() or student.email} created a booking request.",
            link=f"/api/bookings/{booking.id}/",
            kind="BOOKING_CREATED",
        )

        if slot:
            slot.is_booked = True
            slot.save(update_fields=["is_booked", "updated_at"])

        return booking


class BookingActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("ACCEPT", "REJECT", "CANCEL", "COMPLETE"))
    message = serializers.CharField(required=False, allow_blank=True, default="")


class DisputeDecisionSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source="admin.email", read_only=True)
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = DisputeDecision
        fields = ("id", "status", "comment", "admin", "admin_email", "admin_name", "created_at")
        read_only_fields = fields

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() or obj.admin.username


class DisputeSerializer(serializers.ModelSerializer):
    reported_by_email = serializers.EmailField(source="reported_by.email", read_only=True)
    reported_against_email = serializers.EmailField(source="reported_against.email", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    decisions = DisputeDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = Dispute
        fields = (
            "id",
            "booking",
            "booking_id",
            "reported_by",
            "reported_by_email",
            "reported_against",
            "reported_against_email",
            "reason",
            "status",
            "admin_comment",
            "resolved_at",
            "decisions",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DisputeCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    reason = serializers.CharField()

    def validate(self, attrs):
        request = self.context["request"]
        try:
            booking = Booking.objects.select_related("student", "tutor").get(pk=attrs["booking_id"])
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"booking_id": "Booking not found."})

        if request.user.id not in {booking.student_id, booking.tutor_id}:
            raise serializers.ValidationError({"booking_id": "You can only report your own bookings."})

        if not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "Please provide a reason for the dispute."})

        attrs["booking"] = booking
        attrs["reported_against"] = booking.tutor if request.user.id == booking.student_id else booking.student
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        dispute = Dispute.objects.create(
            booking=validated_data["booking"],
            reported_by=request.user,
            reported_against=validated_data["reported_against"],
            reason=validated_data["reason"].strip(),
        )
        return dispute


class DisputeActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DisputeDecision.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
