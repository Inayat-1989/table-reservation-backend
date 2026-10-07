from django.core.management.base import BaseCommand

from reservations.models import (
    MenuCategory,
    MenuItem,
)
from reservations.seed_data.menu_categories import (
    INITIAL_MENU_CATEGORIES,
)
from reservations.seed_data.menu_items import (
    INITIAL_MENU_ITEMS,
)


class Command(BaseCommand):
    help = "Create missing initial menu categories and menu items."

    def handle(self, *args, **options):

        category_map = {}

        created_category_count = 0
        existing_category_count = 0

        for category_data in INITIAL_MENU_CATEGORIES:
            category, created = MenuCategory.objects.get_or_create(
                name=category_data["name"],
                defaults={
                    "description": category_data["description"],
                    "is_active": category_data["is_active"],
                },
            )

            category_map[category.name] = category

            if created:
                created_category_count += 1
            else:
                existing_category_count += 1

        created_item_count = 0
        existing_item_count = 0

        for item_data in INITIAL_MENU_ITEMS:
            category_name = item_data["category"]

            category = category_map.get(category_name)

            if category is None:
                self.stdout.write(
                    self.style.ERROR(f"Category '{category_name}' does not exist.")
                )
                continue

            item_defaults = {
                "category": category,
                "title": item_data["title"],
                "description": item_data["description"],
                "price": item_data["price"],
                "is_special": item_data["is_special"],
                "is_available": item_data["is_available"],
                "is_deleted": False,
                "src": item_data["src"],
            }

            item, created = MenuItem.objects.get_or_create(
                seed_key=item_data["seed_key"],
                defaults=item_defaults,
            )

            if created:
                created_item_count += 1
            else:
                existing_item_count += 1

        self.stdout.write(self.style.SUCCESS("Menu initialization complete."))

        self.stdout.write(
            f"Categories - "
            f"Created: {created_category_count}, "
            f"Already existed: {existing_category_count}"
        )

        self.stdout.write(
            f"Menu Items - "
            f"Created: {created_item_count}, "
            f"Already existed: {existing_item_count}"
        )
