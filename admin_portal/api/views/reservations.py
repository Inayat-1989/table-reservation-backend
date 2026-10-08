from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.api.pagination import (
    AdminReservationPagination,
)
from admin_portal.api.permissions import IsAuthenticatedAdmin
from reservations.api.serializers.reservation import (
    ReservationResponseSerializer,
)
from reservations.selectors.reservation import (
    get_admin_reservation_by_reference,
    get_admin_reservations,
)


class AdminReservationDetailView(APIView):
    permission_classes = [IsAuthenticatedAdmin]

    def get(self, request, reference_code):
        reservation = get_admin_reservation_by_reference(reference_code)

        if reservation is None:
            return Response(
                {"detail": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReservationResponseSerializer(reservation)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AdminReservationListView(APIView):
    permission_classes = [IsAuthenticatedAdmin]
    pagination_class = AdminReservationPagination

    def get(self, request):
        search = request.query_params.get("search")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        reservation_status = request.query_params.get("status")

        reservations = get_admin_reservations(
            search=search,
            date_from=date_from,
            date_to=date_to,
            status=reservation_status,
        )

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            reservations,
            request,
            view=self,
        )

        serializer = ReservationResponseSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)
