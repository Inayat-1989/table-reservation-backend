import hashlib
import hmac
import secrets

from django.conf import settings


def generate_otp():
    """Generate a numeric OTP using the configured OTP length."""
    minimum = 10 ** (settings.OTP_LENGTH - 1)
    maximum = (10**settings.OTP_LENGTH) - 1

    return str(secrets.randbelow(maximum - minimum + 1) + minimum)


def hash_otp(otp):
    """Hash the OTP before storing it in the database.

    HMAC is used because a six-digit OTP has very low entropy.
    """
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(otp, stored_hash):
    """Safely compare a submitted OTP against the stored hash."""
    calculated_hash = hash_otp(otp)

    return hmac.compare_digest(
        calculated_hash,
        stored_hash,
    )
