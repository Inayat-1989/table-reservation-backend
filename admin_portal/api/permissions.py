from rest_framework.permissions import BasePermission


class IsAuthenticatedAdmin(BasePermission):
    """Allow access only when the request has an authenticated active admin."""

    message = "Admin authentication is required."

    def has_permission(self, request, view):
        return request.admin is not None


class HasAdminRole(BasePermission):
    """Allow access only when the authenticated admin has one of the roles required by the view.

    The view must define:

        required_admin_roles = (
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
        )
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        admin = request.admin

        if admin is None:
            return False

        required_roles = getattr(
            view,
            "required_admin_roles",
            (),
        )

        return admin.role in required_roles
