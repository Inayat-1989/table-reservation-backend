from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.db import models


class AdminRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    RESERVATION_VIEWER = "RESERVATION_VIEWER", "Reservation Viewer"
    MENU_MANAGER = "MENU_MANAGER", "Menu Manager"


class AdminAccount(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )

    username = models.CharField(
        max_length=100,
        unique=True,
    )

    email = models.EmailField(
        unique=True,
    )

    password_hash = models.CharField(
        max_length=128,
    )

    first_name = models.CharField(
        max_length=100,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        max_length=30,
        choices=AdminRole.choices,
        default=AdminRole.ADMIN,
    )

    is_active = models.BooleanField(
        default=True,
    )

    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(
            raw_password,
            self.password_hash,
        )

    def __str__(self):
        return self.username


class AdminLoginChallenge(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )

    admin = models.ForeignKey(
        AdminAccount,
        on_delete=models.CASCADE,
        related_name="login_challenges",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    otp_hash = models.CharField(
        max_length=64,
    )

    attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["admin", "is_active"],
                name="admin_challenge_active_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="admin_challenge_exp_idx",
            ),
        ]

    def __str__(self):
        return f"2FA challenge for {self.admin.username}"


class AdminSession(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )

    admin = models.ForeignKey(
        AdminAccount,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )

    last_activity_at = models.DateTimeField(
        auto_now=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["admin", "expires_at"],
                name="admin_session_exp_idx",
            ),
        ]

    def __str__(self):
        return f"Session for {self.admin.username}"
