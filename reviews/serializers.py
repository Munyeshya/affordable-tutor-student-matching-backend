from rest_framework import serializers

from bookings.models import Booking
from reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "student",
            "student_name",
            "tutor",
            "tutor_name",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "student", "tutor", "created_at", "updated_at")


class ReviewCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.select_related("student", "tutor").get(pk=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")

        request = self.context["request"]
        if booking.student_id != request.user.id:
            raise serializers.ValidationError("You can only review your own booking.")
        if booking.status != Booking.Status.COMPLETED:
            raise serializers.ValidationError("You can only review a completed booking.")
        if hasattr(booking, "review"):
            raise serializers.ValidationError("This booking has already been reviewed.")

        return value

    def create(self, validated_data):
        booking = Booking.objects.select_related("student", "tutor").get(pk=validated_data["booking_id"])
        return Review.objects.create(
            booking=booking,
            student=booking.student,
            tutor=booking.tutor,
            rating=validated_data["rating"],
            comment=validated_data.get("comment", ""),
        )

