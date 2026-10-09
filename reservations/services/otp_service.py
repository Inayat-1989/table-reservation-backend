from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from reservations.models import Reservation, ReservationOTP
from reservations.utils.otp import generate_otp, hash_otp, verify_otp


class OTPServiceError(Exception):
    """Base exception for OTP service errors."""


class OTPRateLimitError(OTPServiceError):
    """Raised when an OTP resend or attempt limit has been reached."""


class OTPExpiredError(OTPServiceError):
    """Raised when an OTP or its reservation has expired."""


class OTPInvalidError(OTPServiceError):
    """Raised when the submitted OTP is incorrect."""


class OTPNotAvailableError(OTPServiceError):
    """Raised when no usable OTP exists for the reservation."""


def issue_otp(reservation_id):
    """Create and store a new OTP for a pending reservation.

    Returns:
        (otp_record, raw_otp)

    The raw OTP is returned only for internal email-delivery code.
    Never include it in an API response.

    """
    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(id=reservation_id)

        now = timezone.now()

        if reservation.status != Reservation.Status.PENDING_VERIFICATION:
            raise OTPServiceError("An OTP can only be issued for a pending reservation.")

        if reservation.expires_at and reservation.expires_at <= now:
            raise OTPExpiredError("This reservation has expired.")

        previous_otps = reservation.otp_attempts_history.order_by("-sent_at")
        latest_otp = previous_otps.first()

        # Enforce resend cooldown using the most recently issued OTP.
        if latest_otp:
            cooldown = timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
            if now < latest_otp.sent_at + cooldown:
                raise OTPRateLimitError("Please wait 1 Min before requesting another OTP.")

        # Limit the number of OTPs issued for this reservation.
        total_sent = reservation.otp_attempts_history.count()

        if total_sent >= settings.OTP_MAX_SENDS:
            raise OTPRateLimitError("The maximum number of OTP requests has been reached.")

        # Invalidate previous active codes before issuing a new one.
        reservation.otp_attempts_history.filter(is_active=True).update(is_active=False)

        raw_otp = generate_otp()
        otp_hash = hash_otp(raw_otp)

        otp_record = ReservationOTP.objects.create(
            reservation=reservation,
            otp_hash=otp_hash,
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
            attempts=0,
            is_active=True,
        )

        return otp_record, raw_otp


def verify_reservation_otp(reservation_id, submitted_otp):
    """Verify an OTP and persist attempt counters even when verification fails.

    Returns the ReservationOTP record on success.
    """
    error = None
    verified_record = None

    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(id=reservation_id)

        now = timezone.now()

        if reservation.status != Reservation.Status.PENDING_VERIFICATION:
            error = OTPServiceError("This reservation is not awaiting OTP verification.")

        elif reservation.expires_at and reservation.expires_at <= now:
            error = OTPExpiredError("This reservation has expired.")

        else:
            otp_record = (
                reservation.otp_attempts_history.select_for_update().filter(is_active=True).order_by("-sent_at").first()
            )

            if otp_record is None:
                error = OTPNotAvailableError("No active OTP exists. Request a new code if permitted.")

            elif otp_record.expires_at <= now:
                otp_record.is_active = False
                otp_record.save(update_fields=["is_active"])
                error = OTPExpiredError("The OTP has expired.")

            elif otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp_record.is_active = False
                otp_record.save(update_fields=["is_active"])
                error = OTPRateLimitError("The maximum number of verification attempts has been reached.")

            else:
                otp_record.attempts += 1

                if verify_otp(submitted_otp, otp_record.otp_hash):
                    otp_record.verified_at = now
                    otp_record.is_active = False
                    verified_record = otp_record
                    otp_record.save(
                        update_fields=[
                            "attempts",
                            "verified_at",
                            "is_active",
                        ]
                    )
                else:
                    update_fields = ["attempts"]

                    if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
                        otp_record.is_active = False
                        update_fields.append("is_active")

                    otp_record.save(update_fields=update_fields)
                    error = OTPInvalidError("The OTP is incorrect.")

    # Raise only after the transaction has committed its changes.
    if error is not None:
        raise error

    return verified_record
