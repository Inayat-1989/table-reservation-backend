from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from reservations.models import RestaurantSettings, TimeSlot
from reservations.selectors.slot import (
    get_slots_for_date as select_slots_for_date,
)


class SlotCapacityError(Exception):
    """Raised when a time slot cannot accommodate the requested guests."""


class TimeSlotError(Exception):
    """Custom Errors can be passed regarding any TimeSlot Errors/Exceptions."""


# ---------------------------------------------------------
# Restaurant settings
# ---------------------------------------------------------


def get_restaurant_settings():
    """Return the single global restaurant settings record.

    Exactly one RestaurantSettings row must exist.
    """
    return RestaurantSettings.objects.get()


# ---------------------------------------------------------
# Slot datetime helpers
# ---------------------------------------------------------


def generate_daily_slot_datetimes(selected_date):
    """Generate all slot datetimes for a given date using the restaurant's configured

    opening time, closing time, and slot interval.

    The closing time is inclusive.

    Example:
        opening_time = 10:00
        closing_time = 11:00
        interval = 30

    Produces:

        10:00
        10:30
        11:00

    """
    if not isinstance(selected_date, date):
        raise TimeSlotError("selected_date must be a date object.")

    restaurant_settings = get_restaurant_settings()

    opening_time = restaurant_settings.opening_time
    closing_time = restaurant_settings.closing_time
    interval_minutes = restaurant_settings.slot_interval_minutes

    if interval_minutes <= 0:
        raise TimeSlotError("slot_interval_minutes must be greater than zero.")

    if opening_time >= closing_time:
        raise TimeSlotError("opening_time must be earlier than closing_time.")

    current_timezone = timezone.get_current_timezone()

    current_datetime = timezone.make_aware(
        datetime.combine(
            selected_date,
            opening_time,
        ),
        current_timezone,
    )

    closing_datetime = timezone.make_aware(
        datetime.combine(
            selected_date,
            closing_time,
        ),
        current_timezone,
    )

    slot_datetimes = []

    while current_datetime <= closing_datetime:
        slot_datetimes.append(current_datetime)

        current_datetime += timedelta(minutes=interval_minutes)

    return slot_datetimes


