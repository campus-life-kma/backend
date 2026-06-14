from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from api.models import Floor
from api.permissions import AdminPermission
from api.serializers.locations_serializer import (
    FloorListSerializer,
    FloorMapDataSerializer,
    RoomBlockSerializer,
    RoomCreateSerializer,
    RoomMapSerializer,
    RoomUpdateSerializer,
    ResourceCreateUpdateSerializer,
    ResourceSerializer,
)
from api.services.locations_service import LocationsService


class FloorsView(APIView):
    """Ендпоінт для отримання списку поверхів конкретного гуртожитку."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

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
        """Повертає відсортований список поверхів гуртожитку.

        Args:
            request: HTTP-запит.
            dormitory_id: Ідентифікатор гуртожитку.

        Returns:
            Response: Список поверхів або 404, якщо гуртожиток не знайдено.
        """
        service = LocationsService()
        try:
            floors = service.get_floors_by_dormitory_id(dormitory_id)

            serializer = FloorListSerializer(floors, many=True, context={"request": request})

            return Response(serializer.data)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=["Локації"],
        summary="Створення нового поверху",
        description="Створює новий поверх. Приймає номер поверху та SVG мапу.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "map_file": {"type": "string", "format": "binary"},
                },
                "required": ["number", "map_file"],
            }
        },
        responses={
            201: FloorListSerializer,
            400: OpenApiResponse(description="Помилка валідації або поверх вже існує."),
        },
    )
    def post(self, request, dormitory_id):
        try:
            number = int(request.data.get("number"))
            map_file = request.data.get("map_file")
            if not map_file:
                return Response({"detail": "map_file обов'язковий."}, status=status.HTTP_400_BAD_REQUEST)

            service = LocationsService()
            floor = service.create_floor(request.user, dormitory_id, number, map_file)
            serializer = FloorListSerializer(floor, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FloorMapDataView(APIView):
    """Ендпоінт для отримання повної мапи поверху з кімнатами та подіями."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

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
                            "notice": "",
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
        """Повертає дані мапи поверху разом із кімнатами та активними подіями.

        Args:
            request: HTTP-запит.
            floor_id: Ідентифікатор поверху в базі даних.

        Returns:
            Response: Дані мапи або 404, якщо поверх не знайдено.
        """
        try:
            floor = Floor.objects.get(id=floor_id)
            serializer = FloorMapDataSerializer(floor, context={"request": request})

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Floor.DoesNotExist:
            return Response({"detail": "Поверху з таким id не знайдено!"}, status=status.HTTP_404_NOT_FOUND)


