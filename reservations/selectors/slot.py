from datetime import datetime, time, timedelta

from django.utils import timezone

from reservations.models import TimeSlot


def get_slots_for_date(selected_date):
    """
    Return all TimeSlot records belonging to the selected date.

    Business rules such as today's cutoff are handled by
    the service layer.
    """

    current_timezone = timezone.get_current_timezone()

    start_of_day = timezone.make_aware(
        datetime.combine(
            selected_date,
            time.min,
        ),
        current_timezone,
    )

    start_of_next_day = start_of_day + timedelta(days=1)

    return TimeSlot.objects.filter(
        starts_at__gte=start_of_day,
        starts_at__lt=start_of_next_day,
    ).order_by("starts_at")


def get_slot_by_id(slot_id):
    """
    Return a slot by primary key.
    """

    return TimeSlot.objects.filter(id=slot_id).first()


def get_slot_by_start_time(starts_at):
    """
    Return a slot by exact datetime.
    """

    return TimeSlot.objects.filter(starts_at=starts_at).first()
