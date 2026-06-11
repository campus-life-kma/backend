from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.presence_serializer import PresenceCheckInSerializer, PresenceResponseSerializer
from api.services.presence_service import PresenceService


class PresenceCheckInView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Присутність"],
        summary="Відмітити присутність у спільному просторі",
        request=PresenceCheckInSerializer,
        examples=[
            OpenApiExample(
                "Запит на відмітку присутності",
                value={"room_id": 5},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=PresenceResponseSerializer,
                description="Присутність успішно створено або оновлено.",
                examples=[
                    OpenApiExample(
                        "Поточна присутність",
                        value={
                            "id": 11,
                            "room_id": 5,
                            "room_name": "Спільна кімната",
                            "floor_id": 3,
                            "joined_at": "2026-05-23T18:00:00Z",
                            "expires_at": "2026-05-23T20:00:00Z",
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=dict,
                description="У вибраній кімнаті не можна відмітити присутність.",
                examples=[
                    OpenApiExample(
                        "Заблокована кімната",
                        value={"detail": "Ця кімната заблокована, тому в ній не можна відмітити присутність."},
                    ),
                    OpenApiExample(
                        "Житлова кімната",
                        value={"detail": "Відмітити присутність можна лише у спільних просторах."},
                    ),
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(
                response=dict,
                description="Кімнату не знайдено.",
                examples=[OpenApiExample("Кімнату не знайдено", value={"detail": "Кімнату з таким id не знайдено."})],
            ),
        },
    )
    def post(self, request):
        serializer = PresenceCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PresenceService()

        try:
            presence = service.check_in(request.user, serializer.validated_data["room_id"])
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND
            if str(exc) != "Кімнату з таким id не знайдено.":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=response_status)

        response_serializer = PresenceResponseSerializer(presence, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PresenceGoHomeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Присутність"],
        summary="Очистити поточну присутність",
        request=None,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Поточну присутність очищено.",
                examples=[OpenApiExample("Присутність очищено", value={"detail": "Присутність очищено."})],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def post(self, request):
        service = PresenceService()
        service.go_home(request.user)
        return Response({"detail": "Присутність очищено."}, status=status.HTTP_200_OK)


class PresenceMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Присутність"],
        summary="Поточна присутність користувача",
        request=None,
        responses={
            200: OpenApiResponse(
                response=PresenceResponseSerializer,
                description="Поточна присутність користувача або null, якщо він удома.",
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request):
        service = PresenceService()
        presence = service.get_current(request.user)
        if presence is None:
            return Response(None, status=status.HTTP_200_OK)

        serializer = PresenceResponseSerializer(presence, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
