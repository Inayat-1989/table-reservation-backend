from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.api.permissions import (
    IsAuthenticatedAdmin,
)
from admin_portal.api.serializers.authentication import (
    AdminLoginSerializer,
    AdminOTPVerifySerializer,
)
from admin_portal.services.authentication import (
    InactiveAdminError,
    InvalidAdminCredentialsError,
    InvalidLoginChallengeError,
    InvalidOTPError,
    OTPAttemptLimitExceededError,
    login,
    verify_login_challenge,
)
from admin_portal.services.session_service import (
    revoke_admin_session,
)
from rest_framework.permissions import AllowAny

from admin_portal.api.permissions import IsAuthenticatedAdmin
from admin_portal.api.serializers.authentication import (
    AdminMeSerializer,
)

# required_admin_roles = (
#     AdminRole.MENU_MANAGER,
#     AdminRole.ADMIN,
#     AdminRole.SUPER_ADMIN,
#     AdminRole.RESERVATION_VIEWER,
# )


class AdminLoginView(APIView):
    def post(self, request):
        serializer = AdminLoginSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]

        try:
            login_data = login(
                identifier=identifier,
                password=password,
            )

        except InvalidAdminCredentialsError:
            return Response(
                {
                    "detail": "Invalid username/email or password.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except InactiveAdminError:
            return Response(
                {
                    "detail": "This admin account is inactive.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "detail": ("Credentials verified. A verification code has been sent."),
                "challenge_token": login_data["challenge_token"],
                "expires_at": login_data["expires_at"],
            },
            status=status.HTTP_200_OK,
        )


class AdminOTPVerifyView(APIView):
    def post(self, request):
        serializer = AdminOTPVerifySerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        challenge_token = serializer.validated_data["challenge_token"]

        otp = serializer.validated_data["otp"]

        try:
            session_data = verify_login_challenge(
                challenge_token=challenge_token,
                otp=otp,
            )

        except InvalidLoginChallengeError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except InvalidOTPError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except OTPAttemptLimitExceededError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except InactiveAdminError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        response = Response(
            {
                "detail": "Admin login successful.",
                "admin": {
                    "id": session_data["admin"].id,
                    "username": session_data["admin"].username,
                    "email": session_data["admin"].email,
                    "first_name": session_data["admin"].first_name,
                    "last_name": session_data["admin"].last_name,
                    "role": session_data["admin"].role,
                },
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            key="admin_session",
            value=session_data["session_token"],
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=60 * 60 * 24,
        )

        return response


class AdminLogoutView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
    ]

    def post(self, request):

        session_token = request.COOKIES.get(
            "admin_session",
        )

        revoke_admin_session(
            session_token,
        )

        response = Response(
            {
                "detail": "Admin logout successful.",
            },
            status=status.HTTP_200_OK,
        )

        response.delete_cookie(
            "admin_session",
        )

        return response

class AdminMeView(APIView):
    permission_classes = [IsAuthenticatedAdmin]

    def get(self, request):
        admin = request.admin

        serializer = AdminMeSerializer(
            {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "role": admin.role,
            }
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )