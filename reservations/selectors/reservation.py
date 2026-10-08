from django.db.models import Q
from django.utils import timezone

from reservations.models import Reservation


def get_reservation_by_reference(reference_code, browser_session):
    """Retrieve a reservation only if it belongs to the supplied browser session.

    Returns None if the reference doesn't exist or doesn't belong to this browser session.
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
    """Return reservations belonging to a particular customer."""
    return Reservation.objects.select_related("slot", "customer").filter(customer=customer).order_by("-created_at")


def get_pending_reservations():
    """Return reservations that are awaiting email verification.

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


def get_admin_reservations(
    search=None,
    date_from=None,
    date_to=None,
    status=None,
):
    queryset = Reservation.objects.select_related(
        "customer",
        "slot",
    ).order_by("-created_at")

    if search:
        queryset = queryset.filter(
            Q(customer__full_name__icontains=search)
            | Q(customer__email__icontains=search)
            | Q(customer__phone__icontains=search)
            | Q(reference_code__icontains=search)
        )

    if date_from:
        queryset = queryset.filter(slot__starts_at__date__gte=date_from)

    if date_to:
        queryset = queryset.filter(slot__starts_at__date__lte=date_to)

    if status:
        queryset = queryset.filter(status=status)

    return queryset

def get_admin_reservation_by_reference(reference_code):
    return (
        Reservation.objects
        .select_related(
            "customer",
            "slot",
        )
        .filter(
            reference_code=reference_code,
        )
        .first()
    )