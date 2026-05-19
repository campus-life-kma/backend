from django.db.models import QuerySet

from api.models import Floor
from api.models.locations import Dormitory


class LocationsService:
    def get_floors_by_dormitory_id(self, dormitory_id) -> QuerySet[Floor]:
        try:
            dormitory = Dormitory.objects.get(id=dormitory_id)

            floors = Floor.objects.filter(dormitory=dormitory)

            return floors.order_by("number")

        except Dormitory.DoesNotExist:
            raise ValueError("Гуртожитку з таким id не знайдено!")
