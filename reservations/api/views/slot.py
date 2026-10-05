from datetime import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.api.serializers.slot import (
    TimeSlotSerializer,
)
from reservations.services.slot_service import (
    get_restaurant_settings,
    get_slots_for_date,
)


class SlotListView(APIView):
    """
    Return restaurant slots for a selected date.

    GET /api/v1/slots/?date=2026-10-05
    """

    def get(self, request):
        date_string = request.query_params.get("date")

        if not date_string:
            return Response(
                {
                    "detail": ("The 'date' query parameter is required."),
                    "code": "DATE_REQUIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            selected_date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return Response(
                {
                    "detail": ("Invalid date format. Use YYYY-MM-DD."),
                    "code": "INVALID_DATE",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        slots = get_slots_for_date(selected_date)

        restaurant_settings = get_restaurant_settings()

        serializer = TimeSlotSerializer(
            slots,
            many=True,
            context={"capacity": (restaurant_settings.capacity_per_slot)},
        )

        return Response(
            {
                "date": date_string,
                "slots": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
