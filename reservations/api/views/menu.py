from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.api.serializers.menu import MenuItemSerializer
from reservations.selectors.menu import get_available_menu_items


class MenuListView(APIView):
    """
    Return all currently available menu items.
    """

    def get(self, request):
        menu_items = get_available_menu_items()

        serializer = MenuItemSerializer(
            menu_items,
            many=True,
        )

        return Response(serializer.data)