def get_next_valid_slot_datetime():
    """Return the next valid configured restaurant slot from the current local time.

    Example with 30-minute intervals:

        6:00 PM -> 6:00 PM
        6:01 PM -> 6:30 PM
        6:13 PM -> 6:30 PM
        6:30 PM -> 6:30 PM
        6:31 PM -> 7:00 PM
    """
    restaurant_settings = get_restaurant_settings()

    interval_minutes = restaurant_settings.slot_interval_minutes

    if interval_minutes <= 0:
        raise TimeSlotError("slot_interval_minutes must be greater than zero.")

    current_timezone = timezone.get_current_timezone()

    now = timezone.localtime(
        timezone.now(),
        current_timezone,
    )

    opening_time = restaurant_settings.opening_time
    closing_time = restaurant_settings.closing_time

    today_opening = now.replace(
        hour=opening_time.hour,
        minute=opening_time.minute,
        second=0,
        microsecond=0,
    )

    today_closing = now.replace(
        hour=closing_time.hour,
        minute=closing_time.minute,
        second=0,
        microsecond=0,
    )

    # Before restaurant opening.
    if now < today_opening:
        return today_opening

    # After restaurant closing.
    if now > today_closing:
        return today_closing + timedelta(minutes=interval_minutes)

    elapsed_seconds = (now - today_opening).total_seconds()

    interval_seconds = interval_minutes * 60

    intervals_passed = int(elapsed_seconds // interval_seconds)

    candidate = today_opening + timedelta(seconds=(intervals_passed * interval_seconds))

    # If the current time is between slots,
    # move to the next slot.
    if candidate < now:
        candidate += timedelta(minutes=interval_minutes)

    return candidate


# ---------------------------------------------------------
# Slot creation
# ---------------------------------------------------------


def ensure_daily_slots(selected_date):
    """Ensure that all configured restaurant slots for the selected date exist in the database.

    Existing slots are preserved.

    Missing slots are created.

    Past slots are never deleted.
    """
    slot_datetimes = generate_daily_slot_datetimes(selected_date)

    existing_starts_at = set(
        TimeSlot.objects.filter(starts_at__in=slot_datetimes).values_list(
            "starts_at",
            flat=True,
        )
    )

    slots_to_create = [
        TimeSlot(starts_at=starts_at) for starts_at in slot_datetimes if starts_at not in existing_starts_at
    ]

    if slots_to_create:
        TimeSlot.objects.bulk_create(
            slots_to_create,
            ignore_conflicts=True,
        )


# ---------------------------------------------------------
# Public slot retrieval
# ---------------------------------------------------------


def get_slots_for_date(selected_date):
    """Return the slots that should be displayed for a date.

    Past date:
        No slots.

    Today:
        Only the next valid slot onward.

    Future date:
        All configured slots.

    Full slots are still returned.
    """
    if not isinstance(selected_date, date):
        raise TimeSlotError("selected_date must be a date object.")

    today = timezone.localdate()

    # Past date.
    if selected_date < today:
        return TimeSlot.objects.none()

    # Ensure all configured slots exist.
    ensure_daily_slots(selected_date)

    slots = select_slots_for_date(selected_date)

    # Future date:
    # Return the complete schedule.
    if selected_date > today:
        return slots

    # Today:
    # Return only future/current valid slots.
    next_valid_slot = get_next_valid_slot_datetime()

    return slots.filter(starts_at__gte=next_valid_slot)


# ---------------------------------------------------------
# Individual slot helpers
# ---------------------------------------------------------


def validate_slot_datetime(starts_at):
    """Validate a requested slot datetime against the configured restaurant schedule."""
    if not isinstance(starts_at, datetime):
        raise TimeSlotError("starts_at must be a datetime object.")

    if timezone.is_naive(starts_at):
        raise TimeSlotError("starts_at must be timezone-aware.")

    restaurant_settings = get_restaurant_settings()

    interval_minutes = restaurant_settings.slot_interval_minutes

    opening_time = restaurant_settings.opening_time
    closing_time = restaurant_settings.closing_time

    local_starts_at = timezone.localtime(starts_at)

    requested_time = local_starts_at.time()

    if requested_time < opening_time:
        raise TimeSlotError("The requested time is before the restaurant opening time.")

    if requested_time > closing_time:
        raise TimeSlotError("The requested time is after the restaurant closing time.")

    opening_datetime = local_starts_at.replace(
        hour=opening_time.hour,
        minute=opening_time.minute,
        second=0,
        microsecond=0,
    )

    elapsed_seconds = (local_starts_at - opening_datetime).total_seconds()

    interval_seconds = interval_minutes * 60

    if elapsed_seconds % interval_seconds != 0:
        raise TimeSlotError("The requested time does not match the restaurant's configured slot interval.")


def get_or_create_time_slot(starts_at):
    """Return an existing slot or create one for the requested datetime."""
    validate_slot_datetime(starts_at)

    slot, created = TimeSlot.objects.get_or_create(
        starts_at=starts_at,
    )

    return slot


def get_bookable_slot(slot_id):
    """Retrieve and validate a slot that can be used for a reservation.

    The slot must:
        - exist
        - use the configured restaurant schedule
        - be in the future
    """
    try:
        slot = TimeSlot.objects.get(id=slot_id)
    except TimeSlot.DoesNotExist:
        raise TimeSlotError("The selected time slot does not exist.")

    current_timezone = timezone.get_current_timezone()

    slot_local_datetime = timezone.localtime(
        slot.starts_at,
        current_timezone,
    )

    now = timezone.localtime(
        timezone.now(),
        current_timezone,
    )

    if slot_local_datetime <= now:
        raise TimeSlotError("Reservations must be made for a future time slot.")

    restaurant_settings = get_restaurant_settings()

    opening_time = restaurant_settings.opening_time
    closing_time = restaurant_settings.closing_time
    interval_minutes = restaurant_settings.slot_interval_minutes

    requested_time = slot_local_datetime.time()

    if requested_time < opening_time:
        raise TimeSlotError("The selected time slot is before the restaurant opening time.")

    if requested_time > closing_time:
        raise TimeSlotError("The selected time slot is after the restaurant closing time.")

    opening_datetime = slot_local_datetime.replace(
        hour=opening_time.hour,
        minute=opening_time.minute,
        second=0,
        microsecond=0,
    )

    elapsed_seconds = (slot_local_datetime - opening_datetime).total_seconds()

    interval_seconds = interval_minutes * 60

    if elapsed_seconds % interval_seconds != 0:
        raise TimeSlotError("The selected time slot does not match the restaurant's configured slot interval.")

    return slot


# ---------------------------------------------------------
# Capacity
# ---------------------------------------------------------


def get_slot_capacity_status(slot):
    """Return capacity information for a slot.

    Informational only.

    This must not be used as the authoritative booking
    capacity check.
    """
    restaurant_settings = get_restaurant_settings()

    capacity = restaurant_settings.capacity_per_slot
    booked_seats = slot.booked_seats

    return {
        "capacity": capacity,
        "booked_seats": booked_seats,
        "remaining_seats": max(
            0,
            capacity - booked_seats,
        ),
    }


def reserve_seats(slot_id, guest_count):
    """Atomically reserve seats for a reservation.

    This is the authoritative capacity check.
    """
    if not isinstance(guest_count, int) or isinstance(guest_count, bool):
        raise TimeSlotError("guest_count must be an integer.")

    if guest_count < 1:
        raise TimeSlotError("guest_count must be at least 1.")

    with transaction.atomic():
        slot = TimeSlot.objects.select_for_update().get(id=slot_id)

        restaurant_settings = get_restaurant_settings()

        capacity = restaurant_settings.capacity_per_slot

        if slot.booked_seats + guest_count > capacity:
            remaining = max(
                0,
                capacity - slot.booked_seats,
            )

            raise SlotCapacityError(f"Only {remaining} seat(s) remain for this time slot.")

        slot.booked_seats += guest_count

        slot.save(update_fields=["booked_seats"])

        return slot


def release_seats(slot_id, guest_count):
    """Release seats when a reservation is cancelled or expires."""
    if not isinstance(guest_count, int) or isinstance(guest_count, bool):
        raise TimeSlotError("guest_count must be an integer.")

    if guest_count < 1:
        raise TimeSlotError("guest_count must be at least 1.")

    with transaction.atomic():
        slot = TimeSlot.objects.select_for_update().get(id=slot_id)

        if slot.booked_seats < guest_count:
            raise TimeSlotError(
                "Cannot release more seats than are "
                "currently booked. Check reservation "
                "state and seat-count consistency."
            )

        slot.booked_seats -= guest_count

        slot.save(update_fields=["booked_seats"])

        return slot
