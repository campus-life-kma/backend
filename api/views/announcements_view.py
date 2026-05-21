from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.announcements_serializer import AnnouncementCreateSerializer, AnnouncementSerializer
from api.services.announcements_service import AnnouncementsService


def get_announcement_error_status(error_message):
    if "не знайдено" in error_message:
        return status.HTTP_404_NOT_FOUND

    if "не призначене" in error_message or "немає прав" in error_message or "Голова поверху" in error_message:
        return status.HTTP_403_FORBIDDEN

    return status.HTTP_400_BAD_REQUEST


class ActiveAnnouncementsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Оголошення"],
        summary="Отримання активних оголошень",
        responses={
            200: OpenApiResponse(
                response=AnnouncementSerializer(many=True), description="Активні оголошення отримано."
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
            403: OpenApiResponse(description="Оголошення не призначене для цього користувача."),
            404: OpenApiResponse(description="Оголошення не знайдено."),
        },
    )
    def post(self, request, announcement_id):
        service = AnnouncementsService()

        try:
            service.mark_as_read(request.user, announcement_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_announcement_error_status(str(exc)))

        return Response({"detail": "Оголошення позначено як прочитане."}, status=status.HTTP_200_OK)


class AnnouncementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Оголошення"],
        summary="Створення оголошення",
        request=AnnouncementCreateSerializer,
        responses={
            201: OpenApiResponse(response=AnnouncementSerializer, description="Оголошення створено."),
            400: OpenApiResponse(description="Помилка валідації даних."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Недостатньо прав для створення оголошення."),
        },
    )
    def post(self, request):
        serializer = AnnouncementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AnnouncementsService()

        try:
            announcement = service.create_announcement(request.user, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_announcement_error_status(str(exc)))

        response_serializer = AnnouncementSerializer(announcement, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
