import uuid
from datetime import time

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class BrowserSession(models.Model):
    id = models.BigAutoField(primary_key=True)

    # SHA-256 hash of the opaque browser-session token.
    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    def __str__(self):
        return f"Browser session {self.pk}"


class Customer(models.Model):
    id = models.BigAutoField(primary_key=True)

    browser_session = models.OneToOneField(
        BrowserSession,
        on_delete=models.CASCADE,
        related_name="customer",
    )

    full_name = models.CharField(max_length=150)

    email = models.EmailField()

    phone = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class RestaurantSettings(models.Model):
    id = models.BigAutoField(primary_key=True)

    capacity_per_slot = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    opening_time = models.TimeField(default=time(10, 0))

    closing_time = models.TimeField(default=time(23, 0))

    slot_interval_minutes = models.PositiveIntegerField(default=30, validators=[MinValueValidator(1)])

    def __str__(self):
        return "Restaurant Settings"


class TimeSlot(models.Model):
    id = models.BigAutoField(primary_key=True)

    starts_at = models.DateTimeField(
        unique=True,
    )

    booked_seats = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        local_time = timezone.localtime(self.starts_at)
        return local_time.strftime("%Y-%m-%d %H:%M")


class MenuCategory(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )

    seed_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.PROTECT,
        related_name="menu_items",
    )

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    # Path/key of the image.
    src = models.CharField(
        max_length=500,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    is_special = models.BooleanField(
        default=False,
    )

    is_available = models.BooleanField(
        default=True,
    )

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Reservation(models.Model):
    class Status(models.TextChoices):
        DRAFT = ("DRAFT", "Draft")
        PENDING_VERIFICATION = (
            "PENDING_VERIFICATION",
            "Pending Email Verification",
        )
        CONFIRMED = (
            "CONFIRMED",
            "Confirmed",
        )
        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )
        COMPLETED = (
            "COMPLETED",
            "Completed",
        )
        EXPIRED = (
            "EXPIRED",
            "Expired",
        )

    id = models.BigAutoField(primary_key=True)

    # Public identifier shown to the customer.
    reference_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    guest_count = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING_VERIFICATION,
        db_index=True,
    )

    # Calculated by the backend.
    # True if reservation qualifies for the special menu
    # based on the restaurant's 24-hour rule.
    special_menu_eligible = models.BooleanField(
        default=False,
    )

    # List of MenuItem IDs selected by the customer.
    selected_menu_items = models.JSONField(
        default=list,
        blank=True,
    )

    customer_note = models.TextField(
        blank=True,
    )

    # Reservation expiry is NOT OTP expiry.
    # Example: pending reservation expires after a certain period
    # if the customer does not complete verification.
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["customer", "created_at"],
                name="res_cus_created_idx",
            ),
            models.Index(
                fields=["slot", "status"],
                name="res_slot_status_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(guest_count__gte=1),
                name="res_guest_count",
            ),
        ]

    def __str__(self):
        return f"Reservation {self.reference_code} ({self.status})"


class ReservationOTP(models.Model):
    id = models.BigAutoField(primary_key=True)

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="otp_attempts_history",
    )

    # Store a hash/HMAC of the OTP, NEVER the plaintext OTP.
    otp_hash = models.CharField(
        max_length=64,
    )

    # When this particular OTP becomes invalid.
    expires_at = models.DateTimeField(
        db_index=True,
    )

    # Number of verification attempts against this OTP.
    attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    # When this OTP was sent.
    sent_at = models.DateTimeField(
        auto_now_add=True,
    )

    # Whether this specific OTP was successfully used.
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Useful for invalidating an older OTP when a new one is sent.
    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["-sent_at"]

        indexes = [
            models.Index(
                fields=["reservation", "is_active"],
                name="otp_res_active_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="otp_expires_idx",
            ),
        ]

    def __str__(self):
        return f"OTP for reservation {self.reservation_id}"
