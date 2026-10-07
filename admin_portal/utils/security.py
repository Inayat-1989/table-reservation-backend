import hashlib
import secrets


def generate_token():
    """
    Generate a cryptographically secure random token.

    The raw token is intended to be given to the client
    through a secure HttpOnly cookie.

    Only its hash should be stored in the database.
    """
    return secrets.token_urlsafe(32)


def hash_token(token):
    """
    Hash a token before storing or looking it up in the database.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
