from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.announcements_serializer import (
    AnnouncementCreateSerializer,
    AnnouncementSerializer,
)
from api.services.announcements_service import (
    AnnouncementEmailSendError,
    AnnouncementError,
    AnnouncementNotFoundError,
    AnnouncementPermissionDeniedError,
    AnnouncementsService,
)


def get_announcement_error_status(error):
    if isinstance(error, AnnouncementEmailSendError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(error, AnnouncementNotFoundError):
        return status.HTTP_404_NOT_FOUND

    if isinstance(error, AnnouncementPermissionDeniedError):
        return status.HTTP_403_FORBIDDEN

    return status.HTTP_400_BAD_REQUEST


class ActiveAnnouncementsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Оголошення"],
        summary="Отримання активних оголошень",
        responses={
            200: OpenApiResponse(
                response=AnnouncementSerializer(many=True),
                description="Активні оголошення отримано.",
                examples=[
                    OpenApiExample(
                        "Активні оголошення",
                        value=[
                            {
                                "id": 4,
                                "title": "Відключення води",
                                "message": "Сьогодні з 14:00 до 16:00 не буде гарячої води.",
                                "creator": {
                                    "id": "0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74",
                                    "display_name": "Адміністрація гуртожитку",
                                    "photo": None,
                                },
                                "target_type": "GLOBAL",
                                "target_floor_id": None,
                                "target_room_id": None,
                                "target_user_ids": [],
                                "created_at": "2026-05-23T09:00:00Z",
                                "expires_at": "2026-05-23T16:00:00Z",
                                "is_pinned": True,
                            }
                        ],
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request):
        service = AnnouncementsService()
        announcements = service.get_active_announcements(request.user)
        serializer = AnnouncementSerializer(announcements, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnnouncementReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Оголошення"],
        summary="Позначити оголошення як прочитане",
        request=None,
        parameters=[
            OpenApiParameter(
                name="announcement_id",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="ID оголошення, яке поточний користувач позначає як прочитане.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Оголошення позначено як прочитане.",
                examples=[
                    OpenApiExample(
                        "Успішна відповідь",
                        value={"detail": "Оголошення позначено як прочитане."},
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(
                response=dict,
                description="Оголошення не призначене для цього користувача.",
                examples=[
                    OpenApiExample(
                        "Оголошення не призначене",
                        value={"detail": "Це оголошення не призначене для вас."},
                        response_only=True,
                    )
                ],
            ),
            404: OpenApiResponse(
                response=dict,
                description="Оголошення не знайдено.",
                examples=[
                    OpenApiExample(
                        "Оголошення не знайдено",
                        value={"detail": "Оголошення з таким id не знайдено."},
                        response_only=True,
                    )
                ],
            ),
        },
    )
    def post(self, request, announcement_id):
        service = AnnouncementsService()

        try:
            service.mark_as_read(request.user, announcement_id)
        except AnnouncementError as exc:
            return Response({"detail": str(exc)}, status=get_announcement_error_status(exc))

        return Response({"detail": "Оголошення позначено як прочитане."}, status=status.HTTP_200_OK)


class AnnouncementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Оголошення"],
        summary="Створення оголошення",
        description=(
            "Створює оголошення в системі та синхронно надсилає один email-лист усім отримувачам, "
            "які відповідають обраному target_type. Створення оголошення і надсилання листа виконуються "
            "в одній DB-транзакції: якщо email не вдалося надіслати, оголошення не зберігається. "
            "У email-розсилку потрапляють лише користувачі з is_activated=True та непорожньою email-адресою."
        ),
        request=AnnouncementCreateSerializer,
        examples=[
            OpenApiExample(
                "Глобальне оголошення",
                value={
                    "title": "Відключення води",
                    "message": "Сьогодні з 14:00 до 16:00 не буде гарячої води.",
                    "target_type": "GLOBAL",
                    "expires_at": "2026-05-23T16:00:00Z",
                    "is_pinned": True,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Оголошення для поверху",
                value={
                    "title": "Прибирання кухні",
                    "message": "Просимо мешканців 3 поверху прибрати речі з кухні до 20:00.",
                    "target_type": "FLOOR",
                    "target_floor": 3,
                    "is_pinned": False,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Оголошення для конкретних користувачів",
                value={
                    "title": "Зверніться до адміністрації",
                    "message": "Будь ласка, зайдіть до адміністратора гуртожитку.",
                    "target_type": "SPECIFIC_USERS",
                    "target_users": ["0c3a2cb7-7ef5-4c0f-9d36-1b7f0eb05c74"],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Оголошення для кімнати",
                value={
                    "title": "Перевірка кімнати",
                    "message": "Просимо мешканців кімнати бути присутніми о 18:00.",
                    "target_type": "ROOM",
                    "target_room": 12,
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(response=AnnouncementSerializer, description="Оголошення створено."),
            400: OpenApiResponse(
                response=dict,
                description="Помилка валідації даних.",
                examples=[
                    OpenApiExample(
                        "Для поверху не вказано target_floor",
                        value={"target_floor": ["Для оголошення на поверх необхідно обрати поверх."]},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Для кімнати не вказано target_room",
                        value={"target_room": ["Для оголошення на кімнату необхідно обрати кімнату."]},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Для адресного оголошення не вказано target_users",
                        value={
                            "target_users": ["Для адресного оголошення необхідно обрати хоча б одного користувача."]
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Дата завершення в минулому",
                        value={"detail": "Час завершення оголошення має бути в майбутньому."},
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            500: OpenApiResponse(
                response=dict,
                description="Не вдалося надіслати email-сповіщення отримувачам, тому оголошення не збережено.",
                examples=[
                    OpenApiExample(
                        "Email-розсилку не надіслано",
                        value={"detail": "Не вдалося надіслати email-сповіщення отримувачам."},
                        response_only=True,
                    )
                ],
            ),
            403: OpenApiResponse(
                response=dict,
                description="Недостатньо прав для створення оголошення.",
                examples=[
                    OpenApiExample(
                        "Недостатньо прав",
                        value={"detail": "У вас немає прав для створення оголошень."},
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Модератор створює не на своєму поверсі",
                        value={"detail": "Голова поверху може створювати оголошення лише для свого поверху."},
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        serializer = AnnouncementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AnnouncementsService()

        try:
            announcement = service.create_announcement(request.user, serializer.validated_data)
        except AnnouncementError as exc:
            return Response({"detail": str(exc)}, status=get_announcement_error_status(exc))

        response_serializer = AnnouncementSerializer(announcement, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
