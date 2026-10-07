from django.conf import settings

from admin_portal.services.session_service import (
    InvalidAdminSessionError,
    get_admin_from_session_token,
)


class AdminAuthenticationMiddleware:
    """Resolve the authenticated admin for custom admin API requests.

    Authentication is handled here.
    Authorization is handled separately by the API permission layer.
    """

    def __init__(self, get_response):
        """Middleware Initialization."""
        self.get_response = get_response

    def __call__(self, request):
        request.admin = None

        if request.path.startswith(settings.ADMIN_API_PREFIX):
            session_token = request.COOKIES.get(
                settings.ADMIN_SESSION_COOKIE,
            )

            if session_token:
                try:
                    request.admin = get_admin_from_session_token(
                        session_token,
                    )

                except InvalidAdminSessionError:
                    request.admin = None

        return self.get_response(request)
