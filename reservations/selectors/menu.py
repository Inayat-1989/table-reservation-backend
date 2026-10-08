from django.db.models import Q

from reservations.models import MenuCategory, MenuItem


def get_available_menu_items():
    """Return all menu items currently available to customers."""
    return MenuItem.objects.filter(is_available=True).order_by("category", "title")


def get_menu_item_by_id(menu_item_id):
    """Return an available menu item by its ID.

    Return None if it doesn't exist or isn't available.
    """
    return MenuItem.objects.filter(
        id=menu_item_id,
        is_available=True,
        is_deleted=False,
    ).first()


def get_available_menu_items_by_ids(menu_item_ids):
    """Return available menu items matching a collection of IDs.

    Useful when validating the menu items selected during
    reservation creation.
    """
    if not menu_item_ids:
        return MenuItem.objects.none()

    return MenuItem.objects.filter(
        id__in=menu_item_ids,
        is_available=True,
        is_deleted=False,
    )


def get_admin_menu_categories():
    return MenuCategory.objects.order_by("name")


def get_admin_menu_category(category_id):
    return MenuCategory.objects.filter(id=category_id).first()


def get_admin_menu_items(
    search=None,
    category_id=None,
    is_special=None,
    is_available=None,
):
    queryset = (
        MenuItem.objects.select_related("category")
        .filter(
            is_deleted=False,
        )
        .order_by("title")
    )

    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)

    if is_special:
        queryset = queryset.filter(is_special=is_special)

    if is_available:
        queryset = queryset.filter(is_available=is_available)

    return queryset


def get_admin_menu_item(menu_item_id):
    return (
        MenuItem.objects.select_related("category")
        .filter(
            id=menu_item_id,
            is_deleted=False,
        )
        .first()
    )
