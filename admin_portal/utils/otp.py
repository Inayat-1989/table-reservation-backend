import hashlib
import secrets

from django.conf import settings


def generate_otp():
    """
    Generate a cryptographically secure numeric OTP.
    """
    return f"{secrets.randbelow(1_000_000):0{settings.OTP_LENGTH}d}"


def hash_otp(otp):
    """
    Hash an OTP before storing it in the database.
    """
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def verify_otp(otp, otp_hash):
    """
    Verify a raw OTP against its stored hash.
    """
    return secrets.compare_digest(
        hash_otp(otp),
        otp_hash,
    )
