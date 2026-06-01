from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Floor
from api.permissions import AdminPermission
from api.serializers.locations_serializer import (
    FloorListSerializer,
    FloorMapDataSerializer,
    RoomBlockSerializer,
)
from api.services.locations_service import LocationsService


class FloorsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Локації"],
        summary="Отримання поверхів конкретного гуртожитку",
        description="Ендпоінт для отримання відсортованого списку поверхів конкретного гуртожитку за його ID.",
        parameters=[
            OpenApiParameter(
                name="dormitory_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="Унікальний ідентифікатор гуртожитку (наприклад, 1 для Гуртожитку №1).",
                examples=[OpenApiExample("Гуртожиток №1", value=1), OpenApiExample("Гуртожиток №2", value=2)],
            )
        ],
        responses={
            200: OpenApiResponse(
                response=FloorListSerializer(many=True), description="Успішне отримання списку поверхів."
            ),
            401: OpenApiResponse(
                description="Не авторизовано (відсутній або недійсний токен).",
                response=dict,
                examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!."})],
            ),
            404: OpenApiResponse(
                description="Гуртожиток не знайдено.",
                response=dict,
                examples=[
                    OpenApiExample("Гуртожиток відсутній", value={"detail": "Гуртожитку з таким id не знайдено!"})
                ],
            ),
        },
    )
    def get(self, request, dormitory_id):
        service = LocationsService()
        try:
            floors = service.get_floors_by_dormitory_id(dormitory_id)

            serializer = FloorListSerializer(floors, many=True)

            return Response(serializer.data)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class FloorMapDataView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Локації"],
        summary="Отримання мапи поверху",
        description="Ендпоінт для отримання мапи конкретного поверху за його ID, "
        "з кімнатами, ресурсами, івентами та користувачами на ньому",
        parameters=[
            OpenApiParameter(
                name="floor_id",
                type=int,
                location="path",
                required=True,
                description="Унікальний ідентифікатор поверху (його ID у базі даних, а не фізичний номер).",
                examples=[OpenApiExample("Поверх 1", value=1), OpenApiExample("Поверх 2", value=2)],
            )
        ],
        responses={
            200: OpenApiResponse(
                response=FloorMapDataSerializer(),
                description="Успішне отримання повної мапи поверху.",
                examples=[
                    OpenApiExample(
                        "Детальна мапа поверху",
                        value={
                            "id": 1,
                            "number": 1,
                            "map_file": "/media/maps/floor_1.svg",
                            "dormitory_name": "Гуртожиток №1",
                            "rooms": [
                                {
                                    "id": 101,
                                    "name": "114",
                                    "room_type": "LIVING",
                                    "max_person": 4,
                                    "is_blocked": False,
                                    "svg_element_id": "room_114_polygon",
                                    "resources": [],
                                    "current_users": [
                                        {
                                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                            "display_name": "Новий мешканець",
                                            "photo": None,
                                        },
                                        {
                                            "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                                            "display_name": "Новий мешканець",
                                            "photo": None,
                                        },
                                    ],
                                    "active_events": [],
                                },
                                {
                                    "id": 102,
                                    "name": "Кухня лівого крила",
                                    "room_type": "KITCHEN",
                                    "max_person": 10,
                                    "is_blocked": False,
                                    "svg_element_id": "kitchen_left_polygon",
                                    "resources": [
                                        {
                                            "id": 1,
                                            "name": "Електроплита №1",
                                            "max_person": 1,
                                            "is_blocked": False,
                                            "resource_type": "OVEN",
                                            "resource_icon": "/media/resource-icons/oven.svg",
                                        }
                                    ],
                                    "current_users": [],
                                    "active_events": [
                                        {
                                            "id": 42,
                                            "title": "Спільне приготування вечері",
                                            "creator": {
                                                "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                                                "display_name": "Surname Name Middle_name",
                                                "photo": "/media/avatars/"
                                                "avatar_87fb51a6-5abd-4398-bd5f-7a15dfdafa2d.jpg",
                                            },
                                            "participants_count": 3,
                                        }
                                    ],
                                },
                            ],
                            "active_floor_events": [
                                {
                                    "id": 15,
                                    "title": "Вечір настільних ігор у холі",
                                    "creator": {
                                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                        "display_name": "Безух Данило Валентинович",
                                        "photo": "/media/avatars/avatar_87fb51a6-5abd-4398-bd5f-7a15dfdafa2d.jpg",
                                    },
                                    "participants_count": 8,
                                }
                            ],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Не авторизовано (відсутній або недійсний токен).",
                response=dict,
                examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!."})],
            ),
            404: OpenApiResponse(
                description="Поверх не знайдено.",
                response=dict,
                examples=[OpenApiExample("Поверх відсутній", value={"detail": "Поверху з таким id не знайдено!"})],
            ),
        },
    )
    def get(self, request, floor_id):
        try:
            floor = Floor.objects.get(id=floor_id)
            serializer = FloorMapDataSerializer(floor, context={"request": request})

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Floor.DoesNotExist:
            return Response({"detail": "Поверху з таким id не знайдено!"}, status=status.HTTP_404_NOT_FOUND)


class RoomBlockView(APIView):
    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Блокування кімнати (лише адміністратор)",
        request=None,
        parameters=[
            OpenApiParameter(
                name="room_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID кімнати, яку адміністратор блокує.",
            )
        ],
        responses={
            200: OpenApiResponse(response=RoomBlockSerializer, description="Кімнату заблоковано."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Тільки адміністратор може блокувати кімнати."),
            404: OpenApiResponse(
                description="Кімнату не знайдено.",
                response=dict,
                examples=[OpenApiExample("Кімната відсутня", value={"detail": "Кімнату з таким id не знайдено!"})],
            ),
        },
    )
    def patch(self, request, room_id):
        service = LocationsService()
        try:
            room = service.set_room_blocked(room_id, True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoomBlockSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomUnblockView(APIView):
    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Розблокування кімнати (лише адміністратор)",
        request=None,
        parameters=[
            OpenApiParameter(
                name="room_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID кімнати, яку адміністратор розблоковує.",
            )
        ],
        responses={
            200: OpenApiResponse(response=RoomBlockSerializer, description="Кімнату розблоковано."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Тільки адміністратор може розблоковувати кімнати."),
            404: OpenApiResponse(
                description="Кімнату не знайдено.",
                response=dict,
                examples=[OpenApiExample("Кімната відсутня", value={"detail": "Кімнату з таким id не знайдено!"})],
            ),
        },
    )
    def patch(self, request, room_id):
        service = LocationsService()
        try:
            room = service.set_room_blocked(room_id, False)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoomBlockSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
