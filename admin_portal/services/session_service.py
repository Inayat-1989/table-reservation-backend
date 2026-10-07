# admin_portal/services/session_service.py

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from admin_portal.models import AdminSession
from admin_portal.utils.security import (
    generate_token,
    hash_token,
)


class AdminSessionError(Exception):
    """Base exception for admin session failures."""


class InvalidAdminSessionError(AdminSessionError):
    """Raised when an admin session is invalid or expired."""


def create_admin_session(admin):
    """Create a new authenticated admin session.

    Returns the raw session token and session object.

    The raw token is intended to be placed in an HttpOnly cookie.
    Only its hash is stored in the database.
    """
    now = timezone.now()

    session_duration = timedelta(
        days=settings.ADMIN_SESSION_DAYS,
    )

    expires_at = now + session_duration

    raw_session_token = generate_token()

    session_token_hash = hash_token(
        raw_session_token,
    )

    session = AdminSession.objects.create(
        admin=admin,
        token_hash=session_token_hash,
        expires_at=expires_at,
    )

    return {
        "session": session,
        "session_token": raw_session_token,
        "expires_at": expires_at,
    }


def get_admin_from_session_token(raw_session_token):
    """Validate an admin session token and return the authenticated admin.

    The raw token comes from the HttpOnly browser cookie.
    """
    if not raw_session_token:
        raise InvalidAdminSessionError(
            "Admin session is required.",
        )

    token_hash = hash_token(
        raw_session_token,
    )

    session = (
        AdminSession.objects.select_related("admin")
        .filter(
            token_hash=token_hash,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            admin__is_active=True,
        )
        .first()
    )

    if session is None:
        raise InvalidAdminSessionError(
            "Admin session is invalid or expired.",
        )

    session.last_activity_at = timezone.now()
    session.save(
        update_fields=["last_activity_at"],
    )

    return session.admin


def revoke_admin_session(raw_session_token):
    """Revoke the admin session represented by the raw session token.

    Returns True if a session was revoked, otherwise False.
    """
    if not raw_session_token:
        return False

    token_hash = hash_token(
        raw_session_token,
    )

    updated_count = AdminSession.objects.filter(
        token_hash=token_hash,
        revoked_at__isnull=True,
    ).update(
        revoked_at=timezone.now(),
    )

    return updated_count > 0
