from django.conf import settings
from rest_framework import serializers


class OTPRequestSerializer(serializers.Serializer):
    """Validate a request to send or resend a reservation OTP."""

    reference_code = serializers.UUIDField()


class OTPVerifySerializer(serializers.Serializer):
    """Validate an OTP verification request."""

    reference_code = serializers.UUIDField()

    otp = serializers.CharField(
        min_length=settings.OTP_LENGTH,
        max_length=settings.OTP_LENGTH,
        trim_whitespace=True,
        write_only=True,
    )

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("The OTP must contain digits only.")

        return value
