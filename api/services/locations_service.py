from django.db.models import QuerySet

from api.models import Floor, Room
from api.models.locations import Dormitory


class LocationsService:
    def get_floors_by_dormitory_id(self, dormitory_id) -> QuerySet[Floor]:
        try:
            dormitory = Dormitory.objects.get(id=dormitory_id)

            floors = Floor.objects.filter(dormitory=dormitory)

            return floors.order_by("number")

        except Dormitory.DoesNotExist:
            raise ValueError("Гуртожитку з таким id не знайдено!")

    def set_room_blocked(self, room_id, is_blocked: bool) -> Room:
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise ValueError("Кімнату з таким id не знайдено!")

        room.is_blocked = is_blocked
        room.save(update_fields=["is_blocked"])

        return room