class RoomBlockView(APIView):
    """Ендпоінт для блокування кімнати (тільки адміністратор)."""

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
        """Блокує кімнату за її ID.

        Args:
            request: HTTP-запит.
            room_id: Ідентифікатор кімнати.

        Returns:
            Response: Дані заблокованої кімнати або помилку.
        """
        service = LocationsService()
        try:
            room = service.block_room(request.user, room_id)
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND
            if str(exc) != "Кімнату з таким id не знайдено!":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=response_status)

        serializer = RoomBlockSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomUnblockView(APIView):
    """Ендпоінт для розблокування кімнати (тільки адміністратор)."""

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
        """Розблоковує кімнату за її ID.

        Args:
            request: HTTP-запит.
            room_id: Ідентифікатор кімнати.

        Returns:
            Response: Дані розблокованої кімнати або 404.
        """
        service = LocationsService()
        try:
            room = service.unblock_room(request.user, room_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoomBlockSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomUpdateView(APIView):
    """Ендпоінт для редагування та видалення кімнати (тільки адміністратор)."""

    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Редагування кімнати (лише адміністратор)",
        request=RoomUpdateSerializer,
        responses={200: RoomBlockSerializer},
    )
    def patch(self, request, room_id):
        """Оновлює параметри кімнати (назва, тип, місткість тощо).

        Args:
            request: HTTP-запит із частковими або повними даними для оновлення.
            room_id: Ідентифікатор кімнати.

        Returns:
            Response: Оновлені дані кімнати або помилку валідації.
        """
        serializer = RoomUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = LocationsService()
        try:
            room = service.update_room(request.user, room_id, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = RoomBlockSerializer(room, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Локації"],
        summary="Вилучення кімнати з активної мапи гуртожитку (лише адміністратор)",
        description=(
            "Видаляє кімнату з бази Campus Life, після чого відповідна зона SVG-мапи "
            "знову відображатиметься як така, що не належить гуртожитку. "
            "Кімнату можна вилучити лише після блокування."
        ),
        responses={
            204: OpenApiResponse(description="Кімнату вилучено з активної мапи гуртожитку."),
            400: OpenApiResponse(
                description="Кімнату не можна вилучити через поточний стан.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Потрібне блокування",
                        value={"detail": "Спочатку заблокуйте кімнату, а потім вилучайте її з гуртожитку."},
                    ),
                    OpenApiExample(
                        "Є мешканці",
                        value={"detail": "Не можна вилучити кімнату, доки до неї прикріплені мешканці."},
                    ),
                ],
            ),
            403: OpenApiResponse(description="Тільки адміністратор може вилучати кімнати з гуртожитку."),
            404: OpenApiResponse(
                description="Кімнату не знайдено.",
                response=dict,
                examples=[OpenApiExample("Кімната відсутня", value={"detail": "Кімнату з таким id не знайдено!"})],
            ),
        },
    )
    def delete(self, request, room_id):
        """Видаляє кімнату з активної мапи гуртожитку.

        Кімнату можна видалити лише після попереднього блокування та
        відсутності прикріплених мешканців.

        Args:
            request: HTTP-запит.
            room_id: Ідентифікатор кімнати.

        Returns:
            Response: 204 No Content або повідомлення про помилку.
        """
        service = LocationsService()
        try:
            service.delete_room(request.user, room_id)
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND
            if str(exc) != "Кімнату з таким id не знайдено!":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=response_status)

        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomCreateView(APIView):
    """Ендпоінт для підключення неактивної SVG-зони як кімнати (тільки адміністратор)."""

    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Підключення неактивної кімнати на мапі (лише адміністратор)",
        description=(
            "Створює кімнату на конкретному поверсі для SVG-зони, яка вже є на мапі, "
            "але ще не прив'язана до кімнати в базі. Після створення зона перестає "
            "бути сірою та стає доступною на мапі."
        ),
        request=RoomCreateSerializer,
        parameters=[
            OpenApiParameter(
                name="floor_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID поверху, на SVG-мапі якого є неактивна кімната.",
            )
        ],
        responses={
            201: OpenApiResponse(
                response=RoomMapSerializer,
                description="Кімнату успішно додано до гуртожитку.",
                examples=[
                    OpenApiExample(
                        "Створена кімната",
                        value={
                            "id": 201,
                            "name": "Кімната 1/1",
                            "room_type": "LIVING",
                            "max_person": 2,
                            "is_blocked": False,
                            "svg_element_id": "room_1",
                            "resources": [],
                            "current_users": [],
                            "active_events": [],
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Некоректні дані або SVG-зона вже використовується.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Зона вже активна",
                        value={"detail": "Ця зона мапи вже прив'язана до кімнати."},
                    ),
                    OpenApiExample(
                        "Зони немає в SVG",
                        value={"detail": "У SVG-мапі цього поверху немає такої кімнати."},
                    ),
                ],
            ),
            403: OpenApiResponse(description="Тільки адміністратор може додавати кімнати на мапу."),
            404: OpenApiResponse(
                description="Поверх не знайдено.",
                response=dict,
                examples=[OpenApiExample("Поверх відсутній", value={"detail": "Поверх з таким id не знайдено!"})],
            ),
        },
        examples=[
            OpenApiExample(
                "Додати кімнату з SVG",
                value={
                    "name": "Кімната 1/1",
                    "room_type": 1,
                    "max_person": 2,
                    "is_blocked": False,
                    "svg_element_id": "room_1",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request, floor_id):
        """Створює кімнату, прив'язуючи її до SVG-зони поверху.

        Args:
            request: HTTP-запит із даними нової кімнати.
            floor_id: Ідентифікатор поверху, де знаходиться SVG-зона.

        Returns:
            Response: Дані створеної кімнати або повідомлення про помилку.
        """
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = LocationsService()
        try:
            room = service.create_room(request.user, floor_id, serializer.validated_data)
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND
            if str(exc) != "Поверх з таким id не знайдено!":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=response_status)

        response_serializer = RoomMapSerializer(room, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ResourceCreateView(APIView):
    """Ендпоінт для створення ресурсу в кімнаті (тільки адміністратор)."""

    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Створення ресурсу в кімнаті (лише адміністратор)",
        request=ResourceCreateUpdateSerializer,
        responses={201: ResourceSerializer},
    )
    def post(self, request, room_id):
        """Створює новий ресурс (обладнання) у зазначеній кімнаті.

        Args:
            request: HTTP-запит із даними ресурсу.
            room_id: Ідентифікатор кімнати, до якої додається ресурс.

        Returns:
            Response: Дані створеного ресурсу або повідомлення про помилку.
        """
        serializer = ResourceCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = LocationsService()
        try:
            resource = service.create_resource(request.user, room_id, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ResourceSerializer(resource, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ResourceDetailView(APIView):
    """Ендпоінт для оновлення та видалення ресурсу (тільки адміністратор)."""

    permission_classes = [AdminPermission]

    @extend_schema(
        tags=["Локації"],
        summary="Оновлення ресурсу (лише адміністратор)",
        request=ResourceCreateUpdateSerializer,
        responses={200: ResourceSerializer},
    )
    def patch(self, request, resource_id):
        """Оновлює дані ресурсу.

        Args:
            request: HTTP-запит із частковими або повними даними ресурсу.
            resource_id: Ідентифікатор ресурсу.

        Returns:
            Response: Оновлені дані ресурсу або повідомлення про помилку.
        """
        serializer = ResourceCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = LocationsService()
        try:
            resource = service.update_resource(request.user, resource_id, serializer.validated_data)
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND
            if str(exc) != "Ресурс не знайдено!":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=response_status)

        response_serializer = ResourceSerializer(resource, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Локації"],
        summary="Видалення ресурсу (лише адміністратор)",
        responses={204: None},
    )
    def delete(self, request, resource_id):
        """Видаляє ресурс із кімнати.

        Args:
            request: HTTP-запит.
            resource_id: Ідентифікатор ресурсу.

        Returns:
            Response: 204 No Content або 404, якщо ресурс не знайдено.
        """
        service = LocationsService()
        try:
            service.delete_resource(request.user, resource_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


class FloorDetailView(APIView):
    """Детальні операції з поверхом."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Локації"],
        summary="Оновлення SVG-мапи поверху",
        description=(
            "Замінює SVG-мапу існуючого поверху без видалення кімнат. "
            "Нова мапа повинна містити всі id кімнат, які вже прив'язані до цього поверху."
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "map_file": {
                        "type": "string",
                        "format": "binary",
                        "description": "Новий SVG-файл мапи поверху.",
                    }
                },
                "required": ["map_file"],
            }
        },
        responses={
            200: OpenApiResponse(
                response=FloorListSerializer,
                description="Мапу поверху успішно оновлено.",
                examples=[
                    OpenApiExample(
                        "Оновлена мапа поверху",
                        value={"id": 5, "number": 9, "map_file": "/media/maps/floor_9_new.svg"},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Файл не передано, SVG некоректний або у новій мапі бракує id існуючих кімнат.",
                examples=[
                    OpenApiExample(
                        "Відсутній id кімнати",
                        value={
                            "detail": (
                                "Нова SVG-мапа не містить id для існуючих кімнат: 901 (room_901). "
                                "Через це ці кімнати перестали б бути клікабельними. "
                                "Збережіть ці id у новому SVG або спочатку вилучіть відповідні кімнати з гуртожитку."
                            )
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Не авторизовано."),
            403: OpenApiResponse(description="Оновлювати мапу поверху може лише адміністратор."),
        },
    )
    def patch(self, request, floor_id):
        if not request.user.is_admin:
            return Response(
                {"detail": "Лише адміністратор може оновлювати мапу поверху."},
                status=status.HTTP_403_FORBIDDEN,
            )
        map_file = request.FILES.get("map_file")
        if not map_file:
            return Response({"detail": "Завантажте SVG-файл мапи поверху."}, status=status.HTTP_400_BAD_REQUEST)
        if not map_file.name.lower().endswith(".svg"):
            return Response({"detail": "Мапа поверху має бути SVG-файлом."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = LocationsService()
            floor = service.update_floor_map(request.user, floor_id, map_file)
            serializer = FloorListSerializer(floor, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Локації"],
        summary="Видалення поверху",
        description="Видаляє поверх. Якщо на поверсі існують кімнати, видалення заборонено.",
        responses={
            204: OpenApiResponse(description="Успішно видалено."),
            400: OpenApiResponse(description="Неможливо видалити поверх (існують кімнати)."),
        },
    )
    def delete(self, request, floor_id):
        try:
            service = LocationsService()
            service.delete_floor(request.user, floor_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
