from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.api.permissions import IsAuthenticatedAdmin
from admin_portal.api.serializers.dashboard import (
    AdminDashboardSummarySerializer,
)
from admin_portal.services.dashboard import (
    get_dashboard_summary,
)

from admin_portal.api.serializers.dashboard import (
    AdminReservationTrendSerializer,
)

from admin_portal.services.dashboard import (
    get_reservation_trends,
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