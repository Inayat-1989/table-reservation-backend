from rest_framework import serializers

from reservations.models import Reservation


class AdminReservationFilterSerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    date_from = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
    )

    date_to = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
    )

    status = serializers.ChoiceField(
        required=False,
        choices=Reservation.Status.choices,
    )

    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({"date_to": ("End date must be greater than or equal to start date.")})

        return attrs
