from datetime import datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from reservations.models import Reservation


def get_dashboard_summary():
    now = timezone.now()
    today = timezone.localdate()

    start_of_today = timezone.make_aware(
        datetime.combine(
            today,
            time.min,
        ),
    )

    start_of_tomorrow = start_of_today + timedelta(days=1)

    start_of_week = start_of_today - timedelta(
        days=today.weekday(),
    )

    start_of_next_week = start_of_week + timedelta(days=7)

    confirmed_reservations = Reservation.objects.filter(
        status=Reservation.Status.CONFIRMED,
    )

    today_reservations = confirmed_reservations.filter(
        slot__starts_at__gte=start_of_today,
        slot__starts_at__lt=start_of_tomorrow,
    )

    today_reservation_list = today_reservations.select_related(
        "customer",
        "slot",
    ).order_by(
        "slot__starts_at",
    )

    today_reservations_data = [
        {
            "reference_code": str(reservation.reference_code),
            "customer_name": reservation.customer.full_name,
            "email": reservation.customer.email,
            "phone": reservation.customer.phone,
            "starts_at": reservation.slot.starts_at,
            "guest_count": reservation.guest_count,
            "status": reservation.status,
        }
        for reservation in today_reservation_list
    ]

    upcoming_reservations = confirmed_reservations.filter(
        slot__starts_at__gte=now,
    )

    week_reservations = confirmed_reservations.filter(
        slot__starts_at__gte=start_of_week,
        slot__starts_at__lt=start_of_next_week,
    )

    guests_expected_this_week = sum(reservation.guest_count for reservation in week_reservations)

    reservation_statuses = Reservation.objects.values("status").annotate(count=Count("id")).order_by("status")

    status_breakdown = {item["status"]: item["count"] for item in reservation_statuses}

    return {
        "today_reservations": today_reservations.count(),
        "upcoming_reservations": upcoming_reservations.count(),
        "guests_expected_this_week": guests_expected_this_week,
        "status_breakdown": status_breakdown,
        "today_reservation_list": today_reservations_data,
    }


def get_reservation_trends(days=7):
    today = timezone.localdate()

    start_date = today - timedelta(days=days - 1)

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        ),
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            today + timedelta(days=1),
            time.min,
        ),
    )

    reservations = (
        Reservation.objects.filter(
            status=Reservation.Status.CONFIRMED,
            slot__starts_at__gte=start_datetime,
            slot__starts_at__lt=end_datetime,
        )
        .annotate(
            reservation_date=TruncDate(
                "slot__starts_at",
                tzinfo=timezone.get_current_timezone(),
            ),
        )
        .values("reservation_date")
        .annotate(
            reservation_count=Count("id"),
        )
        .order_by("reservation_date")
    )

    reservation_counts = {item["reservation_date"]: item["reservation_count"] for item in reservations}

    trends = []

    for day_offset in range(days):
        current_date = start_date + timedelta(
            days=day_offset,
        )

        trends.append(
            {
                "date": current_date,
                "reservation_count": reservation_counts.get(
                    current_date,
                    0,
                ),
            }
        )

    return trends
