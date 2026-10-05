from django.core.management.base import BaseCommand

from reservations.models import MenuItem
from reservations.seed_data.menu_items import (
    INITIAL_MENU_ITEMS,
)


class Command(BaseCommand):
    help = "Create missing initial menu items."

    def handle(self, *args, **options):

        created_count = 0
        existing_count = 0

        for item_data in INITIAL_MENU_ITEMS:
            seed_key = item_data["seed_key"]

            item, created = MenuItem.objects.get_or_create(
                seed_key=seed_key,
                defaults=item_data,
            )

            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Menu initialization complete. "
                f"Created: {created_count}, "
                f"Already existed: {existing_count}."
            )
        )
