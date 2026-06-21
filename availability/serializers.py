from rest_framework import serializers

from availability.models import AvailabilitySlot


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ("id", "start_datetime", "end_datetime", "mode", "is_booked", "created_at", "updated_at")
        read_only_fields = ("id", "is_booked", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        tutor = getattr(request, "user", None)
        start_datetime = attrs.get("start_datetime")
        end_datetime = attrs.get("end_datetime")

        if start_datetime and end_datetime and start_datetime >= end_datetime:
            raise serializers.ValidationError({"end_datetime": "End time must be after start time."})

        if tutor and tutor.is_authenticated:
            queryset = AvailabilitySlot.objects.filter(tutor=tutor)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if start_datetime and end_datetime and queryset.filter(start_datetime__lt=end_datetime, end_datetime__gt=start_datetime).exists():
                raise serializers.ValidationError("This availability slot overlaps with an existing slot.")

        return attrs
