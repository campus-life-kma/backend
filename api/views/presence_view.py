from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.presence_serializer import PresenceCheckInSerializer, PresenceResponseSerializer
from api.services.presence_service import (
    PresenceLivingRoomError,
    PresenceRoomBlockedError,
    PresenceRoomNotFoundError,
    PresenceService,
)


class PresenceCheckInView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Presence"],
        summary="Check in to a shared room",
        request=PresenceCheckInSerializer,
        examples=[
            OpenApiExample(
                "Check-in request",
                value={"room_id": 5},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(response=PresenceResponseSerializer, description="Presence was created or updated."),
            400: OpenApiResponse(
                response=dict,
                description="The selected room cannot be used for presence.",
                examples=[
                    OpenApiExample(
                        "Blocked room", value={"detail": "This room is blocked and cannot be used for presence."}
                    ),
                    OpenApiExample("Living room", value={"detail": "Check-in is available only for shared spaces."}),
                ],
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            404: OpenApiResponse(
                response=dict,
                description="Room was not found.",
                examples=[OpenApiExample("Missing room", value={"detail": "Room with this id was not found."})],
            ),
        },
    )
    def post(self, request):
        serializer = PresenceCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PresenceService()

        try:
            presence = service.check_in(request.user, serializer.validated_data["room_id"])
        except PresenceRoomNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except (PresenceRoomBlockedError, PresenceLivingRoomError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = PresenceResponseSerializer(presence, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PresenceGoHomeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Presence"],
        summary="Clear current presence",
        request=None,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Presence was cleared.",
                examples=[OpenApiExample("Presence cleared", value={"detail": "Presence cleared."})],
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def post(self, request):
        service = PresenceService()
        service.go_home(request.user)
        return Response({"detail": "Presence cleared."}, status=status.HTTP_200_OK)
