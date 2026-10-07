from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from reservations.models import Reservation
from reservations.selectors.menu import (
    get_available_menu_items_by_ids,
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
from reservations.services.session_service import (
    get_or_create_customer,
)
from reservations.services.slot_service import (
    get_bookable_slot,
    release_seats,
    reserve_seats,
)
from reservations.tasks import send_reservation_otp_email_task
from reservations.utils.otp import verify_otp


class ReservationServiceError(Exception):
    """Base exception for reservation business-rule violations."""


class InvalidMenuSelectionError(ReservationServiceError):
    """Raised when selected menu items are unavailable or invalid."""


class ReservationStateError(ReservationServiceError):
    """Raised when an operation is not allowed for the current status."""


class DuplicateReservationError(ReservationServiceError):
    """Raised when a customer already has an active reservation for the same slot."""


def create_pending_reservation(
    browser_session,
    *,
    full_name,
    email,
    phone,
    slot_id,
    guest_count,
    selected_menu_item_ids=None,
    customer_note="",
):
    """Create a pending reservation, reserve its seats, and issue an OTP.

    The OTP is sent to the customer's email only after the database
    transaction successfully commits.

    Returns:
        Reservation

    """
    selected_menu_item_ids = selected_menu_item_ids or []

    # ---------------------------------------------------------
    # Validate duplicate menu selections
    # ---------------------------------------------------------

    if len(selected_menu_item_ids) != len(set(selected_menu_item_ids)):
        raise InvalidMenuSelectionError("A menu item cannot be selected more than once.")

    with transaction.atomic():
        # -----------------------------------------------------
        # Customer
        # -----------------------------------------------------

        customer = get_or_create_customer(
            browser_session,
            full_name=full_name,
            email=email,
            phone=phone,
        )

        # -----------------------------------------------------
        # Menu
        # -----------------------------------------------------

        menu_items = list(get_available_menu_items_by_ids(selected_menu_item_ids))

        if len(menu_items) != len(selected_menu_item_ids):
            raise InvalidMenuSelectionError("One or more selected menu items are unavailable.")

        # -----------------------------------------------------
        # Slot
        # -----------------------------------------------------

        try:
            slot = get_bookable_slot(slot_id)

        except ValueError as exc:
            raise ReservationServiceError(str(exc)) from exc

        # -----------------------------------------------------
        # Special menu eligibility
        # -----------------------------------------------------

        now = timezone.now()

        special_menu_eligible = slot.starts_at >= now + timedelta(hours=24)

        if not special_menu_eligible and any(item.is_special for item in menu_items):
            raise InvalidMenuSelectionError("Special menu items require a reservation at least 24 hours in advance.")

        # -----------------------------------------------------
        # Reserve seats
        # -----------------------------------------------------

        reserve_seats(
            slot.id,
            guest_count,
        )

        # -----------------------------------------------------
        # Create reservation
        # -----------------------------------------------------

        reservation = Reservation.objects.create(
            customer=customer,
            slot=slot,
            guest_count=guest_count,
            status=(Reservation.Status.PENDING_VERIFICATION),
            special_menu_eligible=(special_menu_eligible),
            selected_menu_items=[item.id for item in menu_items],
            customer_note=customer_note,
            expires_at=(now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)),
        )

        # -----------------------------------------------------
        # OTP
        # -----------------------------------------------------

        otp_record, raw_otp = issue_otp(reservation.id)

        # Send email only after transaction commits.
        transaction.on_commit(
            lambda: send_reservation_otp_email(
                recipient_email=customer.email,
                customer_name=customer.full_name,
                otp=raw_otp,
                reservation_reference=(reservation.reference_code),
                expires_at=otp_record.expires_at,
            )
        )

        return reservation


def confirm_reservation(
    reservation_id,
    submitted_otp,
):
    """Verify the reservation OTP and confirm the reservation as one atomic state transition."""
    error = None
    confirmed_reservation = None

    with transaction.atomic():
        reservation = (
            Reservation.objects.select_for_update()
            .select_related(
                "slot",
                "customer",
            )
            .get(id=reservation_id)
        )

        now = timezone.now()

        # -----------------------------------------------------
        # Reservation validation
        # -----------------------------------------------------

        if reservation.status != Reservation.Status.PENDING_VERIFICATION:
            error = ReservationStateError("This reservation is no longer pending verification.")

        elif reservation.expires_at and reservation.expires_at <= now:
            error = ReservationStateError("This reservation has expired.")

        else:
            # -------------------------------------------------
            # Lock active OTP
            # -------------------------------------------------

            otp_record = (
                reservation.otp_attempts_history.select_for_update().filter(is_active=True).order_by("-sent_at").first()
            )

            if otp_record is None:
                error = OTPNotAvailableError("No active OTP exists for this reservation.")

            elif otp_record.expires_at <= now:
                otp_record.is_active = False

                otp_record.save(update_fields=["is_active"])

                error = OTPExpiredError("The OTP has expired.")

            elif otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp_record.is_active = False

                otp_record.save(update_fields=["is_active"])

                error = OTPRateLimitError("The maximum number of OTP attempts has been reached.")

            else:
                # -------------------------------------------------
                # Count attempt
                # -------------------------------------------------

                otp_record.attempts += 1

                # -------------------------------------------------
                # Verify OTP
                # -------------------------------------------------

                if not verify_otp(
                    submitted_otp,
                    otp_record.otp_hash,
                ):
                    update_fields = ["attempts"]

                    if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
                        otp_record.is_active = False

                        update_fields.append("is_active")

                    otp_record.save(update_fields=update_fields)

                    if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
                        error = OTPRateLimitError("The maximum number of OTP attempts has been reached.")

                    else:
                        error = OTPInvalidError("The OTP is incorrect.")

                else:
                    # -------------------------------------------------
                    # OTP correct
                    # -------------------------------------------------

                    otp_record.verified_at = now
                    otp_record.is_active = False

                    otp_record.save(
                        update_fields=[
                            "attempts",
                            "verified_at",
                            "is_active",
                        ]
                    )

                    # -------------------------------------------------
                    # Confirm reservation
                    # -------------------------------------------------

                    reservation.status = Reservation.Status.CONFIRMED

                    reservation.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                    confirmed_reservation = reservation

    # ---------------------------------------------------------
    # Transaction committed
    # ---------------------------------------------------------

    if error is not None:
        raise error

    return confirmed_reservation


def cancel_reservation(reservation):
    """Cancel a pending or confirmed reservation and release its seats exactly once."""
    with transaction.atomic():
        locked_reservation = Reservation.objects.select_for_update().get(id=reservation.id)

        if locked_reservation.status not in (
            Reservation.Status.PENDING_VERIFICATION,
            Reservation.Status.CONFIRMED,
        ):
            raise ReservationStateError("Only pending or confirmed reservations can be cancelled.")

        release_seats(
            locked_reservation.slot_id,
            locked_reservation.guest_count,
        )

        locked_reservation.status = Reservation.Status.CANCELLED

        locked_reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # Invalidate outstanding OTPs.
        (locked_reservation.otp_attempts_history.filter(is_active=True).update(is_active=False))

        return locked_reservation


def expire_pending_reservation(
    reservation_id,
):
    """Expire a pending reservation after its verification deadline.

    Returns the updated reservation, or None if it was not eligible for expiration.
    """
    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(id=reservation_id)

        now = timezone.now()

        if reservation.status != Reservation.Status.PENDING_VERIFICATION:
            return None

        if not reservation.expires_at or reservation.expires_at > now:
            return None

        release_seats(
            reservation.slot_id,
            reservation.guest_count,
        )

        reservation.status = Reservation.Status.EXPIRED

        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        (reservation.otp_attempts_history.filter(is_active=True).update(is_active=False))

        return reservation


@transaction.atomic
def create_draft_reservation(
    *,
    browser_session,
    full_name,
    email,
    phone,
    slot_id,
    guest_count,
    customer_note="",
):
    customer = get_or_create_customer(
        browser_session=browser_session,
        full_name=full_name,
        email=email,
        phone=phone,
    )

    slot = get_bookable_slot(slot_id)

    # ---------------------------------------------------------
    # Prevent duplicate reservation for the same time slot
    # ---------------------------------------------------------

    existing_reservation = Reservation.objects.filter(
        customer=customer,
        slot=slot,
        status__in=[
            Reservation.Status.PENDING_VERIFICATION,
            Reservation.Status.CONFIRMED,
        ],
    ).first()

    if existing_reservation:
        raise DuplicateReservationError("You already have a reservation for this date and time slot.")

    now = timezone.now()

    special_menu_eligible = (slot.starts_at - now).total_seconds() >= 24 * 60 * 60

    expires_at = now + timedelta(minutes=settings.DRAFT_EXPIRY_MINUTES)

    # ---------------------------------------------------------
    # Find an existing active draft
    # ---------------------------------------------------------

    existing_draft = (
        Reservation.objects.select_for_update()
        .filter(
            customer=customer,
            status=Reservation.Status.DRAFT,
        )
        .order_by("-created_at")
        .first()
    )

    if existing_draft and (existing_draft.expires_at is not None and existing_draft.expires_at <= now):
        existing_draft.status = Reservation.Status.EXPIRED

        existing_draft.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )
        existing_draft = None

    # ---------------------------------------------------------
    # Update existing draft
    # ---------------------------------------------------------

    if existing_draft:
        existing_draft.slot = slot
        existing_draft.guest_count = guest_count
        existing_draft.special_menu_eligible = special_menu_eligible
        existing_draft.customer_note = customer_note
        existing_draft.expires_at = expires_at

        existing_draft.save(
            update_fields=[
                "slot",
                "guest_count",
                "special_menu_eligible",
                "customer_note",
                "expires_at",
                "updated_at",
            ]
        )

        return existing_draft

    # ---------------------------------------------------------
    # Create new draft
    # ---------------------------------------------------------

    return Reservation.objects.create(
        customer=customer,
        slot=slot,
        guest_count=guest_count,
        status=Reservation.Status.DRAFT,
        special_menu_eligible=special_menu_eligible,
        selected_menu_items=[],
        customer_note=customer_note,
        expires_at=expires_at,
    )


@transaction.atomic
def update_draft_menu(
    *,
    browser_session,
    selected_menu_item_ids,
):
    """Update the selected menu items of the active draft.

    The draft must belong to the supplied browser session.
    Menu item IDs are validated against currently available
    menu items.
    """
    reservation = (
        Reservation.objects.select_for_update()
        .select_related(
            "customer",
            "slot",
        )
        .filter(
            customer__browser_session=browser_session,
            status=Reservation.Status.DRAFT,
        )
        .order_by("-created_at")
        .first()
    )

    if reservation is None:
        raise ReservationServiceError("No active draft reservation exists.")

    now = timezone.now()

    if reservation.expires_at is not None and reservation.expires_at <= now:
        reservation.status = Reservation.Status.EXPIRED

        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise ReservationStateError("The draft reservation has expired.")

    menu_items = list(get_available_menu_items_by_ids(selected_menu_item_ids))

    if len(menu_items) != len(selected_menu_item_ids):
        raise InvalidMenuSelectionError("One or more selected menu items are unavailable.")

    if not reservation.special_menu_eligible and any(item.is_special for item in menu_items):
        raise InvalidMenuSelectionError("Special menu items require a reservation at least 24 hours in advance.")

    reservation.selected_menu_items = [item.id for item in menu_items]

    reservation.save(
        update_fields=[
            "selected_menu_items",
            "updated_at",
        ]
    )

    return reservation


