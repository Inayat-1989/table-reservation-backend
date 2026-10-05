from rest_framework import serializers

from reservations.models import MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    """Read-only representation of a menu item for the frontend."""

    class Meta:
        model = MenuItem

        fields = [
            "id",
            "category",
            "title",
            "description",
            "src",
            "price",
            "is_special",
            "is_available",
        ]

        read_only_fields = fields
