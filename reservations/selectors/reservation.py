from django.utils import timezone

from reservations.models import Reservation


def get_reservation_by_reference(reference_code, browser_session):
    """
    Retrieve a reservation only if it belongs to the supplied
    browser session.

    Returns None if the reference doesn't exist or doesn't
    belong to this browser session.
    """
    return (
        Reservation.objects.select_related(
            "customer",
            "customer__browser_session",
            "slot",
        )
        .filter(
            reference_code=reference_code,
            customer__browser_session=browser_session,
        )
        .first()
    )


def get_customer_reservations(customer):
    """
    Return reservations belonging to a particular customer.
    """
    return (
        Reservation.objects.select_related("slot", "customer")
        .filter(customer=customer)
        .order_by("-created_at")
    )


def get_pending_reservations():
    """
    Return reservations that are awaiting email verification.

    Expiration must still be checked separately; a reservation
    can have pending status while its expiry time has passed.
    """
    return (
        Reservation.objects.select_related("customer", "slot")
        .filter(status=Reservation.Status.PENDING_VERIFICATION)
        .order_by("created_at")
    )


def get_active_draft_reservation(browser_session):
    return (
        Reservation.objects.select_related(
            "customer",
            "slot",
        )
        .filter(
            customer__browser_session=browser_session,
            status=Reservation.Status.DRAFT,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )


from django.db.models import Q


def get_active_reservation(browser_session):
    now = timezone.now()

    return (
        Reservation.objects.select_related(
            "customer",
            "slot",
        )
        .filter(
            customer__browser_session=browser_session,
        )
        .filter(
            Q(
                status=Reservation.Status.DRAFT,
                expires_at__gt=now,
            )
            | Q(
                status=Reservation.Status.PENDING_VERIFICATION,
                expires_at__gt=now,
            )
            | Q(
                status=Reservation.Status.CONFIRMED,
            )
        )
        .order_by("-created_at")
        .first()
    )