@transaction.atomic
def finalize_draft_reservation(
    *,
    browser_session,
):
    """Finalize the current DRAFT reservation.

    DRAFT
        -> PENDING_VERIFICATION

    During finalization the backend:
    - locks the draft
    - validates that it has not expired
    - validates the selected menu items again
    - recalculates special-menu eligibility
    - validates the slot
    - reserves seats
    - changes the reservation status
    - issues an OTP
    - schedules the OTP email after commit
    """
    reservation = (
        Reservation.objects.select_for_update()
        .select_related(
            "customer",
            "slot",
        )
        .filter(
            customer__browser_session=browser_session,
            status=Reservation.Status.DRAFT,
        )
        .order_by("-created_at")
        .first()
    )

    if reservation is None:
        raise ReservationServiceError("No active draft reservation exists.")

    now = timezone.now()

    # ---------------------------------------------------------
    # 1. Validate draft expiration
    # ---------------------------------------------------------

    if reservation.expires_at is not None and reservation.expires_at <= now:
        reservation.status = Reservation.Status.EXPIRED

        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise ReservationStateError("The draft reservation has expired.")

    # ---------------------------------------------------------
    # 2. Validate selected menu items again
    # ---------------------------------------------------------

    selected_menu_item_ids = reservation.selected_menu_items or []

    if len(selected_menu_item_ids) != len(set(selected_menu_item_ids)):
        raise InvalidMenuSelectionError("A menu item cannot be selected more than once.")

    menu_items = list(get_available_menu_items_by_ids(selected_menu_item_ids))

    if len(menu_items) != len(selected_menu_item_ids):
        raise InvalidMenuSelectionError("One or more selected menu items are unavailable.")

    # ---------------------------------------------------------
    # 3. Validate slot again
    # ---------------------------------------------------------

    slot = get_bookable_slot(reservation.slot_id)
    if slot.starts_at <= now:
        raise ReservationStateError("The selected time slot is no longer available.")
    # ---------------------------------------------------------
    # 3. Prevent duplicate reservation for the same time slot
    # ---------------------------------------------------------

    existing_reservation = (
        Reservation.objects.filter(
            customer=reservation.customer,
            slot=slot,
            status__in=[
                Reservation.Status.PENDING_VERIFICATION,
                Reservation.Status.CONFIRMED,
            ],
        )
        .exclude(id=reservation.id)
        .first()
    )

    if existing_reservation:
        raise DuplicateReservationError("You already have a reservation for this date and time slot.")

    # ---------------------------------------------------------
    # 4. Recalculate special-menu eligibility
    # ---------------------------------------------------------

    special_menu_eligible = (slot.starts_at - now).total_seconds() >= 24 * 60 * 60

    if not special_menu_eligible and any(item.is_special for item in menu_items):
        raise InvalidMenuSelectionError("Special menu items require a reservation at least 24 hours in advance.")

    # ---------------------------------------------------------
    # 5. Reserve seats
    # ---------------------------------------------------------

    reserve_seats(
        slot.id,
        reservation.guest_count,
    )

    # ---------------------------------------------------------
    # 6. Change reservation state
    # ---------------------------------------------------------

    reservation.slot = slot
    reservation.special_menu_eligible = special_menu_eligible
    reservation.status = Reservation.Status.PENDING_VERIFICATION

    reservation.expires_at = now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    reservation.save(
        update_fields=[
            "slot",
            "special_menu_eligible",
            "status",
            "expires_at",
            "updated_at",
        ]
    )

    # ---------------------------------------------------------
    # 7. Issue OTP
    # ---------------------------------------------------------

    otp_record, raw_otp = issue_otp(reservation.id)

    # ---------------------------------------------------------
    # 8. Send email only after transaction commits
    # The Celery worker performs the actual SMTP operation asynchronously.
    # ---------------------------------------------------------
    transaction.on_commit(
        lambda: send_reservation_otp_email_task.delay(
            recipient_email=reservation.customer.email,
            customer_name=reservation.customer.full_name,
            otp=raw_otp,
            reservation_reference=reservation.reference_code,
            expires_at=otp_record.expires_at,
        )
    )

    return reservation
