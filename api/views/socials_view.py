from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.socials_serializer import (
    SocialEventCreateSerializer,
    SocialEventDetailSerializer,
    SocialEventFullDetailSerializer,
    SocialSharingRequestCreateSerializer,
    SocialSharingRequestDetailSerializer,
    SocialEventFeedSerializer,
    SocialSharingRequestFeedSerializer,
)
from api.services.socials_service import (
    SocialAccessDeniedError,
    SocialError,
    SocialEventFullError,
    SocialEventUnavailableError,
    SocialNotFoundError,
    SocialPermissionDeniedError,
    SocialStatusNotFoundError,
    SocialsService,
)


def get_social_error_status(exc):
    if isinstance(exc, SocialStatusNotFoundError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, SocialNotFoundError):
        return status.HTTP_404_NOT_FOUND

    if isinstance(exc, (SocialAccessDeniedError, SocialPermissionDeniedError)):
        return status.HTTP_403_FORBIDDEN

    if isinstance(exc, (SocialEventFullError, SocialEventUnavailableError)):
        return status.HTTP_400_BAD_REQUEST

    return status.HTTP_400_BAD_REQUEST


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Отримання соціальної стрічки з фільтрацією та сортуванням",
        description=(
            "Повертає об'єднану стрічку подій та запитів на шеринг. "
            "Підтримує фільтрацію за типами сутностей, датами, поверхами та станом активності."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="Номер сторінки стрічки",
            ),
            OpenApiParameter(
                name="item_type",
                type=OpenApiTypes.STR,
                location="query",
                required=False,
                enum=["all", "event", "sharing_request"],
                default="all",
                description="Фільтр типу карток: тільки події, тільки шеринг або все разом.",
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location="query",
                required=False,
                description="Початкова дата діапазону (YYYY-MM-DD). Працює тільки якщо item_type = 'event' або 'all'.",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location="query",
                required=False,
                description="Кінцева дата діапазону (YYYY-MM-DD). Працює тільки якщо item_type = 'event' або 'all'.",
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location="query",
                required=False,
                description="Якщо true — повертає тільки ті івенти,"
                "які проходять прямо зараз (start_time <= NOW <= end_time).",
            ),
            OpenApiParameter(
                name="floor_id",
                type=OpenApiTypes.STR,
                location="query",
                required=False,
                description="Фільтр по поверху."
                "Передайте ID конкретного поверху або рядок 'my' для динамічного фільтру по поверху поточного юзера.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location="query",
                required=False,
                enum=["created_at", "start_time"],
                default="created_at",
                description="Сортування: 'created_at' (нові згори) або 'start_time' (найближчі івенти згори).",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Сторінку стрічки успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Сторінка соціальної стрічки",
                        value={
                            "page": 1,
                            "page_size": 20,
                            "has_next": False,
                            "results": [
                                {
                                    "type": "event",
                                    "id": 12,
                                    "title": "Граємо в Мафію",
                                    "start_time": "2026-05-23T20:00:00Z",
                                    "creator": {
                                        "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                        "display_name": "Богдан Змеул",
                                        "photo": "/media/avatars/bogdan.jpg",
                                    },
                                    "is_faculty_only": False,
                                    "is_major_only": False,
                                },
                                {
                                    "type": "sharing_request",
                                    "id": 7,
                                    "title": "Позичте зарядку для ноутбука",
                                    "status": "ACTIVE",
                                    "created_at": "2026-05-23T18:10:00Z",
                                    "creator": {
                                        "id": "6a6d7bb9-9210-4f62-a5df-c7c9d2c6f9a1",
                                        "display_name": "Олена Петренко",
                                        "photo": None,
                                    },
                                },
                            ],
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request, page):
        filters = {
            "item_type": request.query_params.get("item_type", "all"),
            "start_date": request.query_params.get("start_date"),
            "end_date": request.query_params.get("end_date"),
            "is_active": request.query_params.get("is_active") == "true",
            "floor_id": request.query_params.get("floor_id"),
            "ordering": request.query_params.get("ordering", "created_at"),
        }

        service = SocialsService()
        feed = service.get_feed(request.user, page, filters)

        results = []
        for _, item_type, item in feed["items"]:
            if item_type == "event":
                results.append(SocialEventFeedSerializer(item, context={"request": request}).data)
            else:
                results.append(SocialSharingRequestFeedSerializer(item, context={"request": request}).data)

        return Response(
            {
                "page": feed["page"],
                "page_size": feed["page_size"],
                "has_next": feed["has_next"],
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


class SocialEventCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Створення події",
        request=SocialEventCreateSerializer,
        examples=[
            OpenApiExample(
                "Подія в кімнаті",
                value={
                    "title": "Граємо в Мафію",
                    "description": "Збираємось у спільній кімнаті, новачкам усе пояснимо.",
                    "start_time": "2026-05-23T20:00:00Z",
                    "end_time": "2026-05-23T22:00:00Z",
                    "max_person": 8,
                    "is_faculty_only": False,
                    "is_major_only": False,
                    "room": 5,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Подія на поверсі",
                value={
                    "title": "Кіновечір на поверсі",
                    "description": "Дивимось фільм у холі.",
                    "start_time": "2026-05-24T19:00:00Z",
                    "end_time": "2026-05-24T21:30:00Z",
                    "max_person": 0,
                    "is_faculty_only": False,
                    "is_major_only": False,
                    "floor": 3,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Подія з довільною локацією",
                value={
                    "title": "Пробіжка біля гуртожитку",
                    "description": "Стартуємо біля входу.",
                    "start_time": "2026-05-25T07:30:00Z",
                    "end_time": "2026-05-25T08:30:00Z",
                    "max_person": 10,
                    "is_faculty_only": False,
                    "is_major_only": False,
                    "custom_location": "Біля головного входу",
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(response=SocialEventDetailSerializer, description="Подію успішно створено."),
            400: OpenApiResponse(
                response=dict,
                description="Помилка валідації даних.",
                examples=[
                    OpenApiExample(
                        "Локацію не вказано",
                        value={"detail": "Вкажіть хоча б одну локацію: кімнату, поверх або текстову назву місця."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Некоректний час завершення",
                        value={"end_time": ["Час завершення має бути пізніше часу початку."]},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def post(self, request):
        serializer = SocialEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SocialsService()
        event = service.create_event(request.user, serializer.validated_data)
        response_serializer = SocialEventDetailSerializer(event, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SocialEventJoinView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Приєднання до події",
        request=None,
        parameters=[
            OpenApiParameter(
                name="event_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID події, до якої потрібно приєднати поточного користувача.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialEventDetailSerializer,
                description="Користувача додано до події.",
                examples=[
                    OpenApiExample(
                        "Користувача додано до події",
                        value={
                            "type": "event",
                            "id": 12,
                            "title": "Граємо в Мафію",
                            "description": "Збираємось у спільній кімнаті.",
                            "start_time": "2026-05-23T20:00:00Z",
                            "end_time": "2026-05-23T22:00:00Z",
                            "created_at": "2026-05-21T15:30:00Z",
                            "max_person": 8,
                            "is_faculty_only": False,
                            "is_major_only": False,
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "participants_count": 4,
                            "room_id": 5,
                            "room_name": "Спільна кімната",
                            "floor_id": 3,
                            "custom_location": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=dict,
                description="Приєднатися до події неможливо.",
                examples=[
                    OpenApiExample(
                        "Немає вільних місць",
                        value={"detail": "На цю подію вже немає вільних місць."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Подія завершилася",
                        value={"detail": "Неможливо приєднатися до події, яка вже завершилася."},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Подія недоступна цьому користувачу.",
                examples=[
                    OpenApiExample(
                        "Немає доступу",
                        value={"detail": "Ви не маєте доступу до цієї події."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Подію не знайдено.",
                examples=[
                    OpenApiExample(
                        "Подію не знайдено",
                        value={"detail": "Подію з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def post(self, request, event_id):
        service = SocialsService()

        try:
            event = service.join_event(request.user, event_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialEventDetailSerializer(event, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialEventLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Вихід з події",
        request=None,
        parameters=[
            OpenApiParameter(
                name="event_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID події, з якої потрібно прибрати поточного користувача.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialEventDetailSerializer,
                description="Користувача прибрано з події.",
                examples=[
                    OpenApiExample(
                        "Користувача прибрано з події",
                        value={
                            "type": "event",
                            "id": 12,
                            "title": "Граємо в Мафію",
                            "description": "Збираємось у спільній кімнаті.",
                            "start_time": "2026-05-23T20:00:00Z",
                            "end_time": "2026-05-23T22:00:00Z",
                            "created_at": "2026-05-21T15:30:00Z",
                            "max_person": 8,
                            "is_faculty_only": False,
                            "is_major_only": False,
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "participants_count": 3,
                            "room_id": 5,
                            "room_name": "Спільна кімната",
                            "floor_id": 3,
                            "custom_location": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Подію не знайдено.",
                examples=[
                    OpenApiExample(
                        "Подію не знайдено",
                        value={"detail": "Подію з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def post(self, request, event_id):
        service = SocialsService()

        try:
            event = service.leave_event(request.user, event_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialEventDetailSerializer(event, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialEventDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Отримання детальної інформації про подію",
        parameters=[
            OpenApiParameter(
                name="event_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID події, для якої потрібно отримати повну інформацію.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialEventFullDetailSerializer,
                description="Детальну інформацію про подію успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Детальна інформація про подію",
                        value={
                            "type": "event",
                            "id": 12,
                            "title": "Граємо в Мафію",
                            "description": "Збираємось у спільній кімнаті, новачкам усе пояснимо на місці.",
                            "start_time": "2026-05-23T20:00:00Z",
                            "end_time": "2026-05-23T22:00:00Z",
                            "created_at": "2026-05-21T15:30:00Z",
                            "max_person": 8,
                            "is_faculty_only": False,
                            "is_major_only": False,
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "room_id": 5,
                            "room_name": "Спільна кімната",
                            "floor_id": 3,
                            "custom_location": None,
                            "participants": [
                                {
                                    "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                    "display_name": "Богдан Змеул",
                                    "photo": "/media/avatars/bogdan.jpg",
                                },
                                {
                                    "id": "6a6d7bb9-9210-4f62-a5df-c7c9d2c6f9a1",
                                    "display_name": "Олена Петренко",
                                    "photo": None,
                                },
                            ],
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Подія недоступна цьому користувачу.",
                examples=[
                    OpenApiExample(
                        "Подія недоступна",
                        value={"detail": "Ви не маєте доступу до цієї події."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Подію не знайдено.",
                examples=[
                    OpenApiExample(
                        "Подію не знайдено",
                        value={"detail": "Подію з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request, event_id):
        service = SocialsService()

        try:
            event = service.get_event_detail(request.user, event_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialEventFullDetailSerializer(event, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Видалення події",
        parameters=[
            OpenApiParameter(
                name="event_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID події, яку потрібно видалити.",
            )
        ],
        responses={
            204: OpenApiResponse(description="Подію видалено."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для видалення події.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "Ви не маєте прав для видалення цієї події."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Подію не знайдено.",
                examples=[
                    OpenApiExample(
                        "Подію не знайдено",
                        value={"detail": "Подію з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def delete(self, request, event_id):
        service = SocialsService()

        try:
            service.delete_event(request.user, event_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialSharingRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Створення запиту на шеринг",
        request=SocialSharingRequestCreateSerializer,
        examples=[
            OpenApiExample(
                "Запит на шеринг",
                value={"title": "Позичте зарядку для ноутбука на дві години"},
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Запит на шеринг успішно створено.",
                examples=[
                    OpenApiExample(
                        "Запит на шеринг створено",
                        value={
                            "type": "sharing_request",
                            "id": 7,
                            "title": "Позичте зарядку для ноутбука на дві години",
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "status": "ACTIVE",
                            "created_at": "2026-05-23T18:10:00Z",
                            "floor_id": 3,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=dict,
                description="Помилка валідації даних.",
                examples=[
                    OpenApiExample(
                        "Порожній заголовок",
                        value={"title": ["Це поле не може бути порожнім."]},
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            500: OpenApiResponse(
                response=dict,
                description="У базі відсутній потрібний статус запиту.",
                examples=[
                    OpenApiExample(
                        "Статус відсутній",
                        value={"detail": "Статус ACTIVE не знайдено в базі даних."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = SocialSharingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SocialsService()

        try:
            sharing_request = service.create_sharing_request(request.user, serializer.validated_data)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        response_serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SocialSharingRequestDoneView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Завершення запиту на шеринг",
        request=None,
        parameters=[
            OpenApiParameter(
                name="request_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID запиту на шеринг, який потрібно завершити.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Запит на шеринг завершено.",
                examples=[
                    OpenApiExample(
                        "Запит на шеринг завершено",
                        value={
                            "type": "sharing_request",
                            "id": 7,
                            "title": "Позичте зарядку для ноутбука на дві години",
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "status": "COMPLETED",
                            "created_at": "2026-05-23T18:10:00Z",
                            "floor_id": 3,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для завершення запиту.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "Ви не маєте прав для завершення цього запиту."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Запит на шеринг не знайдено.",
                examples=[
                    OpenApiExample(
                        "Запит не знайдено",
                        value={"detail": "Запит на шеринг з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
            500: OpenApiResponse(
                response=dict,
                description="У базі відсутній потрібний статус запиту.",
                examples=[
                    OpenApiExample(
                        "Статус відсутній",
                        value={"detail": "Статус COMPLETED не знайдено в базі даних."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def patch(self, request, request_id):
        service = SocialsService()

        try:
            sharing_request = service.complete_sharing_request(request.user, request_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialSharingRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Видалення запиту на шеринг",
        parameters=[
            OpenApiParameter(
                name="request_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID запиту на шеринг, який потрібно скасувати.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Запит на шеринг скасовано.",
                examples=[
                    OpenApiExample(
                        "Запит на шеринг скасовано",
                        value={
                            "type": "sharing_request",
                            "id": 7,
                            "title": "Позичте зарядку для ноутбука на дві години",
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "status": "CANCELLED",
                            "created_at": "2026-05-23T18:10:00Z",
                            "floor_id": 3,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для видалення запиту.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "Ви не маєте прав для видалення цього запиту."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Запит на шеринг не знайдено.",
                examples=[
                    OpenApiExample(
                        "Запит не знайдено",
                        value={"detail": "Запит на шеринг з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
            500: OpenApiResponse(
                response=dict,
                description="У базі відсутній потрібний статус запиту.",
                examples=[
                    OpenApiExample(
                        "Статус відсутній",
                        value={"detail": "Статус CANCELLED не знайдено в базі даних."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def delete(self, request, request_id):
        service = SocialsService()

        try:
            sharing_request = service.delete_sharing_request(request.user, request_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Отримання детальної інформації про запит на шеринг",
        description="Повертає повну інформацію про конкретний запит на шеринг за його ID.",
        parameters=[
            OpenApiParameter(
                name="request_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID запиту на шеринг, який потрібно отримати.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Детальну інформацію про запит успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Деталі запиту на шеринг",
                        value={
                            "type": "sharing_request",
                            "id": 7,
                            "title": "Позичте зарядку для ноутбука на дві години",
                            "creator": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "status": "ACTIVE",
                            "created_at": "2026-05-23T18:10:00Z",
                            "floor_id": 3,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Запит на шеринг не знайдено.",
                examples=[
                    OpenApiExample(
                        "Запит не знайдено",
                        value={"detail": "Запит на шеринг з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request, request_id):
        service = SocialsService()

        try:
            sharing_request = service.get_sharing_request_detail(request.user, request_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSocialProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Отримання соціальної активності користувача",
        description=(
            "Повертає три списки для сторінки профілю користувача: його запити на шеринг, "
            "створені ним події та актуальні події, в яких він планує взяти участь (end_time > now). "
            "Усі події фільтруються з урахуванням прав доступу користувача, який робить запит."
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.UUID,
                location="path",
                required=True,
                description="ID користувача, активність якого потрібно отримати.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Профіль успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Активність користувача",
                        value={
                            "sharing_requests": [
                                {
                                    "type": "sharing_request",
                                    "id": 7,
                                    "title": "Позичте зарядку для ноутбука",
                                    "status": "ACTIVE",
                                    "created_at": "2026-05-23T18:10:00Z",
                                    "creator": {
                                        "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                        "display_name": "Богдан Змеул",
                                        "photo": None
                                    }
                                }
                            ],
                            "created_events": [
                                {
                                    "type": "event",
                                    "id": 12,
                                    "title": "Граємо в Мафію",
                                    "start_time": "2026-05-23T20:00:00Z",
                                    "creator": {
                                        "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                        "display_name": "Богдан Змеул",
                                        "photo": None
                                    },
                                    "is_faculty_only": False,
                                    "is_major_only": False
                                }
                            ],
                            "participating_events": []
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(description="Користувача не знайдено.")
        }
    )
    def get(self, request, user_id):
        service = SocialsService()

        try:
            activity = service.get_user_social_profile(request.user, user_id)
        except SocialError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(exc))

        return Response(
            {
                "sharing_requests": SocialSharingRequestFeedSerializer(
                    activity["sharing_requests"], many=True, context={"request": request}
                ).data,
                "created_events": SocialEventFeedSerializer(
                    activity["created_events"], many=True, context={"request": request}
                ).data,
                "participating_events": SocialEventFeedSerializer(
                    activity["participating_events"], many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )
