from .menu import MenuListView
from .otp import (
    OTPResendView,
    OTPVerifyView,
)
from .reservation import (
    ActiveReservationView,
    ReservationCancelView,
    ReservationCreateView,
    ReservationDetailView,
    ReservationDraftCreateView,
    ReservationDraftFinalizeView,
    ReservationDraftMenuUpdateView,
    ReservationListView,
)
from .slot import SlotListView

__all__ = [
    "ActiveReservationView",
    "MenuListView",
    "OTPResendView",
    "OTPVerifyView",
    "ReservationCancelView",
    "ReservationCreateView",
    "ReservationDetailView",
    "ReservationDraftCreateView",
    "ReservationDraftFinalizeView",
    "ReservationDraftMenuUpdateView",
    "ReservationListView",
    "SlotListView",
]
