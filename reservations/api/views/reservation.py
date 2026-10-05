from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.api.serializers.reservation import (
    ReservationCreateSerializer,
    ReservationDraftCreateSerializer,
    ReservationDraftMenuUpdateSerializer,
    ReservationResponseSerializer,
)
from reservations.selectors.reservation import (
    get_active_draft_reservation,
    get_customer_reservations,
    get_reservation_by_reference,
)
from reservations.services.reservation_service import (
    DuplicateReservationError,
    InvalidMenuSelectionError,
    ReservationServiceError,
    ReservationStateError,
    cancel_reservation,
    create_draft_reservation,
    create_pending_reservation,
    finalize_draft_reservation,
    update_draft_menu,
)
from reservations.services.session_service import (
    get_browser_session,
    get_or_create_browser_session,
)
from reservations.services.slot_service import SlotCapacityError
from reservations.utils.cookies import (
    get_browser_session_token,
    set_browser_session_cookie,
)


class ReservationCreateView(APIView):
    """
    Create a pending reservation.

    Successful creation reserves the requested seats and generates
    an OTP. The OTP itself is sent to the customer's email and is
    never returned to React.
    """

    def post(self, request):

        serializer = ReservationCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        raw_token = get_browser_session_token(request)
        browser_session, new_token = get_or_create_browser_session(raw_token)

        data = serializer.validated_data

        try:
            reservation = create_pending_reservation(
                browser_session,
                full_name=data["full_name"],
                email=data["email"],
                phone=data["phone"],
                slot_id=data["slot_id"],
                guest_count=data["guest_count"],
                selected_menu_item_ids=data.get(
                    "selected_menu_item_ids",
                    [],
                ),
                customer_note=data.get(
                    "customer_note",
                    "",
                ),
            )

        except SlotCapacityError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": ("SLOT_CAPACITY_EXCEEDED"),
                },
                status=status.HTTP_409_CONFLICT,
            )

        except ReservationServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": ("RESERVATION_ERROR"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = ReservationResponseSerializer(reservation).data

        response = Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response


class ReservationListView(APIView):
    """
    Return reservations belonging to the current browser session.
    """

    def get(self, request):
        raw_token = get_browser_session_token(request)
        browser_session, new_token = get_or_create_browser_session(raw_token)

        customer = getattr(
            browser_session,
            "customer",
            None,
        )

        if customer is None:
            reservations = []
        else:
            reservations = get_customer_reservations(customer)

        serializer = ReservationResponseSerializer(
            reservations,
            many=True,
        )

        response = Response(serializer.data)

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response


class ReservationDetailView(APIView):
    """
    Retrieve one reservation belonging to the current browser session.
    """

    def get(
        self,
        request,
        reference_code,
    ):
        raw_token = get_browser_session_token(request)
        browser_session, new_token = get_or_create_browser_session(raw_token)

        reservation = get_reservation_by_reference(
            reference_code,
            browser_session,
        )

        if reservation is None:
            return Response(
                {"detail": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReservationResponseSerializer(reservation)

        response = Response(serializer.data)

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response


class ReservationCancelView(APIView):
    """
    Cancel a reservation belonging to the current browser session.
    """

    def post(
        self,
        request,
        reference_code,
    ):
        raw_token = get_browser_session_token(request)
        browser_session, new_token = get_or_create_browser_session(raw_token)

        reservation = get_reservation_by_reference(
            reference_code,
            browser_session,
        )

        if reservation is None:
            return Response(
                {"detail": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            reservation = cancel_reservation(reservation)

        except ReservationServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "CANCELLATION_ERROR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationResponseSerializer(reservation)

        response = Response(serializer.data)

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response


class ReservationDraftCreateView(APIView):
    def post(self, request):
        serializer = ReservationDraftCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        raw_token = get_browser_session_token(request)

        browser_session, new_token = get_or_create_browser_session(raw_token)

        data = serializer.validated_data

        try:
            reservation = create_draft_reservation(
                browser_session=browser_session,
                full_name=data["full_name"],
                email=data["email"],
                phone=data["phone"],
                slot_id=data["slot_id"],
                guest_count=data["guest_count"],
                customer_note=data.get(
                    "customer_note",
                    "",
                ),
            )

        except SlotCapacityError as error:
            return Response(
                {
                    "detail": str(error),
                    "code": "SLOT_CAPACITY_EXCEEDED",
                },
                status=status.HTTP_409_CONFLICT,
            )

        except ReservationServiceError as error:
            return Response(
                {
                    "detail": str(error),
                    "code": "RESERVATION_ERROR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except DuplicateReservationError as error:
            return Response(
                {
                    "detail": str(error),
                    "code": "DUPLICATE_RESERVATION",
                },
                status=status.HTTP_409_CONFLICT,
            )

        response_serializer = ReservationResponseSerializer(reservation)

        response = Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

        if new_token:
            set_browser_session_cookie(
                response,
                new_token,
            )

        return response


class ActiveReservationView(APIView):
    def get(self, request):
        raw_token = get_browser_session_token(request)

        browser_session = get_browser_session(raw_token)

        if not browser_session:
            return Response(
                {
                    "reservation": None,
                },
                status=status.HTTP_200_OK,
            )

        reservation = get_active_draft_reservation(browser_session)

        if not reservation:
            return Response(
                {
                    "reservation": None,
                },
                status=status.HTTP_200_OK,
            )

        serializer = ReservationResponseSerializer(reservation)

        return Response(
            {
                "reservation": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ReservationDraftMenuUpdateView(APIView):
    """
    Update the selected menu items of the current draft reservation.
    """

    def patch(self, request):
        serializer = ReservationDraftMenuUpdateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        raw_token = get_browser_session_token(request)

        browser_session = get_browser_session(raw_token)

        if not browser_session:
            return Response(
                {
                    "detail": "No active browser session exists.",
                    "code": "SESSION_NOT_FOUND",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            reservation = update_draft_menu(
                browser_session=browser_session,
                selected_menu_item_ids=serializer.validated_data[
                    "selected_menu_item_ids"
                ],
            )

        except InvalidMenuSelectionError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "INVALID_MENU_SELECTION",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ReservationStateError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "RESERVATION_STATE_ERROR",
                },
                status=status.HTTP_409_CONFLICT,
            )

        except ReservationServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "RESERVATION_ERROR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(
            ReservationResponseSerializer(reservation).data,
            status=status.HTTP_200_OK,
        )

        return response


class ReservationDraftFinalizeView(APIView):
    """
    Finalize the current draft reservation.

    DRAFT -> PENDING_VERIFICATION

    This also reserves seats and sends an OTP.
    """

    def post(self, request):
        raw_token = get_browser_session_token(request)

        browser_session = get_browser_session(raw_token)

        if not browser_session:
            return Response(
                {
                    "detail": "No active browser session exists.",
                    "code": "SESSION_NOT_FOUND",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            reservation = finalize_draft_reservation(
                browser_session=browser_session,
            )

        except SlotCapacityError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "SLOT_CAPACITY_EXCEEDED",
                },
                status=status.HTTP_409_CONFLICT,
            )
        except DuplicateReservationError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "DUPLICATE_RESERVATION",
                },
                status=status.HTTP_409_CONFLICT,
            )

        except InvalidMenuSelectionError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "INVALID_MENU_SELECTION",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ReservationStateError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "RESERVATION_STATE_ERROR",
                },
                status=status.HTTP_409_CONFLICT,
            )

        except ReservationServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "RESERVATION_ERROR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationResponseSerializer(reservation)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
