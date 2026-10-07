from rest_framework import serializers


class AdminLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=100,
        required=True,
    )

    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )


class AdminOTPVerifySerializer(serializers.Serializer):
    challenge_token = serializers.CharField(
        required=True,
    )

    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
    )


class AdminMeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.CharField()
