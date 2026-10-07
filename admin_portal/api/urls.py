from django.urls import path

from admin_portal.api.views.authentication import (
    AdminLoginView,
    AdminLogoutView,
    AdminMeView,
    AdminOTPVerifyView,
)
from admin_portal.api.views.dashboard import (
    AdminDashboardView,
    AdminPeakReservationHoursView,
    AdminReservationSlotPopularityView,
    AdminReservationTrendView,
)

urlpatterns = [
    path(
        "login/",
        AdminLoginView.as_view(),
        name="admin-login",
    ),
    path(
        "2fa/verify/",
        AdminOTPVerifyView.as_view(),
        name="admin-2fa-verify",
    ),
    path(
        "logout/",
        AdminLogoutView.as_view(),
        name="admin-logout",
    ),
    path(
        "me/",
        AdminMeView.as_view(),
        name="admin-me",
    ),
    path(
        "dashboard/",
        AdminDashboardView.as_view(),
        name="admin-dashboard",
    ),
    path(
        "dashboard/trends/",
        AdminReservationTrendView.as_view(),
        name="admin-dashboard-trends",
    ),
    path(
        "dashboard/peak-hours/",
        AdminPeakReservationHoursView.as_view(),
        name="admin-dashboard-peak-hours",
    ),
    path(
        "dashboard/slot-popularity/",
        AdminReservationSlotPopularityView.as_view(),
        name="admin-dashboard-slot-popularity",
    ),
]
