from django.contrib import admin

from .models import (
    BrowserSession,
    Customer,
    MenuCategory,
    MenuItem,
    Reservation,
    ReservationOTP,
    RestaurantSettings,
    TimeSlot,
)

# --- INLINES ---


class ReservationInline(admin.TabularInline):
    """Allows viewing a customer's reservations directly on their profile."""

    model = Reservation
    extra = 0
    readonly_fields = ("reference_code", "slot", "guest_count", "status", "created_at")
    can_delete = False


class ReservationOTPInline(admin.TabularInline):
    """Allows viewing OTP attempt logs directly inside a Reservation details page."""

    model = ReservationOTP
    extra = 0
    readonly_fields = (
        "otp_hash",
        "expires_at",
        "attempts",
        "sent_at",
        "verified_at",
        "is_active",
    )
    can_delete = False


# --- MODEL ADMINS ---


@admin.register(BrowserSession)
class BrowserSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "token_hash_short", "created_at", "expires_at")
    list_filter = ("created_at", "expires_at")
    search_fields = ("token_hash",)
    readonly_fields = ("created_at",)

    @admin.display(description="Token Hash (Short)")
    def token_hash_short(self, obj):
        return f"{obj.token_hash[:8]}..." if obj.token_hash else "-"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "phone", "browser_session")
    search_fields = ("full_name", "email", "phone")
    inlines = [ReservationInline]


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "capacity_per_slot",
        "opening_time",
        "closing_time",
        "slot_interval_minutes",
    )


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "starts_at", "booked_seats")
    list_filter = ("starts_at",)
    ordering = ("starts_at",)


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("is_active",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "price",
        "is_special",
        "is_available",
        "is_deleted",
    )
    list_filter = ("category", "is_special", "is_available", "is_deleted")
    search_fields = ("title", "description", "is_deleted")
    list_editable = (
        "is_special",
        "is_available",
        "is_deleted",
    )  # Quick toggles from list view


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "customer",
        "slot",
        "guest_count",
        "status",
        "special_menu_eligible",
        "created_at",
    )
    list_filter = ("status", "special_menu_eligible", "slot__starts_at", "created_at")
    search_fields = ("reference_code", "customer__full_name", "customer__email")
    readonly_fields = ("reference_code", "created_at", "updated_at")
    list_editable = ("status",)  # Change reservation status directly from the list view
    inlines = [ReservationOTPInline]

    fieldsets = (
        (
            "Core Details",
            {"fields": ("reference_code", "customer", "slot", "guest_count", "status")},
        ),
        (
            "System Calculations",
            {"fields": ("special_menu_eligible", "selected_menu_items")},
        ),
        ("Notes & Expirations", {"fields": ("customer_note", "expires_at")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": (
                    "collapse",
                ),  # Keeps page organized by hiding timestamps by default
            },
        ),
    )


@admin.register(ReservationOTP)
class ReservationOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reservation",
        "attempts",
        "is_active",
        "sent_at",
        "verified_at",
    )
    list_filter = ("is_active", "sent_at", "verified_at")
    search_fields = ("reservation__reference_code", "reservation__customer__full_name")
    readonly_fields = ("sent_at",)
