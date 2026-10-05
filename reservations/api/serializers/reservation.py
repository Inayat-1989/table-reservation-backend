from rest_framework import serializers

from reservations.models import Reservation


class ReservationCreateSerializer(serializers.Serializer):
    """Validate the data needed to request a restaurant reservation."""

    full_name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )

    email = serializers.EmailField(
        max_length=254,
    )

    phone = serializers.CharField(
        max_length=30,
        trim_whitespace=True,
    )

    slot_id = serializers.IntegerField(min_value=1)

    guest_count = serializers.IntegerField(
        min_value=1,
    )

    selected_menu_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        allow_empty=True,
    )

    customer_note = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Full name cannot be empty.")
        return value

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Phone number cannot be empty.")
        return value

    def validate_selected_menu_item_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "A menu item cannot be selected more than once."
            )
        return value


class ReservationResponseSerializer(serializers.ModelSerializer):
    """Read-only reservation representation for the owning browser."""

    slot_id = serializers.IntegerField(
        source="slot.id",
        read_only=True,
    )

    slot_start = serializers.DateTimeField(
        source="slot.starts_at",
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
    )

    customer_email = serializers.EmailField(
        source="customer.email",
        read_only=True,
    )

    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )

    class Meta:
        model = Reservation
        fields = [
            "reference_code",
            "status",
            "guest_count",
            "slot_id",
            "slot_start",
            "customer_name",
            "customer_email",
            "customer_phone",
            "selected_menu_items",
            "special_menu_eligible",
            "customer_note",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReservationDraftCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )

    email = serializers.EmailField(
        max_length=254,
    )

    phone = serializers.CharField(
        max_length=30,
        trim_whitespace=True,
    )

    slot_id = serializers.IntegerField(
        min_value=1,
    )

    guest_count = serializers.IntegerField(
        min_value=1,
    )

    customer_note = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Full name cannot be empty.")

        return value

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Phone number cannot be empty.")

        return value


class ReservationDraftMenuUpdateSerializer(serializers.Serializer):
    selected_menu_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        allow_empty=True,
    )

    def validate_selected_menu_item_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "A menu item cannot be selected more than once."
            )

        return value
