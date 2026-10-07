from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from admin_portal.models import (
    AdminAccount,
    AdminLoginChallenge,
)
from admin_portal.services.session_service import (
    create_admin_session,
)
from admin_portal.utils.otp import (
    generate_otp,
    hash_otp,
    verify_otp,
)
from admin_portal.utils.security import (
    generate_token,
    hash_token,
)


class AdminAuthenticationError(Exception):
    """Base exception for custom admin authentication failures."""


class InvalidAdminCredentialsError(AdminAuthenticationError):
    """Raised when the supplied username/email or password is invalid."""


class InactiveAdminError(AdminAuthenticationError):
    """Raised when an admin account exists but is inactive."""


def authenticate_admin(identifier, password):
    """Validate an admin's login credentials.

    `identifier` may be either:
    - username
    - email

    Returns the AdminAccount if credentials are valid.
    """
    identifier = identifier.strip()

    admin = AdminAccount.objects.filter(username=identifier).first()

    if admin is None:
        admin = AdminAccount.objects.filter(email__iexact=identifier).first()

    if admin is None:
        raise InvalidAdminCredentialsError("Invalid username/email or password.")

    if not admin.is_active:
        raise InactiveAdminError("This admin account is inactive.")

    if not admin.check_password(password):
        raise InvalidAdminCredentialsError("Invalid username/email or password.")

    return admin


class InvalidLoginChallengeError(AdminAuthenticationError):
    """Raised when a login challenge is invalid, expired, or inactive."""


class InvalidOTPError(AdminAuthenticationError):
    """Raised when the supplied OTP is incorrect."""


class OTPAttemptLimitExceededError(AdminAuthenticationError):
    """Raised when the maximum OTP verification attempts have been reached."""


@transaction.atomic
def create_login_challenge(admin):
    """Create a new temporary 2FA login challenge.

    This does NOT create an AdminSession.

    Returns:
        {
            "challenge_token": raw temporary challenge token,
            "expires_at": datetime,
        }

    """
    now = timezone.now()

    challenge_duration = timedelta(
        minutes=settings.ADMIN_LOGIN_CHALLENGE_MINUTES,
    )

    expires_at = now + challenge_duration

    # Invalidate any previous active challenges.
    AdminLoginChallenge.objects.filter(
        admin=admin,
        is_active=True,
    ).update(
        is_active=False,
    )

    raw_challenge_token = generate_token()
    challenge_token_hash = hash_token(
        raw_challenge_token,
    )

    raw_otp = generate_otp()
    otp_hash = hash_otp(raw_otp)

    challenge = AdminLoginChallenge.objects.create(
        admin=admin,
        token_hash=challenge_token_hash,
        otp_hash=otp_hash,
        attempts=0,
        expires_at=expires_at,
        is_active=True,
    )

    return {
        "challenge": challenge,
        "challenge_token": raw_challenge_token,
        "otp": raw_otp,
        "expires_at": expires_at,
    }


def login(identifier, password):
    """Authenticate an admin and create a 2FA challenge.

    This method does NOT create an AdminSession.
    """
    admin = authenticate_admin(
        identifier=identifier,
        password=password,
    )

    challenge_data = create_login_challenge(admin)

    return {
        "admin": admin,
        **challenge_data,
    }


def verify_login_challenge(
    challenge_token,
    otp,
):
    """Verify a login challenge and its OTP.

    A fully authenticated AdminSession is created only after
    successful OTP verification.

    Returns:
        {
            "admin": AdminAccount,
            "session": AdminSession,
            "session_token": raw_session_token,
            "expires_at": datetime,
        }

    """
    now = timezone.now()

    challenge_token_hash = hash_token(
        challenge_token,
    )

    error = None

    with transaction.atomic():
        challenge = (
            AdminLoginChallenge.objects.select_for_update()
            .select_related("admin")
            .filter(
                token_hash=challenge_token_hash,
                is_active=True,
            )
            .first()
        )

        if challenge is None:
            error = InvalidLoginChallengeError(
                "The login challenge is invalid or has already been used.",
            )

        elif challenge.expires_at <= now:
            challenge.is_active = False

            challenge.save(
                update_fields=["is_active"],
            )

            error = InvalidLoginChallengeError(
                "The login challenge has expired.",
            )

        else:
            admin = challenge.admin

            if not admin.is_active:
                challenge.is_active = False

                challenge.save(
                    update_fields=["is_active"],
                )

                error = InactiveAdminError(
                    "This admin account is inactive.",
                )

            else:
                max_attempts = settings.ADMIN_OTP_MAX_ATTEMPTS

                if challenge.attempts >= max_attempts:
                    challenge.is_active = False

                    challenge.save(
                        update_fields=["is_active"],
                    )

                    error = OTPAttemptLimitExceededError(
                        "The maximum number of OTP attempts has been reached.",
                    )

                elif not verify_otp(
                    otp,
                    challenge.otp_hash,
                ):
                    challenge.attempts += 1

                    update_fields = [
                        "attempts",
                    ]

                    if challenge.attempts >= max_attempts:
                        challenge.is_active = False
                        update_fields.append("is_active")

                    challenge.save(
                        update_fields=update_fields,
                    )

                    if challenge.attempts >= max_attempts:
                        error = OTPAttemptLimitExceededError(
                            "The maximum number of OTP attempts has been reached.",
                        )
                    else:
                        error = InvalidOTPError(
                            "The OTP is incorrect.",
                        )

                else:
                    challenge.is_active = False
                    challenge.verified_at = now

                    challenge.save(
                        update_fields=[
                            "is_active",
                            "verified_at",
                        ],
                    )

                    session_data = create_admin_session(
                        admin,
                    )

                    result = {
                        "admin": admin,
                        **session_data,
                    }

    if error is not None:
        raise error

    return result
