from django.contrib import admin

from .models import (
    AdminAccount,
    AdminLoginChallenge,
    AdminSession,
)


@admin.register(AdminAccount)
class AdminAccountAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "last_login_at",
        "created_at",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    readonly_fields = (
        "last_login_at",
        "created_at",
        "updated_at",
    )

    ordering = ("username",)


@admin.register(AdminLoginChallenge)
class AdminLoginChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "admin",
        "attempts",
        "created_at",
        "expires_at",
        "verified_at",
        "is_active",
    )

    list_filter = (
        "is_active",
        "verified_at",
    )

    search_fields = (
        "admin__username",
        "admin__email",
    )

    readonly_fields = (
        "token_hash",
        "otp_hash",
        "created_at",
        "expires_at",
        "verified_at",
    )

    ordering = ("-created_at",)


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    list_display = (
        "admin",
        "created_at",
        "expires_at",
        "last_activity_at",
        "revoked_at",
    )

    list_filter = (
        "revoked_at",
        "expires_at",
    )

    search_fields = (
        "admin__username",
        "admin__email",
    )

    readonly_fields = (
        "token_hash",
        "created_at",
        "expires_at",
        "last_activity_at",
        "revoked_at",
    )

    ordering = ("-created_at",)
