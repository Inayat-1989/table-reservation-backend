from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.api.permissions import IsAuthenticatedAdmin
from admin_portal.api.serializers.dashboard import (
    AdminDashboardSummarySerializer,
    AdminPeakReservationHourSerializer,
    AdminReservationSlotPopularitySerializer,
    AdminReservationTrendSerializer,
    AdminTrendingFoodItemSerializer,
)
from admin_portal.services.dashboard import (
    get_dashboard_summary,
    get_peak_reservation_hours,
    get_reservation_slot_popularity,
    get_reservation_trends,
    get_trending_food_items,
)


class AdminDashboardView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
    ]

    def get(self, request):
        dashboard_data = get_dashboard_summary()

        serializer = AdminDashboardSummarySerializer(
            dashboard_data,
        )

        return Response(
            serializer.data,
        )


class AdminReservationTrendView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
    ]

    def get(self, request):
        trends = get_reservation_trends()

        serializer = AdminReservationTrendSerializer(
            trends,
            many=True,
        )

        return Response(
            serializer.data,
        )


class AdminPeakReservationHoursView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
    ]

    def get(self, request):
        peak_hours = get_peak_reservation_hours()

        serializer = AdminPeakReservationHourSerializer(
            peak_hours,
            many=True,
        )

        return Response(
            serializer.data,
        )


class AdminReservationSlotPopularityView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
    ]

    def get(self, request):
        slot_popularity = get_reservation_slot_popularity()

        serializer = AdminReservationSlotPopularitySerializer(
            slot_popularity,
            many=True,
        )

        return Response(
            serializer.data,
        )


class AdminTrendingFoodItemsView(APIView):
    permission_classes = [IsAuthenticatedAdmin]

    def get(self, request):
        trending_items = get_trending_food_items()

        serializer = AdminTrendingFoodItemSerializer(
            trending_items,
            many=True,
        )

        return Response(serializer.data)
