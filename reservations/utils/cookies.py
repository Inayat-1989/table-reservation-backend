from django.conf import settings

BROWSER_SESSION_COOKIE = "browser_session"


def get_browser_session_token(request):
    return request.COOKIES.get(BROWSER_SESSION_COOKIE)


def set_browser_session_cookie(response, raw_token):
    """
    Set the browser-session cookie when a new session was created.

    The raw token is HttpOnly so JavaScript cannot read it.
    """

    if not raw_token:
        return

    response.set_cookie(
        key=BROWSER_SESSION_COOKIE,
        value=raw_token,
        max_age=settings.BROWSER_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.BROWSER_SESSION_COOKIE_SECURE,
        samesite=settings.BROWSER_SESSION_COOKIE_SAMESITE,
    )
