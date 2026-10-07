import hashlib
import secrets


def generate_browser_session_token():
    """Generate a cryptographically secure random token used to identify a browser session."""
    return secrets.token_urlsafe(32)


def hash_browser_session_token(token):
    """Hash the browser session token before storing or looking it up in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
