from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.bookings_serializer import (
    BookingCreateSerializer,
    BookingSerializer,
    ResourceBlockSerializer,
    ResourceScheduleSerializer,
    BookingUpdateSerializer,
)
from api.services.bookings_service import (
    BookingError,
    BookingNotFoundError,
    BookingPermissionDeniedError,
    BookingStatusNotFoundError,
    BookingsService,
)


def get_booking_error_status(error):
    if isinstance(error, BookingStatusNotFoundError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(error, BookingNotFoundError):
        return status.HTTP_404_NOT_FOUND

    if isinstance(error, BookingPermissionDeniedError):
        return status.HTTP_403_FORBIDDEN

    return status.HTTP_400_BAD_REQUEST


class ResourceScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Отримання розкладу ресурсу",
        parameters=[
            OpenApiParameter(
                name="resource_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID ресурсу, для якого потрібно отримати зайняті слоти.",
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location="query",
                required=False,
                description="Початкова дата у форматі YYYY-MM-DD (за замовчуванням сьогодні).",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location="query",
                required=False,
                description="Кінцева дата у форматі YYYY-MM-DD (за замовчуванням завтра).",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=ResourceScheduleSerializer(many=True),
                description="Зайняті слоти ресурсу на сьогодні та завтра отримано.",
                examples=[
                    OpenApiExample(
                        "Зайняті слоти ресурсу",
                        value=[
                            {
                                "booking_id": 17,
                                "start_time": "2026-05-23T18:00:00Z",
                                "end_time": "2026-05-23T19:00:00Z",
                                "status": "ACTIVE",
                            },
                            {
                                "booking_id": 18,
                                "start_time": "2026-05-24T09:00:00Z",
                                "end_time": "2026-05-24T10:00:00Z",
                                "status": "ACTIVE",
                            },
                        ],
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Ресурс не знайдено.",
                examples=[
                    OpenApiExample(
                        "Ресурс не знайдено",
                        value={"detail": "Ресурс з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request, resource_id):
        service = BookingsService()

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            bookings = service.get_resource_schedule(resource_id, start_date, end_date)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        serializer = ResourceScheduleSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Створення бронювання",
        request=BookingCreateSerializer,
        examples=[
            OpenApiExample(
                "Бронювання пральної машини",
                value={
                    "resource": 1,
                    "start_time": "2026-05-23T18:00:00Z",
                    "end_time": "2026-05-23T19:00:00Z",
                },
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=BookingSerializer,
                description="Бронювання успішно створено.",
                examples=[
                    OpenApiExample(
                        "Бронювання створено",
                        value={
                            "id": 17,
                            "user": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "resource_id": 1,
                            "resource_name": "Пральна машина 1",
                            "room_id": 5,
                            "room_name": "Пральня",
                            "floor_id": 3,
                            "start_time": "2026-05-23T18:00:00Z",
                            "end_time": "2026-05-23T19:00:00Z",
                            "status": "ACTIVE",
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=dict,
                description="Бронювання неможливо створити.",
                examples=[
                    OpenApiExample(
                        "Ресурс зайнятий",
                        value={"detail": "На цей час ресурс уже повністю зайнятий."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Ресурс заблокований",
                        value={"detail": "Цей ресурс заблокований і недоступний для бронювання."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Час у минулому",
                        value={"detail": "Не можна створити бронювання в минулому."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Некоректний час завершення",
                        value={"end_time": ["Час завершення має бути пізніше часу початку."]},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Завелика тривалість бронювання",
                        value={"end_time": ["Бронювання не може тривати довше 3 годин."]},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Ресурс не знайдено.",
                examples=[
                    OpenApiExample(
                        "Ресурс не знайдено",
                        value={"detail": "Ресурс з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BookingsService()

        try:
            booking = service.create_booking(request.user, serializer.validated_data)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        response_serializer = BookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Отримання моїх актуальних бронювань",
        responses={
            200: OpenApiResponse(
                response=BookingSerializer(many=True),
                description="Майбутні та поточні активні або скасовані бронювання користувача отримано.",
                examples=[
                    OpenApiExample(
                        "Мої актуальні бронювання",
                        value=[
                            {
                                "id": 17,
                                "user": {
                                    "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                    "display_name": "Богдан Змеул",
                                    "photo": "/media/avatars/bogdan.jpg",
                                },
                                "resource_id": 1,
                                "resource_name": "Пральна машина 1",
                                "room_id": 5,
                                "room_name": "Пральня",
                                "floor_id": 3,
                                "start_time": "2026-05-23T18:00:00Z",
                                "end_time": "2026-05-23T19:00:00Z",
                                "status": "ACTIVE",
                            },
                            {
                                "id": 18,
                                "user": {
                                    "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                    "display_name": "Богдан Змеул",
                                    "photo": "/media/avatars/bogdan.jpg",
                                },
                                "resource_id": 1,
                                "resource_name": "Пральна машина 1",
                                "room_id": 5,
                                "room_name": "Пральня",
                                "floor_id": 3,
                                "start_time": "2026-05-24T11:00:00Z",
                                "end_time": "2026-05-24T12:00:00Z",
                                "status": "CANCELLED",
                            },
                        ],
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request):
        service = BookingsService()
        bookings = service.get_my_bookings(request.user)
        serializer = BookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Скасування бронювання",
        request=None,
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID бронювання, яке потрібно скасувати.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=BookingSerializer,
                description="Бронювання скасовано.",
                examples=[
                    OpenApiExample(
                        "Бронювання скасовано",
                        value={
                            "id": 17,
                            "user": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "resource_id": 1,
                            "resource_name": "Пральна машина 1",
                            "room_id": 5,
                            "room_name": "Пральня",
                            "floor_id": 3,
                            "start_time": "2026-05-23T18:00:00Z",
                            "end_time": "2026-05-23T19:00:00Z",
                            "status": "CANCELLED",
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для скасування бронювання.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "У вас немає прав для скасування цього бронювання."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Бронювання не знайдено.",
                examples=[
                    OpenApiExample(
                        "Бронювання не знайдено",
                        value={"detail": "Бронювання з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def patch(self, request, booking_id):
        service = BookingsService()

        try:
            booking = service.cancel_booking(request.user, booking_id)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        serializer = BookingSerializer(booking, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceBlockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Блокування ресурсу",
        request=None,
        parameters=[
            OpenApiParameter(
                name="resource_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID ресурсу, який адміністратор блокує для бронювань.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Ресурс заблоковано.",
                examples=[
                    OpenApiExample(
                        "Ресурс заблоковано",
                        value={
                            "resource": {
                                "id": 1,
                                "name": "Пральна машина 1",
                                "room_id": 5,
                                "room_name": "Пральня",
                                "max_person": 1,
                                "is_blocked": True,
                            },
                            "cancelled_bookings_count": 2,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Тільки адміністратор може блокувати ресурси.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "Тільки адміністратор може блокувати ресурси."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Ресурс не знайдено.",
                examples=[
                    OpenApiExample(
                        "Ресурс не знайдено",
                        value={"detail": "Ресурс з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def patch(self, request, resource_id):
        service = BookingsService()

        try:
            resource, cancelled_count = service.block_resource(request.user, resource_id)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        serializer = ResourceBlockSerializer(resource, context={"request": request})
        return Response(
            {
                "resource": serializer.data,
                "cancelled_bookings_count": cancelled_count,
            },
            status=status.HTTP_200_OK,
        )


class ResourceUnblockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Розблокування ресурсу",
        request=None,
        parameters=[
            OpenApiParameter(
                name="resource_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID ресурсу, який адміністратор знову відкриває для бронювань.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ResourceBlockSerializer,
                description="Ресурс розблоковано.",
                examples=[
                    OpenApiExample(
                        "Ресурс розблоковано",
                        value={
                            "id": 1,
                            "name": "Пральна машина 1",
                            "room_id": 5,
                            "room_name": "Пральня",
                            "max_person": 1,
                            "is_blocked": False,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Тільки адміністратор може розблоковувати ресурси.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "Тільки адміністратор може розблоковувати ресурси."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Ресурс не знайдено.",
                examples=[
                    OpenApiExample(
                        "Ресурс не знайдено",
                        value={"detail": "Ресурс з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def patch(self, request, resource_id):
        service = BookingsService()

        try:
            resource = service.unblock_resource(request.user, resource_id)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        serializer = ResourceBlockSerializer(resource, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Редагування часу бронювання",
        description=(
            "Ендпоінт для перенесення існуючого бронювання на інший час. "
            "Перевіряє, чи не перекривається новий час із бронями інших користувачів "
            "(при цьому ігнорує поточний час самої броні, яку ми переносимо)."
        ),
        request=BookingUpdateSerializer,
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID бронювання, час якого потрібно змінити.",
            )
        ],
        examples=[
            OpenApiExample(
                "Новий час для бронювання",
                value={
                    "start_time": "2026-05-23T19:00:00Z",
                    "end_time": "2026-05-23T20:30:00Z",
                },
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=BookingSerializer,
                description="Час бронювання успішно оновлено.",
                examples=[
                    OpenApiExample(
                        "Бронювання оновлено",
                        value={
                            "id": 17,
                            "user": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "resource_id": 1,
                            "resource_name": "Пральна машина 1",
                            "room_id": 5,
                            "room_name": "Пральня",
                            "floor_id": 3,
                            "start_time": "2026-05-23T19:00:00Z",
                            "end_time": "2026-05-23T20:30:00Z",
                            "status": "ACTIVE",
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=dict,
                description="Помилка валідації або бізнес-логіки.",
                examples=[
                    OpenApiExample(
                        "Ресурс зайнятий",
                        value={"detail": "На обраний час ресурс уже повністю зайнятий кимось іншим."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Ресурс заблокований",
                        value={"detail": "Цей ресурс наразі заблокований."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Бронювання не активне",
                        value={"detail": "Редагувати можна лише активні бронювання."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Завелика тривалість",
                        value={"end_time": ["Бронювання не може тривати довше 3 годин."]},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Перенесення в минуле",
                        value={"start_time": ["Не можна перенести бронювання на минулий час."]},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для редагування.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "У вас немає прав для редагування цього бронювання."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Бронювання не знайдено.",
                examples=[
                    OpenApiExample(
                        "Бронювання не знайдено",
                        value={"detail": "Бронювання з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def patch(self, request, booking_id):
        serializer = BookingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BookingsService()

        try:
            booking = service.update_booking_time(request.user, booking_id, serializer.validated_data)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        response_serializer = BookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Отримання деталей бронювання",
        description=(
            "Повертає детальну інформацію про конкретне бронювання за його ID. "
            "Включає дані про час, статус, ресурс (локацію) та користувача, який його створив."
        ),
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID бронювання, деталі якого потрібно отримати.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=BookingSerializer,
                description="Деталі бронювання успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Деталі бронювання",
                        value={
                            "id": 17,
                            "user": {
                                "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                "display_name": "Богдан Змеул",
                                "photo": "/media/avatars/bogdan.jpg",
                            },
                            "resource_id": 1,
                            "resource_name": "Пральна машина 1",
                            "room_id": 5,
                            "room_name": "Пральня",
                            "floor_id": 3,
                            "start_time": "2026-05-23T18:00:00Z",
                            "end_time": "2026-05-23T19:00:00Z",
                            "status": "ACTIVE",
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Бронювання не знайдено.",
                examples=[
                    OpenApiExample(
                        "Бронювання не знайдено",
                        value={"detail": "Бронювання з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def get(self, request, booking_id):
        service = BookingsService()

        try:
            booking = service.get_booking(booking_id)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(exc))

        serializer = BookingSerializer(booking, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
