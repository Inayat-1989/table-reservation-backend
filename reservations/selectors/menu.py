from reservations.models import MenuItem


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
