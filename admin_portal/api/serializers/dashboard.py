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


class AdminPeakReservationHourSerializer(serializers.Serializer):
    hour = serializers.IntegerField()
    reservation_count = serializers.IntegerField()


class AdminReservationSlotPopularitySerializer(serializers.Serializer):
    hour = serializers.IntegerField()
    minute = serializers.IntegerField()
    reservation_count = serializers.IntegerField()


class AdminTrendingFoodItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    title = serializers.CharField()
    selection_count = serializers.IntegerField()
