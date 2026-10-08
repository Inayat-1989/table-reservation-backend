from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.api.pagination import (
    AdminMenuItemPagination,
)
from admin_portal.api.permissions import (
    HasAdminRole,
    IsAuthenticatedAdmin,
)
from admin_portal.api.serializers.menu import (
    AdminMenuCategorySerializer,
    AdminMenuItemFilterSerializer,
    AdminMenuItemSerializer,
)
from admin_portal.models import AdminRole
from reservations.selectors.menu import (
    get_admin_menu_categories,
    get_admin_menu_category,
    get_admin_menu_item,
    get_admin_menu_items,
)

MENU_MANAGEMENT_ROLES = (
    AdminRole.SUPER_ADMIN,
    AdminRole.ADMIN,
    AdminRole.MENU_MANAGER,
)


class AdminMenuCategoryListView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
        HasAdminRole,
    ]

    required_admin_roles = MENU_MANAGEMENT_ROLES

    def get(self, request):
        categories = get_admin_menu_categories()

        serializer = AdminMenuCategorySerializer(
            categories,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = AdminMenuCategorySerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        category = serializer.save()

        return Response(
            AdminMenuCategorySerializer(category).data,
            status=status.HTTP_201_CREATED,
        )


class AdminMenuCategoryDetailView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
        HasAdminRole,
    ]

    required_admin_roles = MENU_MANAGEMENT_ROLES

    def get(self, request, category_id):
        category = get_admin_menu_category(category_id)

        if category is None:
            return Response(
                {"detail": "Menu category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMenuCategorySerializer(category)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, category_id):
        category = get_admin_menu_category(category_id)

        if category is None:
            return Response(
                {"detail": "Menu category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMenuCategorySerializer(
            category,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        category = serializer.save()

        return Response(
            AdminMenuCategorySerializer(category).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, category_id):
        category = get_admin_menu_category(category_id)

        if category is None:
            return Response(
                {"detail": "Menu category not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            category.delete()
        except ProtectedError:
            return Response(
                {"detail": ("This category cannot be deleted because menu items are using it.")},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMenuItemDetailView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
        HasAdminRole,
    ]

    required_admin_roles = MENU_MANAGEMENT_ROLES

    def get(self, request, menu_item_id):
        menu_item = get_admin_menu_item(menu_item_id)

        if menu_item is None:
            return Response(
                {"detail": "Menu item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMenuItemSerializer(menu_item)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, menu_item_id):
        menu_item = get_admin_menu_item(menu_item_id)

        if menu_item is None:
            return Response(
                {"detail": "Menu item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMenuItemSerializer(
            menu_item,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        menu_item = serializer.save()

        return Response(
            AdminMenuItemSerializer(menu_item).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, menu_item_id):
        menu_item = get_admin_menu_item(menu_item_id)

        if menu_item is None:
            return Response(
                {"detail": "Menu item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        menu_item.is_deleted = True
        menu_item.is_available = False
        menu_item.save(
            update_fields=[
                "is_deleted",
                "is_available",
                "updated_at",
            ]
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMenuItemListView(APIView):
    permission_classes = [
        IsAuthenticatedAdmin,
        HasAdminRole,
    ]

    required_admin_roles = MENU_MANAGEMENT_ROLES
    pagination_class = AdminMenuItemPagination

    def get(self, request):
        filter_serializer = AdminMenuItemFilterSerializer(data=request.query_params)

        filter_serializer.is_valid(raise_exception=True)

        filters = filter_serializer.validated_data

        items = get_admin_menu_items(
            search=filters.get("search"),
            category_id=filters.get("category"),
            is_special=filters.get("is_special"),
            is_available=filters.get("is_available"),
        )

        paginator = self.pagination_class()

        if "page_size" in filters:
            paginator.page_size = filters["page_size"]

        page = paginator.paginate_queryset(
            items,
            request,
            view=self,
        )

        serializer = AdminMenuItemSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AdminMenuItemSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        menu_item = serializer.save()

        return Response(
            AdminMenuItemSerializer(menu_item).data,
            status=status.HTTP_201_CREATED,
        )
