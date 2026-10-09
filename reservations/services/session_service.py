from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from reservations.models import BrowserSession, Customer
from reservations.utils.security import (
    generate_browser_session_token,
    hash_browser_session_token,
)


def create_browser_session():
    """Create a new browser session.

    Returns:
        tuple[BrowserSession, str]
        The database object and the raw token that
        should be sent to the browser as a cookie.

    """
    raw_token = generate_browser_session_token()

    token_hash = hash_browser_session_token(raw_token)

    expires_at = timezone.now() + timedelta(days=settings.BROWSER_SESSION_DAYS)

    session = BrowserSession.objects.create(
        token_hash=token_hash,
        expires_at=expires_at,
    )

    return session, raw_token


def get_browser_session(raw_token):
    """Find a valid browser session using the raw token received from the browser cookie."""
    if not raw_token:
        return None

    token_hash = hash_browser_session_token(raw_token)

    session = BrowserSession.objects.filter(
        token_hash=token_hash,
        expires_at__gt=timezone.now(),
    ).first()

    return session


def get_or_create_customer(
    browser_session,
    *,
    full_name,
    email,
    phone,
):
    """Get the customer belonging to the browser session, or create one if this is the first reservation."""
    customer = Customer.objects.create(
        browser_session=browser_session,
        full_name=full_name,
        email=email,
        phone=phone,
    )

    if not customer:
        customer.full_name = full_name
        customer.email = email
        customer.phone = phone
        customer.save(
            update_fields=[
                "full_name",
                "email",
                "phone",
            ]
        )

    return customer


def get_or_create_browser_session(raw_token):
    """Return an existing valid browser session or create a new one.

    Returns:
        tuple[BrowserSession, str | None]

    The second value is a newly generated raw token when a new
    session was created, otherwise None.

    """
    existing_session = get_browser_session(raw_token)

    if existing_session:
        return existing_session, None

    session, new_token = create_browser_session()

    return session, new_token
