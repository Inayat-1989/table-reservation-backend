from rest_framework import serializers

from reservations.models import MenuCategory, MenuItem


class AdminMenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class AdminMenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "seed_key",
            "category",
            "category_name",
            "title",
            "description",
            "src",
            "price",
            "is_special",
            "is_available",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "seed_key",
            "category_name",
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")

        return value


class AdminMenuItemFilterSerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    category = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    is_special = serializers.BooleanField(
        required=False,
    )

    is_available = serializers.BooleanField(
        required=False,
    )

    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
    )
