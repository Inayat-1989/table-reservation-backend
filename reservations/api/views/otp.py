from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.api.serializers.otp import (
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from reservations.api.serializers.reservation import (
    ReservationResponseSerializer,
)
from reservations.selectors.reservation import (
    get_reservation_by_reference,
)
from reservations.services.email_service import (
    send_reservation_otp_email,
)
from reservations.services.otp_service import (
    OTPExpiredError,
    OTPInvalidError,
    OTPNotAvailableError,
    OTPRateLimitError,
    issue_otp,
)
from reservations.services.reservation_service import (
    ReservationStateError,
    confirm_reservation,
)
from reservations.services.session_service import (
    get_or_create_browser_session,
)
from reservations.utils.cookies import (
    BROWSER_SESSION_COOKIE,
    set_browser_session_cookie,
)


class OTPResendView(APIView):
    """
    Request a new OTP for a browser-owned pending reservation.
    """

    def post(self, request):

        serializer = OTPRequestSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        browser_session, new_token = get_or_create_browser_session(
            request.COOKIES.get(BROWSER_SESSION_COOKIE)
        )

        reservation = get_reservation_by_reference(
            serializer.validated_data["reference_code"],
            browser_session,
        )

        if reservation is None:
            return Response(
                {
                    "detail": "Reservation not found.",
                    "code": "RESERVATION_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            otp_record, raw_otp = issue_otp(reservation.id)

            send_reservation_otp_email(
                recipient_email=reservation.customer.email,
                customer_name=reservation.customer.full_name,
                otp=raw_otp,
                reservation_reference=reservation.reference_code,
                expires_at=otp_record.expires_at,
            )

        except OTPRateLimitError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_RATE_LIMITED",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except OTPExpiredError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_EXPIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPInvalidError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_INVALID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(
            {"detail": "A new verification code has been sent."},
            status=status.HTTP_200_OK,
        )

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response


class OTPVerifyView(APIView):
    """
    Verify an OTP and confirm the browser-owned reservation.
    """

    def post(self, request):

        # ---------------------------------------------------------
        # 1. Validate request body
        # ---------------------------------------------------------

        serializer = OTPVerifySerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # ---------------------------------------------------------
        # 2. Get browser session
        # ---------------------------------------------------------

        browser_session, new_token = get_or_create_browser_session(
            request.COOKIES.get(BROWSER_SESSION_COOKIE)
        )

        # ---------------------------------------------------------
        # 3. Find reservation owned by this browser
        # ---------------------------------------------------------

        reservation = get_reservation_by_reference(
            serializer.validated_data["reference_code"],
            browser_session,
        )

        if reservation is None:
            return Response(
                {
                    "detail": "Reservation not found.",
                    "code": "RESERVATION_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------
        # 4. Verify OTP + confirm reservation atomically
        # ---------------------------------------------------------

        try:
            reservation = confirm_reservation(
                reservation.id,
                serializer.validated_data["otp"],
            )

        except OTPInvalidError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_INVALID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPExpiredError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_EXPIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPRateLimitError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_MAX_ATTEMPTS",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except OTPNotAvailableError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "OTP_NOT_AVAILABLE",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ReservationStateError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "RESERVATION_STATE_ERROR",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------------------
        # 5. Success
        # ---------------------------------------------------------
        serializer = ReservationResponseSerializer(reservation)

        response = Response(
            {
                "detail": "Reservation confirmed successfully.",
                **serializer.data,
            },
            status=status.HTTP_200_OK,
        )

        # ---------------------------------------------------------
        # 6. Set browser cookie if a new session was created
        # ---------------------------------------------------------

        set_browser_session_cookie(
            response,
            new_token,
        )

        return response
