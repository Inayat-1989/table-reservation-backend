from rest_framework import serializers

from reservations.models import TimeSlot


class TimeSlotSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True)

    booked_seats = serializers.IntegerField(read_only=True)

    remaining_seats = serializers.IntegerField(read_only=True)

    is_full = serializers.BooleanField(read_only=True)

    class Meta:
        model = TimeSlot

        fields = [
            "id",
            "starts_at",
            "capacity",
            "booked_seats",
            "remaining_seats",
            "is_full",
        ]

        read_only_fields = fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        capacity = self.context["capacity"]

        booked_seats = instance.booked_seats

        remaining_seats = max(
            0,
            capacity - booked_seats,
        )

        representation["capacity"] = capacity
        representation["booked_seats"] = booked_seats
        representation["remaining_seats"] = remaining_seats
        representation["is_full"] = remaining_seats <= 0

        return representation
