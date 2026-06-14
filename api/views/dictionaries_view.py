from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from django.db.models import Count
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from api.models import Faculty, Major, Role, TargetType, Room, Floor, Dormitory, Resource
from api.serializers.dictionaries_serializers import (
    FacultyListSerializer,
    MajorListSerializer,
    RoleListSerializer,
    TargetTypeListSerializer,
    RoomListSerializer,
    FloorListSerializer,
    DormitoryListSerializer,
    RoomTypeListSerializer,
    ResourceTypeListSerializer,
)


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх факультетів",
    description="Повертає повний список факультетів (без пагінації) у вигляді масиву. "
    "Ідеально підходить для заповнення випадаючих списків (dropdown) на фронтенді.",
    responses={
        200: OpenApiResponse(
            response=FacultyListSerializer(many=True),
            description="Успішне отримання списку факультетів",
            examples=[
                OpenApiExample(
                    name="Список факультетів",
                    value=[
                        {"id": 1, "name": "Факультет інформатики"},
                        {"id": 2, "name": "Факультет гуманітарних наук"},
                        {"id": 3, "name": "Економічний факультет"},
                    ],
                )
            ],
        ),
        401: OpenApiResponse(
            description="Не авторизовано (відсутній або недійсний токен).",
            response=dict,
            examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!"})],
        ),
    },
)
class FacultyListView(generics.ListAPIView):
    """Представлення для виведення списку факультетів."""

    queryset = Faculty.objects.all().order_by("name")
    serializer_class = FacultyListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх спеціальностей",
    description="Повертає повний список спеціальностей (без пагінації) у вигляді масиву. "
    "Використовується для вибору спеціальності при реєстрації або редагуванні профілю.",
    responses={
        200: OpenApiResponse(
            response=MajorListSerializer(many=True),
            description="Успішне отримання списку спеціальностей",
            examples=[
                OpenApiExample(
                    name="Список спеціальностей",
                    value=[
                        {"id": 1, "name": "Інженерія програмного забезпечення"},
                        {"id": 2, "name": "Комп'ютерні науки"},
                        {"id": 3, "name": "Кібербезпека"},
                    ],
                )
            ],
        ),
        401: OpenApiResponse(
            description="Не авторизовано (відсутній або недійсний токен).",
            response=dict,
            examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!"})],
        ),
    },
)
class MajorListView(generics.ListAPIView):
    """Представлення для виведення списку спеціальностей."""

    queryset = Major.objects.all().order_by("faculty_id", "name")
    serializer_class = MajorListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх ролей",
    description="Повертає повний список доступних системних ролей (без пагінації). "
    "Може використовуватися адміністраторами для призначення нових ролей користувачам.",
    responses={
        200: OpenApiResponse(
            response=RoleListSerializer(many=True),
            description="Успішне отримання списку ролей",
            examples=[
                OpenApiExample(
                    name="Список ролей",
                    value=[{"id": 1, "name": "ADMIN"}, {"id": 2, "name": "MODERATOR"}, {"id": 3, "name": "RESIDENT"}],
                )
            ],
        ),
        401: OpenApiResponse(
            description="Не авторизовано (відсутній або недійсний токен).",
            response=dict,
            examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!"})],
        ),
    },
)
class RoleListView(generics.ListAPIView):
    """Представлення для виведення списку ролей користувачів."""

    queryset = Role.objects.all().order_by("id")
    serializer_class = RoleListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати типи аудиторії оголошень",
    description="Повертає доступні значення цільової аудиторії (target_type) для створення оголошень (без пагінації).",
    responses={
        200: OpenApiResponse(
            response=TargetTypeListSerializer(many=True),
            description="Успішне отримання типів аудиторії",
            examples=[
                OpenApiExample(
                    name="Типи аудиторії",
                    value=[
                        {"id": 1, "type": "GLOBAL"},
                        {"id": 2, "type": "FLOOR"},
                        {"id": 3, "type": "ROOM"},
                        {"id": 4, "type": "SPECIFIC_USERS"},
                    ],
                )
            ],
        ),
        401: OpenApiResponse(
            description="Не авторизовано (відсутній або недійсний токен).",
            response=dict,
            examples=[OpenApiExample("Помилка", value={"detail": "Authentication credentials were not provided."})],
        ),
    },
)
class TargetTypeListView(generics.ListAPIView):
    """Представлення для виведення списку типів цілей оголошень."""

    queryset = TargetType.objects.all().order_by("id")
    serializer_class = TargetTypeListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх гуртожитків",
    description="Повертає повний список гуртожитків (без пагінації) для вибору локації.",
    responses={
        200: OpenApiResponse(
            response=DormitoryListSerializer(many=True),
            description="Успішне отримання списку гуртожитків",
            examples=[
                OpenApiExample(
                    name="Список гуртожитків", value=[{"id": 1, "name": "Гуртожиток №3"}, {"id": 2, "name": "Маккейна"}]
                )
            ],
        ),
        401: OpenApiResponse(description="Не авторизовано."),
    },
)
class DormitoryListView(generics.ListAPIView):
    """Представлення для виведення списку гуртожитків."""

    queryset = Dormitory.objects.all().order_by("name")
    serializer_class = DormitoryListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх поверхів",
    description="Повертає повний список поверхів. "
    "Містить поле dormitory для фільтрації поверхів конкретного гуртожитку на фронтенді.",
    responses={
        200: OpenApiResponse(
            response=FloorListSerializer(many=True),
            description="Успішне отримання списку поверхів",
            examples=[
                OpenApiExample(
                    name="Список поверхів",
                    value=[
                        {"id": 1, "number": 1, "dormitory": 1},
                        {"id": 2, "number": 2, "dormitory": 1},
                        {"id": 3, "number": 1, "dormitory": 2},
                    ],
                )
            ],
        ),
        401: OpenApiResponse(description="Не авторизовано."),
    },
)
class FloorListView(generics.ListAPIView):
    """Представлення для виведення списку поверхів гуртожитків."""

    queryset = Floor.objects.all().order_by("dormitory_id", "number")
    serializer_class = FloorListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список усіх кімнат",
    description="Повертає список кімнат (без пагінації). "
    "Містить поле floor для прив'язки кімнати до конкретного поверху.",
    responses={
        200: OpenApiResponse(
            response=RoomListSerializer(many=True),
            description="Успішне отримання списку кімнат",
            examples=[
                OpenApiExample(
                    name="Список кімнат",
                    value=[{"id": 1, "name": "314", "floor": 1}, {"id": 2, "name": "Кухня лівого крила", "floor": 1}],
                )
            ],
        ),
        401: OpenApiResponse(description="Не авторизовано."),
    },
)
class RoomListView(generics.ListAPIView):
    """Представлення для виведення списку кімнат з підрахунком мешканців."""

    queryset = (
        Room.objects.select_related("floor", "room_type")
        .annotate(current_residents_count=Count("user"))
        .all()
        .order_by("floor_id", "name")
    )
    serializer_class = RoomListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список типів кімнат",
    responses={200: RoomTypeListSerializer(many=True)},
)
class RoomTypeListView(generics.ListAPIView):
    """Представлення для виведення списку типів приміщень."""

    queryset = Room.room_type.field.related_model.objects.all().order_by("id")
    serializer_class = RoomTypeListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(
    tags=["Довідники"],
    summary="Отримати список типів ресурсів",
    responses={200: ResourceTypeListSerializer(many=True)},
)
class ResourceTypeListView(generics.ListAPIView):
    """Представлення для виведення списку типів інвентарю/ресурсів."""

    queryset = Resource.resource_type.field.related_model.objects.all().order_by("id")
    serializer_class = ResourceTypeListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
