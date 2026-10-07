from rest_framework import serializers


class AdminDashboardReservationSerializer(serializers.Serializer):
    reference_code = serializers.UUIDField()
    customer_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    starts_at = serializers.DateTimeField()
    guest_count = serializers.IntegerField()
    status = serializers.CharField()


class AdminDashboardSummarySerializer(serializers.Serializer):
    today_reservations = serializers.IntegerField()
    upcoming_reservations = serializers.IntegerField()
    guests_expected_this_week = serializers.IntegerField()

    status_breakdown = serializers.DictField(
        child=serializers.IntegerField(),
    )

    today_reservation_list = AdminDashboardReservationSerializer(
        many=True,
    )


class AdminReservationTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    reservation_count = serializers.IntegerField()
