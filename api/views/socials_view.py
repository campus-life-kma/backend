from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.socials_serializer import (
    SocialEventCreateSerializer,
    SocialEventDetailSerializer,
    SocialSharingRequestCreateSerializer,
    SocialSharingRequestDetailSerializer,
)
from api.services.socials_service import SocialsService


def get_social_error_status(error_message):
    if error_message.startswith("Статус "):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if "не знайдено" in error_message:
        return status.HTTP_404_NOT_FOUND

    if "не маєте доступу" in error_message or "не маєте прав" in error_message:
        return status.HTTP_403_FORBIDDEN

    return status.HTTP_400_BAD_REQUEST


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Отримання соціальної стрічки",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location="path",
                required=True,
                description="Номер сторінки стрічки",
            )
        ],
        responses={
            200: OpenApiResponse(description="Сторінку стрічки успішно отримано."),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request, page):
        service = SocialsService()
        feed = service.get_feed(request.user, page)

        results = []
        for _, item_type, item in feed["items"]:
            if item_type == "event":
                results.append(SocialEventDetailSerializer(item, context={"request": request}).data)
            else:
                results.append(SocialSharingRequestDetailSerializer(item, context={"request": request}).data)

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
        responses={
            201: OpenApiResponse(response=SocialEventDetailSerializer, description="Подію успішно створено."),
            400: OpenApiResponse(description="Помилка валідації даних."),
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
        responses={
            200: OpenApiResponse(response=SocialEventDetailSerializer, description="Користувача додано до події."),
            400: OpenApiResponse(description="Приєднатися до події неможливо."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Подія недоступна цьому користувачу."),
            404: OpenApiResponse(description="Подію не знайдено."),
        },
    )
    def post(self, request, event_id):
        service = SocialsService()

        try:
            event = service.join_event(request.user, event_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

        serializer = SocialEventDetailSerializer(event, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialEventLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Вихід з події",
        request=None,
        responses={
            200: OpenApiResponse(response=SocialEventDetailSerializer, description="Користувача прибрано з події."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(description="Подію не знайдено."),
        },
    )
    def post(self, request, event_id):
        service = SocialsService()

        try:
            event = service.leave_event(request.user, event_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

        serializer = SocialEventDetailSerializer(event, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialEventDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Видалення події",
        responses={
            204: OpenApiResponse(description="Подію видалено."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Недостатньо прав для видалення події."),
            404: OpenApiResponse(description="Подію не знайдено."),
        },
    )
    def delete(self, request, event_id):
        service = SocialsService()

        try:
            service.delete_event(request.user, event_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

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
            ),
            400: OpenApiResponse(description="Помилка валідації даних."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            500: OpenApiResponse(description="У базі відсутній потрібний статус запиту."),
        },
    )
    def post(self, request):
        serializer = SocialSharingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SocialsService()

        try:
            sharing_request = service.create_sharing_request(request.user, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

        response_serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SocialSharingRequestDoneView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Завершення запиту на шеринг",
        request=None,
        responses={
            200: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Запит на шеринг завершено.",
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Недостатньо прав для завершення запиту."),
            404: OpenApiResponse(description="Запит на шеринг не знайдено."),
            500: OpenApiResponse(description="У базі відсутній потрібний статус запиту."),
        },
    )
    def patch(self, request, request_id):
        service = SocialsService()

        try:
            sharing_request = service.complete_sharing_request(request.user, request_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

        serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialSharingRequestDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Соціальна стрічка"],
        summary="Видалення запиту на шеринг",
        responses={
            200: OpenApiResponse(
                response=SocialSharingRequestDetailSerializer,
                description="Запит на шеринг скасовано.",
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Недостатньо прав для видалення запиту."),
            404: OpenApiResponse(description="Запит на шеринг не знайдено."),
            500: OpenApiResponse(description="У базі відсутній потрібний статус запиту."),
        },
    )
    def delete(self, request, request_id):
        service = SocialsService()

        try:
            sharing_request = service.delete_sharing_request(request.user, request_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_social_error_status(str(exc)))

        serializer = SocialSharingRequestDetailSerializer(sharing_request, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
